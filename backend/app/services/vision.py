"""多模态视觉模型调用（OpenAI 兼容 /chat/completions，支持 OpenAI / 通义千问 / 智谱 / 豆包 / DeepSeek-VL 等）。"""
import base64
import io
import json
import re
from typing import Any

import httpx
from PIL import Image

from ..models import VisionModel

CARD_PROMPT = """你是名片信息提取助手。请仔细阅读名片图片（可能有正反两面，可能是中文、日文或英文），提取信息并只输出一个 JSON 对象，不要任何解释，字段如下：
{
  "language": "名片主要语种，只能是 JP / CN / EN 之一",
  "name": "姓名（保留原文，日文名保留汉字）",
  "sex": "性别，能判断则填 男/女，否则留空",
  "note": "备注，如年龄段、语言能力等，没有留空",
  "department": "部门+职位，例如 営業本部 主任 / 代表取締役",
  "businessKeywords": "主营业务关键词，10字以内",
  "productServiceType": "主营产品/服务类型，10字以内",
  "company": "公司名全称",
  "website": "官网网址",
  "email": "邮箱，多个用 / 分隔",
  "phone": "电话，多个用 / 分隔，保留原格式"
}
找不到的字段填空字符串。"""


class VisionError(Exception):
    pass


def image_to_data_url(data: bytes, max_side: int = 1600, quality: int = 88) -> str:
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _test_image_data_url() -> str:
    """生成一张纯红色小图用于验证模型是否支持图片输入。"""
    img = Image.new("RGB", (64, 64), (220, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


async def chat_with_images(model: VisionModel, prompt: str, image_data_urls: list[str], timeout: float = 120) -> str:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for url in image_data_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    body: dict[str, Any] = {
        "model": model.model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": model.max_tokens,
        "temperature": model.temperature_x100 / 100,
    }
    url = model.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {model.api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise VisionError(f"请求模型失败：{exc}") from exc
    if resp.status_code != 200:
        raise VisionError(f"模型返回 HTTP {resp.status_code}：{resp.text[:400]}")
    try:
        choice = resp.json()["choices"][0]
        message = choice.get("message") or {}
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
        raise VisionError(f"无法解析模型返回：{resp.text[:400]}") from exc
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    content = (content or "").strip()
    if not content:
        reasoning = (message.get("reasoning_content") or message.get("reasoning") or "").strip()
        if reasoning and "{" in reasoning:
            return reasoning
        finish = choice.get("finish_reason")
        if finish == "length":
            raise VisionError(f"模型输出被截断（max_tokens={model.max_tokens} 太小，推理模型建议 4000 以上）")
        if finish == "content_filter":
            raise VisionError("模型触发内容审核，未返回结果")
        raise VisionError(f"模型返回了空内容（finish_reason={finish}）：{resp.text[:300]}")
    return content


async def verify_vision(model: VisionModel) -> tuple[bool, str]:
    """必须是视觉模型：发一张红色图片，要求回答颜色。"""
    try:
        answer = await chat_with_images(
            model,
            "这张图片主要是什么颜色？只回答一个颜色词。",
            [_test_image_data_url()],
            timeout=60,
        )
    except VisionError as exc:
        msg = str(exc)
        if re.search(r"image|vision|multimodal|不支持|content type", msg, re.I):
            return False, f"该模型不支持图片输入，请选择视觉模型：{msg}"
        return False, msg
    if re.search(r"红|red|赤", answer, re.I):
        return True, f"验证通过，模型回答：{answer.strip()[:50]}"
    return False, f"模型未能正确识别图片内容（回答：{answer.strip()[:80]}），请确认是视觉模型"


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _repair_truncated_json(text)
        if data is None:
            raise VisionError(f"模型输出不是合法 JSON（可能被截断，试试调大 max_tokens）：{text[:200]}")
    return data if isinstance(data, dict) else {}


def _repair_truncated_json(text: str) -> dict[str, Any] | None:
    """模型输出中途被截断时，从最后一个完整的键值对处收尾，保住已识别的字段。"""
    start = text.find("{")
    if start < 0:
        return None
    body = text[start:]
    for cut in (len(body), *[m.start() for m in reversed(list(re.finditer(r",", body)))]):
        candidate = body[:cut].rstrip()
        for tail in ("}", '"}', '":""}'):
            try:
                data = json.loads(candidate + tail)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data:
                return data
    return None


async def recognize_card(model: VisionModel, images: list[bytes]) -> dict[str, str]:
    urls = [image_to_data_url(img) for img in images if img]
    if not urls:
        raise VisionError("没有图片")
    try:
        raw = await chat_with_images(model, CARD_PROMPT, urls)
        data = _extract_json(raw)
    except VisionError:
        # 双面失败退回只识别正面；单面失败则重试一次（模型输出不稳定）
        raw = await chat_with_images(model, CARD_PROMPT, urls[:1])
        data = _extract_json(raw)
    keys = [
        "language", "name", "sex", "note", "department", "businessKeywords",
        "productServiceType", "company", "website", "email", "phone",
    ]
    card = {k: str(data.get(k) or "").strip() for k in keys}
    lang = card["language"].upper()
    card["language"] = lang if lang in ("JP", "CN", "EN") else ("JP" if "日" in lang else "CN" if "中" in lang else "EN" if "英" in lang else lang[:2])
    return card
