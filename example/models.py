from typing import List, Optional
from pydantic import BaseModel, Field

class Paper(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    likes: int
    comments: int
    tags: List[str] = Field(default_factory=list)
    aiNotes: Optional[list[str]] = None
    badges: Optional[list[str]] = None

class PaperListResp(BaseModel):
    items: list[Paper]
    total: int
