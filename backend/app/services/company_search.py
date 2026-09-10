"""公司联网检索（Tavily）+ 用已配置的模型总结「主营业务关键词 / 主营产品·服务类型」。

Tavily 文档：https://docs.tavily.com/documentation/api-reference/endpoint/search
"""
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models import SearchConfig, VisionModel
from .vision import VisionError, _extract_json, chat_with_images

TAVILY_URL = "https://api.tavily.com/search"

SUMMARY_PROMPT = """你是企业信息分析助手。下面是关于公司「{company}」{website_hint}的网络搜索结果。
请基于这些资料，只输出一个 JSON 对象，不要任何解释：
{{
  "businessKeywords": "主营业务关键词，中文，10字以内，例如：二手奢侈品回收",
  "productServiceType": "主营产品/服务类型，中文，10字以内，例如：奢侈品/贸易",
  "summary": "公司概述，中文，80~150字：做什么、面向谁、规模/所在地等"
}}
资料不足时按公司名和官网域名合理推断，仍要给出简短结果；完全无法判断的字段填空字符串。

搜索结果：
{results}"""


class SearchError(Exception):
    pass


def get_config(db: Session) -> SearchConfig:
    cfg = db.query(SearchConfig).first()
    if not cfg:
        cfg = SearchConfig()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def is_configured(cfg: SearchConfig) -> bool:
    return bool(cfg.api_key)


def is_enabled(cfg: SearchConfig) -> bool:
    return bool(cfg.enabled) and is_configured(cfg)


async def tavily_search(cfg: SearchConfig, query: str, timeout: float = 30) -> list[dict[str, str]]:
    if not is_configured(cfg):
        raise SearchError("尚未配置 Tavily API Key")
    body = {
        "query": query,
        "search_depth": "basic",
        "max_results": max(1, min(cfg.max_results or 5, 10)),
        "include_answer": False,
        "include_raw_content": False,
    }
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(TAVILY_URL, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise SearchError(f"请求 Tavily 失败：{exc}") from exc
    if resp.status_code == 401:
        raise SearchError("Tavily API Key 无效")
    if resp.status_code == 432 or resp.status_code == 429:
        raise SearchError(f"Tavily 额度不足或请求过于频繁（HTTP {resp.status_code}）")
    if resp.status_code != 200:
        raise SearchError(f"Tavily 返回 HTTP {resp.status_code}：{resp.text[:300]}")
    try:
        results = resp.json().get("results") or []
    except ValueError as exc:
        raise SearchError(f"无法解析 Tavily 返回：{resp.text[:300]}") from exc
    return [
        {
            "title": str(r.get("title") or "").strip(),
            "url": str(r.get("url") or "").strip(),
            "content": str(r.get("content") or "").strip()[:800],
        }
        for r in results
        if isinstance(r, dict)
    ]


def _site_of(website: str) -> str:
    site = website.strip().lower()
    for prefix in ("https://", "http://"):
        if site.startswith(prefix):
            site = site[len(prefix):]
    return site.split("/")[0].removeprefix("www.")


def build_query(company: str, website: str, language: str) -> str:
    q = company.strip()
    site = _site_of(website) if website else ""
    if site:
        q += f" {site}"
    if language == "JP":
        q += " 会社 事業内容"
    elif language == "EN":
        q += " company business"
    else:
        q += " 公司 主营业务"
    return q


async def enrich_company(
    cfg: SearchConfig,
    model: VisionModel,
    company: str,
    website: str = "",
    language: str = "",
) -> dict[str, Any]:
    company = company.strip()
    if not company:
        raise SearchError("公司名为空，无法检索")
    results = await tavily_search(cfg, build_query(company, website, language))
    if not results:
        raise SearchError("没有搜到该公司的资料")
    lines = [f"[{i + 1}] {r['title']}\n{r['url']}\n{r['content']}" for i, r in enumerate(results)]
    prompt = SUMMARY_PROMPT.format(
        company=company,
        website_hint=f"（官网 {website.strip()}）" if website.strip() else "",
        results="\n\n".join(lines),
    )
    try:
        raw = await chat_with_images(model, prompt, [], timeout=90)
        data = _extract_json(raw)
    except VisionError as exc:
        raise SearchError(f"模型总结失败：{exc}") from exc
    return {
        "businessKeywords": str(data.get("businessKeywords") or "").strip()[:10],
        "productServiceType": str(data.get("productServiceType") or "").strip()[:10],
        "summary": str(data.get("summary") or "").strip(),
        "sources": [{"title": r["title"], "url": r["url"]} for r in results],
    }
