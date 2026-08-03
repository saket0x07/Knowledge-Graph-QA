import os
from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from models.schema import EntityModel, RelationshipModel
from core.config import settings

class ExtractionResult(BaseModel):
    entities: List[EntityModel] = Field(description="List of extracted entities")
    relationships: List[RelationshipModel] = Field(description="List of extracted relationships between entities")

def get_llm():
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        raise ValueError("OPENROUTER_API_KEY is not set in .env")
        
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.1
    )

def extract_knowledge_from_chunk(text: str) -> ExtractionResult:
    """Extracts entities and relationships from a text chunk using OpenRouter."""
    try:
        llm = get_llm()
    except ValueError as e:
        print(f"Skipping extraction: {e}. Please add your key to .env!")
        return ExtractionResult(entities=[], relationships=[])
        
    structured_llm = llm.with_structured_output(ExtractionResult)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert data scientist and knowledge graph builder. 
        Your task is to extract meaningful entities and the relationships between them from the provided text.
        Entities should be normalized (e.g., 'Open AI', 'openai' -> 'openai').
        
        DYNAMIC ONTOLOGY EXTRACTION:
        Dynamically discover and infer relevant Entity Types and Relationship Types based on the context of the text chunk.
        - Use PascalCase for Entity Types (e.g., Disease, Player, Contract).
        - Use UPPER_SNAKE_CASE for Relationship Types (e.g., HAS_RISK_FACTOR, PLAYS_FOR, SIGNED_BY).
        
        If no meaningful entities or relationships are found, return empty lists.
        """),
        ("human", "Extract knowledge from this text:\n\n{text}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        print("Extracting entities...")
        result = chain.invoke({"text": text})
        return result
    except Exception as e:
        print(f"Error during extraction: {e}")
        # Return empty result on failure
        return ExtractionResult(entities=[], relationships=[])

async def aextract_knowledge_from_chunk(text: str) -> ExtractionResult:
    """Async extracts entities and relationships from a text chunk using OpenRouter."""
    try:
        llm = get_llm()
    except ValueError as e:
        print(f"Skipping extraction: {e}. Please add your key to .env!")
        return ExtractionResult(entities=[], relationships=[])
        
    structured_llm = llm.with_structured_output(ExtractionResult)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert data scientist and knowledge graph builder. 
        Your task is to extract meaningful entities and the relationships between them from the provided text.
        Entities should be normalized (e.g., 'Open AI', 'openai' -> 'openai').
        
        DYNAMIC ONTOLOGY EXTRACTION:
        Dynamically discover and infer relevant Entity Types and Relationship Types based on the context of the text chunk.
        - Use PascalCase for Entity Types (e.g., Disease, Player, Contract).
        - Use UPPER_SNAKE_CASE for Relationship Types (e.g., HAS_RISK_FACTOR, PLAYS_FOR, SIGNED_BY).
        
        If no meaningful entities or relationships are found, return empty lists.
        """),
        ("human", "Extract knowledge from this text:\n\n{text}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        print("Extracting entities (async)...")
        result = await chain.ainvoke({"text": text})
        return result
    except Exception as e:
        print(f"Error during async extraction: {e}")
        return ExtractionResult(entities=[], relationships=[])

