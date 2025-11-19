from typing import List, Optional
from pydantic import BaseModel


class DiscardedFile(BaseModel):
    filename: str
    reason: str
    size_mb: Optional[float] = None


class UploadResponse(BaseModel):
    store_name: str
    accepted_files: List[str]
    discarded_files: List[DiscardedFile]


class Source(BaseModel):
    filename: str
    page: Optional[int] = None
    snippet: str


class QueryRequest(BaseModel):
    query: str
    prompt_profile: str = "default"


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
