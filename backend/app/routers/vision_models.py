from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import User, VisionModel
from ..schemas import VisionModelIn, VisionModelOut
from ..services.vision import verify_vision

router = APIRouter(prefix="/api/vision-models", tags=["vision models"])


def mask(key: str) -> str:
    return key[:4] + "****" + key[-4:] if len(key) > 8 else "****"


def to_out(m: VisionModel) -> VisionModelOut:
    return VisionModelOut(
        id=m.id,
        name=m.name,
        provider=m.provider,
        base_url=m.base_url,
        api_key_masked=mask(m.api_key),
        model=m.model,
        max_tokens=m.max_tokens,
        temperature=m.temperature_x100 / 100,
        is_default=m.is_default,
        vision_verified=m.vision_verified,
        verify_message=m.verify_message,
        created_at=m.created_at,
    )


def get_default_model(db: Session) -> VisionModel | None:
    return (
        db.query(VisionModel).filter(VisionModel.is_default.is_(True)).first()
        or db.query(VisionModel).filter(VisionModel.vision_verified.is_(True)).order_by(VisionModel.id).first()
    )


def _set_default(db: Session, m: VisionModel):
    db.query(VisionModel).update({VisionModel.is_default: False})
    m.is_default = True


@router.get("", response_model=list[VisionModelOut])
def list_models(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [to_out(m) for m in db.query(VisionModel).order_by(VisionModel.id).all()]


@router.post("", response_model=VisionModelOut)
async def create_model(body: VisionModelIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = VisionModel(
        name=body.name,
        provider=body.provider,
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
        max_tokens=body.max_tokens,
        temperature_x100=int(body.temperature * 100),
    )
    ok, msg = await verify_vision(m)
    if not ok:
        raise HTTPException(400, f"视觉能力验证失败，未保存：{msg}")
    m.vision_verified, m.verify_message = True, msg
    db.add(m)
    if body.is_default or db.query(VisionModel).count() == 0:
        _set_default(db, m)
    db.commit()
    db.refresh(m)
    return to_out(m)


@router.put("/{model_id}", response_model=VisionModelOut)
async def update_model(model_id: int, body: VisionModelIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.get(VisionModel, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    m.name, m.provider, m.base_url, m.model = body.name, body.provider, body.base_url, body.model
    if body.api_key and "****" not in body.api_key:
        m.api_key = body.api_key
    m.max_tokens, m.temperature_x100 = body.max_tokens, int(body.temperature * 100)
    ok, msg = await verify_vision(m)
    if not ok:
        db.rollback()
        raise HTTPException(400, f"视觉能力验证失败，未保存：{msg}")
    m.vision_verified, m.verify_message = True, msg
    if body.is_default:
        _set_default(db, m)
    db.commit()
    db.refresh(m)
    return to_out(m)


@router.post("/{model_id}/verify", response_model=VisionModelOut)
async def verify_model(model_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.get(VisionModel, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    m.vision_verified, m.verify_message = await verify_vision(m)
    db.commit()
    db.refresh(m)
    return to_out(m)


@router.post("/{model_id}/default", response_model=VisionModelOut)
def set_default(model_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.get(VisionModel, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    _set_default(db, m)
    db.commit()
    db.refresh(m)
    return to_out(m)


@router.delete("/{model_id}")
def delete_model(model_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.get(VisionModel, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    db.delete(m)
    db.commit()
    return {"ok": True}
