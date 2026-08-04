import os
import uuid
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.parsers import parse_pdf
from models.schema import DocumentModel, ChunkModel
from db.neo4j_client import get_neo4j_client
from services.vector_store import get_vector_store
from services.extraction import extract_knowledge_from_chunk, aextract_knowledge_from_chunk
from services.graph_builder import merge_entities_and_relations
import asyncio
from db.sqlite_client import update_ingestion_status

processing_status: Dict[str, str] = {}

def save_to_neo4j(doc: DocumentModel, chunks: List[ChunkModel]):
    """Save Document and Chunks to Neo4j and create relationships."""
    client = get_neo4j_client()
    
    query = """
    MERGE (d:Document {id: $doc_id})
    SET d.filename = $filename, d.upload_timestamp = datetime($timestamp)
    
    WITH d
    UNWIND $chunks AS chunk_data
    MERGE (c:Chunk {chunk_id: chunk_data.chunk_id})
    SET c.text = chunk_data.text,
        c.page_number = chunk_data.metadata.page_number,
        c.source = chunk_data.metadata.source
    
    MERGE (d)-[:HAS_CHUNK]->(c)
    
    WITH d
    MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
    WITH c ORDER BY c.page_number, c.chunk_id
    WITH collect(c) AS chunk_list
    UNWIND range(0, size(chunk_list)-2) AS i
    WITH chunk_list[i] AS c1, chunk_list[i+1] AS c2
    MERGE (c1)-[:NEXT_CHUNK]->(c2)
    """
    
    parameters = {
        "doc_id": doc.id,
        "filename": doc.filename,
        "timestamp": doc.upload_timestamp.isoformat(),
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "metadata": c.metadata
            } for c in chunks
        ]
    }
    
    with client.driver.session() as session:
        session.run(query, parameters)

async def process_chunks_async(chunk_models):
    """Process chunks concurrently with a limit of 10 at a time to prevent rate limits."""
    semaphore = asyncio.Semaphore(10)
    
    async def process_single_chunk(chunk):
        async with semaphore:
            result = await aextract_knowledge_from_chunk(chunk.text)
            return chunk.chunk_id, result
            
    tasks = [process_single_chunk(c) for c in chunk_models]
    results = await asyncio.gather(*tasks)
    
    # Save to Neo4j sequentially to avoid database locking/deadlocks
    for chunk_id, extraction_result in results:
        if extraction_result.entities:
            merge_entities_and_relations(
                chunk_id=chunk_id,
                entities=extraction_result.entities,
                relationships=extraction_result.relationships
            )

def process_document(file_path: str):
    """
    Main orchestration function for Ingestion and Graph Building.
    """
    filename = os.path.basename(file_path)
    processing_status[filename] = "processing"
    try:
   
        if not file_path.lower().endswith(".pdf"):
            raise ValueError("Only PDF is supported currently")
            
        pages = parse_pdf(file_path)
        
      
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        

        doc_id = str(uuid.uuid4())
        document = DocumentModel(id=doc_id, filename=filename)
        
        # 4. Chunking
        chunk_models = []
        for page in pages:
            chunks = text_splitter.split_text(page["text"])
            for idx, chunk_text in enumerate(chunks):
                chunk_id = f"{doc_id}_p{page['page_number']}_c{idx}"
                chunk = ChunkModel(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    text=chunk_text,
                    metadata={
                        "page_number": page["page_number"],
                        "source": page["source"]
                    }
                )
                chunk_models.append(chunk)
                

        if chunk_models:
            save_to_neo4j(document, chunk_models)
            
            vector_store = get_vector_store()
            vector_store.add_chunks(chunk_models)
            

            asyncio.run(process_chunks_async(chunk_models))
            
        print(f"Successfully finished processing document: {file_path}")
        processing_status[filename] = "completed"
        update_ingestion_status(filename, "Success")
        return document, chunk_models

    except Exception as e:
        processing_status[filename] = f"error: {str(e)}"
        update_ingestion_status(filename, "Failed")
        print(f"Error processing document {file_path}: {e}")
        return None, None
