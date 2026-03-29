import logging
import time
import uuid

from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.generation.pipeline import generate
from src.retrieval.pipeline import retrieve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Generation Service")


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


class GenerateRequest(BaseModel):
    query: str


class CitationResponse(BaseModel):
    source_key: str
    doc_id: str
    section: str
    type: str
    generated_sql: str


class GenerateResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    model: str
    prompt_tokens: int


@app.post("/generate", response_model=GenerateResponse)
def generate_endpoint(request: GenerateRequest) -> GenerateResponse:
    context = retrieve(request.query)
    result = generate(request.query, context)
    return GenerateResponse(
        answer=result.answer,
        citations=[
            CitationResponse(
                source_key=c.source_key,
                doc_id=c.doc_id,
                section=c.section,
                type=c.type,
                generated_sql=c.generated_sql,
            )
            for c in result.citations
        ],
        model=result.model,
        prompt_tokens=result.prompt_tokens,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}
