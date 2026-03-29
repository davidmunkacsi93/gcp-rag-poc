import logging
import time
import uuid

from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.retrieval.pipeline import retrieve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Retrieval Service")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())[:8]
    t0 = time.time()
    logger.info("[%s] → %s %s", cid, request.method, request.url.path)
    response = await call_next(request)
    ms = (time.time() - t0) * 1000
    logger.info("[%s] ← %d (%.0f ms)", cid, response.status_code, ms)
    response.headers["X-Correlation-ID"] = cid
    return response


class RetrieveRequest(BaseModel):
    query: str


class ContextItemResponse(BaseModel):
    type: str
    content: str
    source_ref: str
    score: float


class RetrieveResponse(BaseModel):
    items: list[ContextItemResponse]


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve_endpoint(request: RetrieveRequest) -> RetrieveResponse:
    context = retrieve(request.query)
    return RetrieveResponse(
        items=[
            ContextItemResponse(
                type=item.type,
                content=item.content,
                source_ref=item.source_ref,
                score=item.score,
            )
            for item in context.items
        ]
    )


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}
