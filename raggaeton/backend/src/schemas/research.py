from pydantic import BaseModel
from typing import List, Dict, Optional, Union, Any
from .common import OptionalParams


class GenerateResearchQuestionsRequest(BaseModel):
    topics: Union[List[str], List[List[str]]]
    article_types: Union[List[str], List[List[str]]]
    platforms: Union[List[str], List[List[str]]]
    optional_params: Optional[OptionalParams] = None


class DoResearchRequest(BaseModel):
    research_questions: List[
        Dict[str, Union[List[str], str]]
    ]  # Allow platform to be a string or list of strings
    optional_params: Optional[OptionalParams] = None


class ResearchQuestion(BaseModel):
    platform: str
    keywords: List[str]


class GenerateResearchQuestionsResponse(BaseModel):
    research_questions: List[ResearchQuestion]
    token_count: Optional[int] = None


class DoResearchResponse(BaseModel):
    fetched_research: Dict[str, Any]
    token_count: Optional[int] = None
