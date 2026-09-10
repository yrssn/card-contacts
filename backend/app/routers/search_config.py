from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import User
from ..schemas import EnrichIn, EnrichOut, SearchConfigIn, SearchConfigOut
from ..services import company_search
from .vision_models import get_default_model

router = APIRouter(prefix="/api/search", tags=["search"])


def to_out(cfg) -> SearchConfigOut:
    k = cfg.api_key
    return SearchConfigOut(
        provider=cfg.provider,
        api_key_masked=(k[:6] + "****" + k[-4:]) if len(k) > 12 else ("****" if k else ""),
        enabled=cfg.enabled,
        max_results=cfg.max_results,
        configured=company_search.is_configured(cfg),
    )


@router.get("/config", response_model=SearchConfigOut)
def get_config(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_out(company_search.get_config(db))


@router.put("/config", response_model=SearchConfigOut)
def save_config(body: SearchConfigIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    cfg = company_search.get_config(db)
    if body.api_key and "****" not in body.api_key:
        cfg.api_key = body.api_key.strip()
    cfg.enabled = body.enabled
    cfg.max_results = body.max_results
    db.commit()
    db.refresh(cfg)
    return to_out(cfg)


@router.post("/test", response_model=EnrichOut)
async def test_search(body: EnrichIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return await _enrich(body, db)


@router.post("/enrich", response_model=EnrichOut)
async def enrich(body: EnrichIn, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _enrich(body, db)


async def _enrich(body: EnrichIn, db: Session) -> EnrichOut:
    cfg = company_search.get_config(db)
    model = get_default_model(db)
    if not model:
        raise HTTPException(400, "尚未配置视觉模型，无法进行总结")
    try:
        data = await company_search.enrich_company(cfg, model, body.company, body.website, body.language)
    except company_search.SearchError as exc:
        raise HTTPException(502, str(exc))
    return EnrichOut(**data)
