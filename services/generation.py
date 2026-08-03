from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.extraction import get_llm

def generate_answer(query: str, context: str) -> str:
    """
    Generates a natural language answer based ONLY on the provided context.
    """
    llm = get_llm()
    
    system_prompt = """You are a helpful, expert knowledge assistant. 
Your task is to answer the user's question based strictly on the provided context.

The context contains two types of information:
1. Semantic Context: Direct quotes from the source documents.
2. Relational Context: Structural facts from the Knowledge Graph.

CRITICAL RULES:
- Use ONLY the provided context to answer the question. Do not use outside knowledge.
- If the context does not contain enough information to answer the question, clearly state: "I don't have enough information to answer that based on the provided documents."
- Synthesize the semantic and relational context smoothly into a natural, easy-to-read response.
- Do not mention "semantic context" or "relational context" in your answer. Just answer the question directly.

CONTEXT:
{context}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    try:
        response = chain.invoke({
            "context": context,
            "question": query
        })
        return response
    except Exception as e:
        print(f"Error during generation: {e}")
        return "Sorry, I encountered an error while trying to generate the answer."
