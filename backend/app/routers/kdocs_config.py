from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import User
from ..schemas import KdocsConfigIn, KdocsConfigOut
from ..services import kdocs

router = APIRouter(prefix="/api/kdocs", tags=["kdocs"])


def to_out(cfg) -> KdocsConfigOut:
    t = cfg.token
    return KdocsConfigOut(
        file_id=cfg.file_id,
        script_id=cfg.script_id,
        token_masked=(t[:4] + "****" + t[-4:]) if len(t) > 8 else ("****" if t else ""),
        doc_url=cfg.doc_url,
        configured=kdocs.is_configured(cfg),
    )


@router.get("/config", response_model=KdocsConfigOut)
def get_config(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_out(kdocs.get_config(db))


@router.put("/config", response_model=KdocsConfigOut)
def save_config(body: KdocsConfigIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    cfg = kdocs.get_config(db)
    cfg.file_id = body.file_id.strip()
    cfg.script_id = body.script_id.strip()
    if body.token and "****" not in body.token:
        cfg.token = body.token.strip()
    cfg.doc_url = body.doc_url.strip()
    db.commit()
    db.refresh(cfg)
    return to_out(cfg)


@router.post("/test")
async def test_connection(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        result = await kdocs.health(kdocs.get_config(db))
        sheets = await kdocs.list_sheets(kdocs.get_config(db))
    except kdocs.KdocsError as exc:
        raise HTTPException(502, str(exc))
    return {"ok": True, "version": result.get("version"), "sheets": sheets}


@router.get("/sheets")
async def sheets(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return {"sheets": await kdocs.list_sheets(kdocs.get_config(db))}
    except kdocs.KdocsError as exc:
        raise HTTPException(502, str(exc))
