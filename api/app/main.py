import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from kubernetes.client.exceptions import ApiException

from app.k8s import load_k8s_config
from app.runs import CreateRunRequest, RunDetail, RunSummary, create_run, get_run, list_runs

load_dotenv(".env.development")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    load_k8s_config()
    yield


app = FastAPI(title=os.environ.get("APP_NAME", "Trident API"), lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runs")
def get_runs() -> list[RunSummary]:
    return list_runs()


@app.get("/runs/{name}")
def get_run_detail(name: str) -> RunDetail:
    try:
        return get_run(name)
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="PipelineRun not found") from e
        raise


@app.post("/runs", status_code=201)
def post_run(req: CreateRunRequest) -> RunSummary:
    try:
        return create_run(req)
    except ApiException as e:
        if e.status == 409:
            raise HTTPException(status_code=409, detail="PipelineRun already exists") from e
        raise
