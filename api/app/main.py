import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.k8s import load_k8s_config

load_dotenv(".env.development")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    load_k8s_config()
    yield


app = FastAPI(title=os.environ.get("APP_NAME", "Trident API"), lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
