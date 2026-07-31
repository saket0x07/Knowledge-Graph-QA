from typing import List
from models.schema import EntityModel, RelationshipModel
from db.neo4j_client import get_neo4j_client
import re

def merge_entities_and_relations(chunk_id: str, entities: List[EntityModel], relationships: List[RelationshipModel]):
    """Insert extracted entities and relationships into Neo4j and link them to the source chunk."""
    if not entities:
        return
        
    client = get_neo4j_client()
    
    query = """
    // 1. Create/Merge all entities
    UNWIND $entities AS ent
    MERGE (e:Entity {id: ent.id})
    SET e.name = ent.name, e.type = ent.type
    
    // 2. Link the chunk to all extracted entities
    WITH ent
    MATCH (c:Chunk {chunk_id: $chunk_id})
    MATCH (e:Entity {id: ent.id})
    MERGE (c)-[:MENTIONS]->(e)
    """
    
    with client.driver.session() as session:
        session.run(query, {
            "chunk_id": chunk_id,
            "entities": [e.model_dump() for e in entities]
        })
        
        # 3. Create relationships between entities
        if relationships:
            for rel in relationships:
                # Sanitize relation type to prevent Cypher injection
                safe_type = re.sub(r'[^A-Z0-9_]', '', rel.relation_type.upper().replace(" ", "_"))
                if not safe_type:
                    continue
                    
                q = f"""
                MATCH (source:Entity {{id: $source_id}})
                MATCH (target:Entity {{id: $target_id}})
                MERGE (source)-[:{safe_type}]->(target)
                """
                session.run(q, {"source_id": rel.source_entity_id, "target_id": rel.target_entity_id})
