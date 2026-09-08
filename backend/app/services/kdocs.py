"""金山文档 AirScript 调用封装。

金山文档 -> 表格 -> 效率 -> 脚本编辑器 -> 新建脚本，粘贴 kdocs/kdocs-airscript.js，
然后在脚本编辑器右上角「发布」->「API 调用」拿到 file_id / script_id / AirScript-Token。
调用方式：POST https://www.kdocs.cn/api/v3/ide/file/{file_id}/script/{script_id}/sync_task
"""
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models import KdocsConfig

KDOCS_API = "https://www.kdocs.cn/api/v3/ide/file/{file_id}/script/{script_id}/sync_task"


class KdocsError(Exception):
    pass


def get_config(db: Session) -> KdocsConfig:
    cfg = db.query(KdocsConfig).first()
    if not cfg:
        cfg = KdocsConfig()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def is_configured(cfg: KdocsConfig) -> bool:
    return bool(cfg.file_id and cfg.script_id and cfg.token)


async def run_script(cfg: KdocsConfig, payload: dict[str, Any], timeout: float = 60) -> dict[str, Any]:
    if not is_configured(cfg):
        raise KdocsError("尚未配置金山文档 file_id / script_id / token")
    url = KDOCS_API.format(file_id=cfg.file_id, script_id=cfg.script_id)
    headers = {"AirScript-Token": cfg.token, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, headers=headers, json={"Context": {"argv": payload}})
        except httpx.HTTPError as exc:
            raise KdocsError(f"请求金山文档失败：{exc}") from exc
    if resp.status_code != 200:
        raise KdocsError(f"金山文档返回 HTTP {resp.status_code}：{resp.text[:300]}")
    body = resp.json()
    # 返回结构：{"status": "finished", "data": {"result": <脚本 return 值>, "logs": [...]}}
    data = body.get("data") if isinstance(body, dict) else None
    result = (data or {}).get("result") if isinstance(data, dict) else None
    if result is None:
        result = body.get("result") if isinstance(body, dict) else None
    if not isinstance(result, dict):
        if body.get("status") == "failed" or body.get("error"):
            raise KdocsError(f"脚本执行失败：{body.get('error') or body}")
        raise KdocsError(f"无法解析脚本返回：{str(body)[:300]}")
    if not result.get("ok"):
        raise KdocsError(result.get("error") or "脚本返回失败")
    return result


async def health(cfg: KdocsConfig) -> dict[str, Any]:
    return await run_script(cfg, {"action": "health"})


async def list_sheets(cfg: KdocsConfig) -> list[str]:
    result = await run_script(cfg, {"action": "list_sheets"})
    return [str(s) for s in result.get("sheets", [])]


async def ensure_sheet(cfg: KdocsConfig, sheet_name: str) -> dict[str, Any]:
    return await run_script(cfg, {"action": "ensure_sheet", "sheetName": sheet_name})


async def add_contact(
    cfg: KdocsConfig,
    *,
    sheet_name: str,
    module_label: str,
    card: dict[str, Any],
    importer: str,
    front_image_url: str = "",
    back_image_url: str = "",
    front_image_data: str = "",
    back_image_data: str = "",
) -> dict[str, Any]:
    return await run_script(
        cfg,
        {
            "action": "add",
            "sheetName": sheet_name,
            "moduleLabel": module_label,
            "card": card,
            "importer": importer,
            "frontImageUrl": front_image_url,
            "backImageUrl": back_image_url,
            "frontImageData": front_image_data,
            "backImageData": back_image_data,
        },
        timeout=120,
    )
