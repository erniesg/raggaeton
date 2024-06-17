from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from .common import OptionalParams


class GenerateHeadlinesRequest(BaseModel):
    article_types: str
    topics: List[str]
    context: Optional[Dict[str, Any]] = None
    optional_params: Optional[OptionalParams] = None


class Headline(BaseModel):
    headline: str
    article_type: str
    hook: str
    thesis: str


class GenerateHeadlinesResponse(BaseModel):
    headlines: List[Headline]


class GenerateDraftRequest(BaseModel):
    headline: str
    hook: str
    thesis: str
    article_type: str
    optional_params: Optional[OptionalParams] = None


class ContentBlock(BaseModel):
    content_block: str
    details: str


class Draft(BaseModel):
    headline: str
    hook: str
    thesis: str
    article_type: str
    structure: List[ContentBlock]
    optional_params: Optional[OptionalParams] = None


class GenerateDraftResponse(BaseModel):
    drafts: List[Draft]
