from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class DocumentModel(BaseModel):
    id: str = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="Name of the file")
    upload_timestamp: datetime = Field(default_factory=utc_now)

class ChunkModel(BaseModel):
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    document_id: str = Field(..., description="Foreign key to the parent Document")
    text: str = Field(..., description="The actual text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata like page numbers, section")

class EntityModel(BaseModel):
    id: str = Field(..., description="Normalized ID (e.g., openai)")
    name: str = Field(..., description="Display name")
    type: str = Field(..., description="Entity category (e.g., Organization, Model)")

class RelationshipModel(BaseModel):
    source_entity_id: str = Field(..., description="ID of the source entity")
    target_entity_id: str = Field(..., description="ID of the target entity")
    relation_type: str = Field(..., description="Action/Connection (e.g., USES)")
