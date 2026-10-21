import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_BUILD = ROOT / "frontend/dist"


class ReviewInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=2000)
    inclusion: str = Field(min_length=1, max_length=10000)
    exclusion: str = Field(min_length=1, max_length=10000)

    @field_validator("title", "question", "inclusion", "exclusion")
    @classmethod
    def required_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Completa este campo.")
        return value


def as_review(row):
    return dict(row)


def create_app(database_path=None):
    db_path = Path(database_path or os.environ.get("SEMANTIK_DATABASE", ROOT / ".local/reviews.sqlite3"))

    @contextmanager
    def database():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @asynccontextmanager
    async def lifespan(app):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with database() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                question TEXT NOT NULL,
                inclusion TEXT NOT NULL,
                exclusion TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )""")
        yield

    app = FastAPI(title="Semantik SLR", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=ROOT / "frontend/static"), name="static")
    if FRONTEND_BUILD.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_BUILD / "assets"), name="assets")
    templates = Jinja2Templates(directory=ROOT / "frontend/templates")

    @app.get("/api/reviews")
    def api_reviews():
        with database() as connection:
            rows = connection.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
        return [as_review(row) for row in rows]

    @app.post("/api/reviews", status_code=201)
    def api_create_review(payload: ReviewInput):
        with database() as connection:
            cursor = connection.execute(
                "INSERT INTO reviews (title, question, inclusion, exclusion) VALUES (?, ?, ?, ?)",
                (payload.title, payload.question, payload.inclusion, payload.exclusion),
            )
            row = connection.execute("SELECT * FROM reviews WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return as_review(row)

    @app.get("/api/reviews/{review_id}")
    def api_review(review_id: int):
        with database() as connection:
            row = connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="No encontramos esa revisión.")
        return as_review(row)

    @app.get("/health")
    def health():
        with database() as connection:
            connection.execute("SELECT count(*) FROM reviews").fetchone()
        return {"status": "ok"}

    @app.get("/")
    def index(request: Request):
        if (FRONTEND_BUILD / "index.html").exists():
            return FileResponse(FRONTEND_BUILD / "index.html")
        with database() as connection:
            reviews = connection.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
        return templates.TemplateResponse(request=request, name="index.html", context={"reviews": reviews})

    @app.get("/reviews/new")
    def new_review(request: Request):
        if (FRONTEND_BUILD / "index.html").exists():
            return FileResponse(FRONTEND_BUILD / "index.html")
        return templates.TemplateResponse(request=request, name="form.html", context={"values": {}, "errors": {}})

    @app.post("/reviews")
    async def create_review(request: Request):
        form = await request.form()
        limits = {"title": 200, "question": 2000, "inclusion": 10000, "exclusion": 10000}
        values = {key: str(form.get(key, "")).strip() for key in limits}
        errors = {}
        for key, limit in limits.items():
            if not values[key]:
                errors[key] = "Completa este campo."
            elif len(values[key]) > limit:
                errors[key] = f"Usa como máximo {limit} caracteres."
        if errors:
            return templates.TemplateResponse(request=request, name="form.html", context={"values": values, "errors": errors}, status_code=422)
        with database() as connection:
            cursor = connection.execute(
                "INSERT INTO reviews (title, question, inclusion, exclusion) VALUES (?, ?, ?, ?)",
                tuple(values[key] for key in limits),
            )
            review_id = cursor.lastrowid
        return RedirectResponse(f"/reviews/{review_id}", status_code=303)

    @app.get("/reviews/{review_id}")
    def review_detail(request: Request, review_id: int):
        if (FRONTEND_BUILD / "index.html").exists():
            return FileResponse(FRONTEND_BUILD / "index.html")
        with database() as connection:
            review = connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if review is None:
            raise HTTPException(status_code=404, detail="No encontramos esa revisión.")
        return templates.TemplateResponse(request=request, name="detail.html", context={"review": review})

    return app


app = create_app()
