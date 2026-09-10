"""公司联网检索（Tavily）+ 用独立配置的文本模型总结「官网 / 主营业务关键词 / 主营产品·服务类型」。

Tavily 文档：https://docs.tavily.com/documentation/api-reference/endpoint/search
"""
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models import SearchConfig
from .vision import _extract_json

TAVILY_URL = "https://api.tavily.com/search"

SUMMARY_PROMPT = """你是企业信息分析助手。下面是关于公司「{company}」{website_hint}的网络搜索结果。
请基于这些资料，只输出一个 JSON 对象，不要任何解释：
{{
  "website": "该公司官网首页完整 URL（从搜索结果里选最可能是官方站的链接，只保留域名首页，不是官网则填空）",
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


def llm_configured(cfg: SearchConfig) -> bool:
    return bool(cfg.llm_api_key and cfg.llm_model and cfg.llm_base_url)


async def chat_text(cfg: SearchConfig, prompt: str, timeout: float = 90) -> str:
    if not llm_configured(cfg):
        raise SearchError("尚未配置总结用的文本模型")
    body: dict[str, Any] = {
        "model": cfg.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": cfg.llm_max_tokens or 1500,
        "temperature": 0,
    }
    url = cfg.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {cfg.llm_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise SearchError(f"请求文本模型失败：{exc}") from exc
    if resp.status_code != 200:
        raise SearchError(f"文本模型返回 HTTP {resp.status_code}：{resp.text[:400]}")
    try:
        choice = resp.json()["choices"][0]
        message = choice.get("message") or {}
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
        raise SearchError(f"无法解析文本模型返回：{resp.text[:400]}") from exc
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    content = (content or "").strip()
    if not content:
        reasoning = (message.get("reasoning_content") or message.get("reasoning") or "").strip()
        if reasoning and "{" in reasoning:
            return reasoning
        raise SearchError(f"文本模型返回空内容（finish_reason={choice.get('finish_reason')}）")
    return content


def is_enabled(cfg: SearchConfig) -> bool:
    return bool(cfg.enabled) and is_configured(cfg) and llm_configured(cfg)


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


def _clean_website(value: str, results: list[dict[str, str]]) -> str:
    site = _site_of(str(value or ""))
    if not site or "." not in site:
        return ""
    # 只采纳搜索结果里真实出现过的域名，避免模型臆造
    if not any(_site_of(r["url"]) == site for r in results):
        return ""
    return f"https://{site}"


async def enrich_company(
    cfg: SearchConfig,
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
    raw = await chat_text(cfg, prompt)
    try:
        data = _extract_json(raw)
    except Exception as exc:  # noqa: BLE001 - 模型输出不是 JSON
        raise SearchError(f"文本模型输出无法解析：{exc}") from exc
    return {
        "website": _clean_website(data.get("website"), results),
        "businessKeywords": str(data.get("businessKeywords") or "").strip()[:10],
        "productServiceType": str(data.get("productServiceType") or "").strip()[:10],
        "summary": str(data.get("summary") or "").strip(),
        "sources": [{"title": r["title"], "url": r["url"]} for r in results],
    }
