import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent.parent.parent


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
    templates = Jinja2Templates(directory=ROOT / "frontend/templates")

    @app.get("/health")
    def health():
        with database() as connection:
            connection.execute("SELECT count(*) FROM reviews").fetchone()
        return {"status": "ok"}

    @app.get("/")
    def index(request: Request):
        with database() as connection:
            reviews = connection.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
        return templates.TemplateResponse(request=request, name="index.html", context={"reviews": reviews})

    @app.get("/reviews/new")
    def new_review(request: Request):
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
        with database() as connection:
            review = connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if review is None:
            raise HTTPException(status_code=404, detail="No encontramos esa revisión.")
        return templates.TemplateResponse(request=request, name="detail.html", context={"review": review})

    return app


app = create_app()
