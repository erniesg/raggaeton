from typing import List, Dict, Any
from datetime import datetime
from llama_index.core import Document
from llama_index.core import SummaryIndex, VectorStoreIndex
import logging

logger = logging.getLogger(__name__)


def convert_to_documents(data: List[Dict[str, Any]]) -> List[Document]:
    documents = []
    for item in data:
        # Convert datetime objects to strings
        for key in ["date_gmt", "modified_gmt"]:
            if isinstance(item[key], datetime):
                item[key] = item[key].isoformat()
        doc = Document(
            text=item["md_content"],
            metadata={
                "id": item["id"],
                "title": item["title"],
                "date_gmt": item["date_gmt"],
                "modified_gmt": item["modified_gmt"],
                "link": item["link"],
                "status": item["status"],
                "excerpt": item.get("excerpt", ""),
                "author_id": item["author_id"],
                "author_first_name": item["author_first_name"],
                "author_last_name": item["author_last_name"],
                "editor": item.get("editor", ""),
                "comments_count": item.get("comments_count", 0),
            },
        )
        documents.append(doc)
    return documents


def create_indices(vector_store, documents):
    # Create the vector index
    vector_index = VectorStoreIndex.from_vector_store(vector_store)
    logger.info("Vector index created from vector store")

    # Create the summary index
    summary_index = SummaryIndex.from_documents(documents)
    logger.info("Summary index created from documents")

    return vector_index, summary_index
