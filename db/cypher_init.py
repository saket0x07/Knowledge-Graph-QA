from db.neo4j_client import get_neo4j_client

def init_db_schema():
    """Initialize Neo4j constraints and indexes."""
    client = get_neo4j_client()
    
    cypher_commands = [
        "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
        "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
        "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
        "CREATE FULLTEXT INDEX chunk_text_index IF NOT EXISTS FOR (n:Chunk) ON EACH [n.text]",
        "CREATE FULLTEXT INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON EACH [e.name]"
    ]
    
    with client.driver.session() as session:
        for cmd in cypher_commands:
            try:
                session.run(cmd)
                print(f"Executed: {cmd}")
            except Exception as e:
                print(f"Failed to execute schema initialization command: {cmd}\nError: {e}")
