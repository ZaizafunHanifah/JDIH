from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.db import init_db
from app.routers import documents, topics, metadata

app = FastAPI(title="JDIH Fitur Tambahan")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup_event():
    init_db()


app.include_router(documents.router)
app.include_router(topics.router)
app.include_router(metadata.router)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")