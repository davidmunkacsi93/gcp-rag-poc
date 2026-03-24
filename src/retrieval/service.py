from fastapi import FastAPI
from pydantic import BaseModel

from src.retrieval.pipeline import retrieve

app = FastAPI(title="RAG Retrieval Service")


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
