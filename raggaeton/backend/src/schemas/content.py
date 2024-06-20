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
    topics: List[str]
    context: Optional[Dict[str, Any]] = None
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
    draft_outlines: List[ContentBlock]
    optional_params: Optional[OptionalParams] = None


class GenerateDraftResponse(BaseModel):
    drafts: List[Draft]


class GenerateTopicSentencesRequest(Draft):
    # Inherits all fields from Draft
    pass


class TopicSentence(ContentBlock):
    # Inherits all fields from ContentBlock
    topic_sentences: List[str]  # Explicitly add topic_sentences


class GenerateTopicSentencesResponse(BaseModel):
    draft_outlines: List[
        TopicSentence
    ]  # Use TopicSentence to include details and topic_sentences


class Paragraph(TopicSentence):
    # Inherits all fields from TopicSentence
    paragraphs: List[str]  # Add paragraphs field


class GenerateFullContentRequest(Draft):
    draft_outlines: List[
        TopicSentence
    ]  # Use TopicSentence to include details and topic_sentences


class GenerateFullContentResponse(BaseModel):
    full_content: List[Paragraph]  # Use Paragraph to include paragraphs


class EditContentRequest(Draft):
    full_content_request: Optional[GenerateFullContentRequest] = None
    full_content_response: Optional[GenerateFullContentResponse] = None
    edit_type: str  # "structure" or "flair"


class EditedContentBlock(ContentBlock):
    topic_sentences: Optional[List[str]] = None
    paragraphs: Optional[List[str]] = None


class EditContentResponse(BaseModel):
    edited_content: List[EditedContentBlock]
