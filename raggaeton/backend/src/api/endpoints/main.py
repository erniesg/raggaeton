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
from raggaeton.backend.src.api.endpoints.generate_topic_sentences import (
    router as generate_topic_sentences_router,
)
from raggaeton.backend.src.api.endpoints.generate_full_content import (
    router as generate_full_content_router,
)
from raggaeton.backend.src.api.endpoints.edit_content import (
    router as edit_content_router,
)

app = FastAPI()

# Include the router for the generate_research endpoints
app.include_router(generate_research_router, prefix="/api", tags=["research"])

# Include the router for the generate_headlines endpoints
app.include_router(generate_headlines_router, prefix="/api", tags=["headlines"])

# Include the router for the generate_draft endpoints
app.include_router(generate_draft_router, prefix="/api", tags=["drafts"])

# Include the router for the generate_topic_sentences endpoints
app.include_router(
    generate_topic_sentences_router, prefix="/api", tags=["topic_sentences"]
)

# Include the router for the generate_full_content endpoints
app.include_router(generate_full_content_router, prefix="/api", tags=["full_content"])

# Include the router for the edit_content endpoints
app.include_router(edit_content_router, prefix="/api", tags=["edit_content"])


@app.get("/")
async def root():
    return {"message": "Welcome to the RAGgaeton API"}
