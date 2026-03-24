from fastapi import FastAPI
from pydantic import BaseModel

from src.generation.pipeline import generate
from src.retrieval.pipeline import retrieve

app = FastAPI(title="RAG Generation Service")


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
