from fastapi import FastAPI
from raggaeton.backend.src.api.endpoints.generate_research import (
    router as generate_research_router,
)

app = FastAPI()

# Include the router for the generate_research endpoints
app.include_router(generate_research_router, prefix="/api", tags=["research"])


@app.get("/")
async def root():
    return {"message": "Welcome to the Research API"}
