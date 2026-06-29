from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from routers import cases

app = FastAPI(
    title="Peraku-Xread",
    description="Parallel data processing service for mortgage preparation.",
    version="0.1.0",
)

app.include_router(cases.router)


@app.get("/health")
def health():
    return {"status": "ok"}
