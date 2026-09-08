from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import Category, User
from ..schemas import CategoryIn, CategoryOut, CategoryUpdate
from ..services import kdocs

router = APIRouter(prefix="/api/categories", tags=["categories"])

DEFAULT_CATEGORIES = [
    ("dining", "餐饮", "1 餐饮", "餐厅、食品与供应链"),
    ("luxury", "二奢", "2 二奢", "奢侈品与二手精品"),
    ("promotion", "推广", "3 推广", "营销、媒体与渠道"),
    ("general", "综合", "4.综合", "其他行业联系人"),
    ("ecommerce", "电商", "5 电商", "平台、网店与电商服务"),
    ("travel", "旅游", "6 旅游", "旅行、酒店与出境服务"),
]


def seed_categories(db: Session):
    if db.query(Category).count():
        return
    for i, (key, label, sheet, desc) in enumerate(DEFAULT_CATEGORIES):
        db.add(Category(key=key, label=label, sheet_name=sheet, description=desc, sort_order=i))
    db.commit()


@router.get("", response_model=list[CategoryOut])
def list_categories(all: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Category)
    if not (all and user.role == "admin"):
        q = q.filter(Category.is_active.is_(True))
    return q.order_by(Category.sort_order, Category.id).all()


@router.post("", response_model=CategoryOut)
async def create_category(body: CategoryIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.key == body.key).first():
        raise HTTPException(400, "分类标识已存在")
    if db.query(Category).filter(Category.sheet_name == body.sheet_name).first():
        raise HTTPException(400, "该工作表已被其他分类使用")
    if body.create_sheet:
        cfg = kdocs.get_config(db)
        if not kdocs.is_configured(cfg):
            raise HTTPException(400, "尚未配置金山文档，无法自动新建工作表（可取消勾选“同步新建 tab”仅保存分类）")
        try:
            await kdocs.ensure_sheet(cfg, body.sheet_name)
        except kdocs.KdocsError as exc:
            raise HTTPException(502, f"金山文档新建工作表失败：{exc}")
    c = Category(
        key=body.key,
        label=body.label,
        sheet_name=body.sheet_name,
        description=body.description,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.patch("/{cat_id}", response_model=CategoryOut)
def update_category(cat_id: int, body: CategoryUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(404, "分类不存在")
    if body.label is not None:
        c.label = body.label
    if body.sheet_name is not None:
        c.sheet_name = body.sheet_name
    if body.description is not None:
        c.description = body.description
    if body.sort_order is not None:
        c.sort_order = body.sort_order
    if body.is_active is not None:
        c.is_active = body.is_active
    db.commit()
    db.refresh(c)
    return c


@router.post("/{cat_id}/ensure-sheet")
async def ensure_sheet(cat_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(404, "分类不存在")
    try:
        return await kdocs.ensure_sheet(kdocs.get_config(db), c.sheet_name)
    except kdocs.KdocsError as exc:
        raise HTTPException(502, str(exc))


@router.delete("/{cat_id}")
def delete_category(cat_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(404, "分类不存在")
    db.delete(c)
    db.commit()
    return {"ok": True}
