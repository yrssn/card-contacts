from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = ""
    password: str = Field(min_length=6)
    role: str = "user"


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class VisionModelIn(BaseModel):
    name: str
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str
    model: str
    max_tokens: int = 1500
    temperature: float = 0
    is_default: bool = False


class VisionModelOut(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    api_key_masked: str
    model: str
    max_tokens: int
    temperature: float
    is_default: bool
    vision_verified: bool
    verify_message: str
    created_at: datetime


class CategoryIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(min_length=1, max_length=32)
    sheet_name: str = Field(min_length=1, max_length=64)
    description: str = ""
    sort_order: int = 0
    is_active: bool = True
    create_sheet: bool = True


class CategoryUpdate(BaseModel):
    label: Optional[str] = None
    sheet_name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryOut(BaseModel):
    id: int
    key: str
    label: str
    sheet_name: str
    description: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class KdocsConfigIn(BaseModel):
    file_id: str
    script_id: str
    token: str
    doc_url: str = ""


class KdocsConfigOut(BaseModel):
    file_id: str
    script_id: str
    token_masked: str
    doc_url: str
    configured: bool


class SearchConfigIn(BaseModel):
    api_key: str = ""
    enabled: bool = True
    max_results: int = Field(default=5, ge=1, le=10)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_max_tokens: int = Field(default=1500, ge=200, le=32000)


class SearchConfigOut(BaseModel):
    provider: str
    api_key_masked: str
    enabled: bool
    max_results: int
    configured: bool
    llm_base_url: str
    llm_api_key_masked: str
    llm_model: str
    llm_max_tokens: int
    llm_configured: bool


class EnrichIn(BaseModel):
    company: str
    website: str = ""
    language: str = ""


class EnrichOut(BaseModel):
    website: str = ""
    businessKeywords: str = ""
    productServiceType: str = ""
    summary: str = ""
    sources: list[dict] = []


class Card(BaseModel):
    language: str = ""  # JP / CN / EN
    name: str = ""
    sex: str = ""
    note: str = ""
    department: str = ""  # 职位
    businessKeywords: str = ""
    productServiceType: str = ""
    company: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""


class RecognizeOut(BaseModel):
    card: Card
    front_image: str
    back_image: str
    front_image_url: str
    back_image_url: str
    model_used: str
    company_summary: str = ""
    search_error: str = ""
    sources: list[dict] = []


class ConfirmIn(BaseModel):
    category_key: str
    card: Card
    front_image: str = ""
    back_image: str = ""


class RecordOut(BaseModel):
    id: int
    importer: str
    category_key: str
    front_image_url: str
    back_image_url: str
    card: Card
    kdocs_row: int
    duplicate: bool
    status: str
    error: str
    warning: str = ""
    created_at: datetime


class RecordPage(BaseModel):
    items: list[RecordOut]
    total: int
    page: int
    page_size: int
