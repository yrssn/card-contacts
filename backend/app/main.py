from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import hash_password
from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth_users, cards, categories, kdocs_config, search_config, vision_models
from .routers.categories import seed_categories


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        existing = {c["name"] for c in inspect(conn).get_columns("card_records")}
        if "warning" not in existing:
            conn.execute(text("ALTER TABLE card_records ADD COLUMN warning TEXT DEFAULT ''"))
    with SessionLocal() as db:
        if not db.query(User).filter(User.role == "admin").first():
            db.add(
                User(
                    username=settings.ADMIN_USERNAME,
                    display_name="管理员",
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    role="admin",
                )
            )
            db.commit()
        seed_categories(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth_users, vision_models, categories, kdocs_config, search_config, cards):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.APP_NAME}


app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 生产模式：把前端 build 产物放到 backend/static 即可由后端一并托管
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        file = STATIC_DIR / full_path
        if full_path and file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    import uvicorn

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
