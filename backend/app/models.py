from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")  # admin / user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class VisionModel(Base):
    """多模态视觉模型配置（OpenAI 兼容 chat/completions 接口）。"""

    __tablename__ = "vision_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32), default="openai")
    base_url: Mapped[str] = mapped_column(String(255), default="https://api.openai.com/v1")
    api_key: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(128))
    max_tokens: Mapped[int] = mapped_column(Integer, default=1500)
    temperature_x100: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    vision_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Category(Base):
    """名片分类 = 金山表格的一个 tab（工作表）。"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    label: Mapped[str] = mapped_column(String(32))  # 写入“大类”列的值，例如 二奢
    sheet_name: Mapped[str] = mapped_column(String(64))  # 金山工作表名，例如 2 二奢
    description: Mapped[str] = mapped_column(String(128), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class KdocsConfig(Base):
    __tablename__ = "kdocs_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[str] = mapped_column(String(64), default="")
    script_id: Mapped[str] = mapped_column(String(64), default="")
    token: Mapped[str] = mapped_column(String(255), default="")
    doc_url: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class SearchConfig(Base):
    """联网检索（Tavily）：识别出公司后自动搜索并总结主营业务。"""

    __tablename__ = "search_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="tavily")
    api_key: Mapped[str] = mapped_column(String(255), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_results: Mapped[int] = mapped_column(Integer, default=5)
    # 总结用的纯文本模型（OpenAI 兼容），与视觉模型独立
    llm_base_url: Mapped[str] = mapped_column(String(255), default="https://api.openai.com/v1")
    llm_api_key: Mapped[str] = mapped_column(String(255), default="")
    llm_model: Mapped[str] = mapped_column(String(128), default="")
    llm_max_tokens: Mapped[int] = mapped_column(Integer, default=1500)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CardRecord(Base):
    __tablename__ = "card_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    importer: Mapped[str] = mapped_column(String(64), default="")
    category_key: Mapped[str] = mapped_column(String(32), default="")
    front_image: Mapped[str] = mapped_column(String(255), default="")
    back_image: Mapped[str] = mapped_column(String(255), default="")
    card_json: Mapped[str] = mapped_column(Text, default="{}")
    kdocs_row: Mapped[int] = mapped_column(Integer, default=0)
    duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="synced")  # synced / failed
    error: Mapped[str] = mapped_column(Text, default="")
    warning: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
