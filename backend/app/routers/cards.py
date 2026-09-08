import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import CardRecord, Category, User
from ..schemas import Card, ConfirmIn, RecognizeOut, RecordOut
from ..services import kdocs
from ..services.vision import VisionError, image_to_data_url, recognize_card
from .vision_models import get_default_model

router = APIRouter(prefix="/api/cards", tags=["cards"])

ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_SIZE = 15 * 1024 * 1024


def public_url(rel: str) -> str:
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/uploads/{rel}" if rel else ""


def image_data(rel: str) -> str:
    """金山 AddPicture 只接受 kdocs 同域 URL 或 Base64，因此把图片压缩后以 Base64 传给脚本。"""
    if not rel:
        return ""
    path = settings.UPLOAD_DIR / rel
    if not path.exists():
        return ""
    try:
        return image_to_data_url(path.read_bytes(), max_side=720, quality=72)
    except OSError:
        return ""


async def _save_upload(file: UploadFile | None) -> tuple[str, bytes]:
    if file is None or not file.filename:
        return "", b""
    if file.content_type not in ALLOWED:
        raise HTTPException(400, f"不支持的图片格式：{file.content_type}")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(400, "图片超过 15MB")
    day = datetime.utcnow().strftime("%Y%m%d")
    ext = Path(file.filename).suffix.lower() or ".jpg"
    rel = f"{day}/{uuid.uuid4().hex}{ext}"
    target = settings.UPLOAD_DIR / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return rel, data


@router.post("/recognize", response_model=RecognizeOut)
async def recognize(
    front: UploadFile = File(...),
    back: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = get_default_model(db)
    if not model:
        raise HTTPException(400, "尚未配置视觉模型，请联系管理员在「模型配置」中添加")
    front_rel, front_bytes = await _save_upload(front)
    back_rel, back_bytes = await _save_upload(back)
    try:
        card = await recognize_card(model, [front_bytes, back_bytes])
    except VisionError as exc:
        raise HTTPException(502, f"识别失败：{exc}")
    return RecognizeOut(
        card=Card(**card),
        front_image=front_rel,
        back_image=back_rel,
        front_image_url=public_url(front_rel),
        back_image_url=public_url(back_rel),
        model_used=f"{model.name} ({model.model})",
    )


def to_record_out(r: CardRecord) -> RecordOut:
    try:
        card = Card(**json.loads(r.card_json or "{}"))
    except (ValueError, TypeError):
        card = Card()
    return RecordOut(
        id=r.id,
        importer=r.importer,
        category_key=r.category_key,
        front_image_url=public_url(r.front_image),
        back_image_url=public_url(r.back_image),
        card=card,
        kdocs_row=r.kdocs_row,
        duplicate=r.duplicate,
        status=r.status,
        error=r.error,
        warning=r.warning,
        created_at=r.created_at,
    )


@router.post("/confirm", response_model=RecordOut)
async def confirm(body: ConfirmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.key == body.category_key, Category.is_active.is_(True)).first()
    if not category:
        raise HTTPException(400, "录入分类不正确")
    for rel in (body.front_image, body.back_image):
        if rel and (".." in rel or not (settings.UPLOAD_DIR / rel).exists()):
            raise HTTPException(400, "图片不存在，请重新拍摄")
    importer = user.display_name or user.username
    record = CardRecord(
        user_id=user.id,
        importer=importer,
        category_key=category.key,
        front_image=body.front_image,
        back_image=body.back_image,
        card_json=json.dumps(body.card.model_dump(), ensure_ascii=False),
    )
    try:
        result = await kdocs.add_contact(
            kdocs.get_config(db),
            sheet_name=category.sheet_name,
            module_label=category.label,
            card=body.card.model_dump(),
            importer=importer,
            front_image_url=public_url(body.front_image),
            back_image_url=public_url(body.back_image),
            front_image_data=image_data(body.front_image),
            back_image_data=image_data(body.back_image),
        )
        record.kdocs_row = int(result.get("row") or 0)
        record.duplicate = bool(result.get("duplicate"))
        record.warning = str(result.get("imageError") or "")
        record.status = "synced"
    except kdocs.KdocsError as exc:
        record.status = "failed"
        record.error = str(exc)
    db.add(record)
    db.commit()
    db.refresh(record)
    if record.status == "failed":
        raise HTTPException(502, f"已保存到本地，但同步金山文档失败：{record.error}")
    return to_record_out(record)


@router.post("/{record_id}/retry", response_model=RecordOut)
async def retry(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(CardRecord, record_id)
    if not r or (user.role != "admin" and r.user_id != user.id):
        raise HTTPException(404, "记录不存在")
    category = db.query(Category).filter(Category.key == r.category_key).first()
    if not category:
        raise HTTPException(400, "分类已删除")
    try:
        result = await kdocs.add_contact(
            kdocs.get_config(db),
            sheet_name=category.sheet_name,
            module_label=category.label,
            card=json.loads(r.card_json or "{}"),
            importer=r.importer,
            front_image_url=public_url(r.front_image),
            back_image_url=public_url(r.back_image),
            front_image_data=image_data(r.front_image),
            back_image_data=image_data(r.back_image),
        )
        r.kdocs_row, r.duplicate = int(result.get("row") or 0), bool(result.get("duplicate"))
        r.status, r.error = "synced", ""
        r.warning = str(result.get("imageError") or "")
    except kdocs.KdocsError as exc:
        r.status, r.error = "failed", str(exc)
    db.commit()
    db.refresh(r)
    if r.status == "failed":
        raise HTTPException(502, r.error)
    return to_record_out(r)


@router.get("/records", response_model=list[RecordOut])
def records(limit: int = 50, mine: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(CardRecord)
    if mine or user.role != "admin":
        q = q.filter(CardRecord.user_id == user.id)
    return [to_record_out(r) for r in q.order_by(CardRecord.id.desc()).limit(min(limit, 200)).all()]
