from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import User
from ..schemas import EnrichIn, EnrichOut, SearchConfigIn, SearchConfigOut
from ..services import company_search

router = APIRouter(prefix="/api/search", tags=["search"])


def _mask(k: str) -> str:
    return (k[:6] + "****" + k[-4:]) if len(k) > 12 else ("****" if k else "")


def to_out(cfg) -> SearchConfigOut:
    return SearchConfigOut(
        provider=cfg.provider,
        api_key_masked=_mask(cfg.api_key),
        enabled=cfg.enabled,
        max_results=cfg.max_results,
        configured=company_search.is_configured(cfg),
        llm_base_url=cfg.llm_base_url,
        llm_api_key_masked=_mask(cfg.llm_api_key),
        llm_model=cfg.llm_model,
        llm_max_tokens=cfg.llm_max_tokens,
        llm_configured=company_search.llm_configured(cfg),
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
    if body.llm_api_key and "****" not in body.llm_api_key:
        cfg.llm_api_key = body.llm_api_key.strip()
    cfg.llm_base_url = body.llm_base_url.strip() or "https://api.openai.com/v1"
    cfg.llm_model = body.llm_model.strip()
    cfg.llm_max_tokens = body.llm_max_tokens
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
    try:
        data = await company_search.enrich_company(cfg, body.company, body.website, body.language)
    except company_search.SearchError as exc:
        raise HTTPException(502, str(exc))
    return EnrichOut(**data)
