from fastapi import FastAPI
from raggaeton.backend.src.api.endpoints.generate_research import (
    router as generate_research_router,
)
from raggaeton.backend.src.api.endpoints.generate_headlines import (
    router as generate_headlines_router,
)
from raggaeton.backend.src.api.endpoints.generate_draft import (
    router as generate_draft_router,
)

app = FastAPI()

# Include the router for the generate_research endpoints
app.include_router(generate_research_router, prefix="/api", tags=["research"])

# Include the router for the generate_headlines endpoints
app.include_router(generate_headlines_router, prefix="/api", tags=["headlines"])

# Include the router for the generate_draft endpoints
app.include_router(generate_draft_router, prefix="/api", tags=["drafts"])


@app.get("/")
async def root():
    return {"message": "Welcome to the RAGgaeton API"}
