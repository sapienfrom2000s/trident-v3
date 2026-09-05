import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(".env.development")

app = FastAPI(title=os.environ.get("APP_NAME", "Trident API"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
