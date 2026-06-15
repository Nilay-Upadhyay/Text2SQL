PLANNER_PROMPT = """
You are a postgresql database query planner.

Your job is to generate SQL.

Your response must be valid JSON and contain only the structured response object. Do not include any extra explanatory text.

You will be given a user question and database metadata in toon format, which includes the database schema and a business dictionary that defines key business terms and their mappings to the underlying database structure.
"""


def get_dynamic_schema_prompt(confidence: float, retrieval_method: str) -> str:
    """Get a prompt suffix based on dynamic schema retrieval context.
    
    Args:
        confidence: Confidence score of the retrieval (0-1)
        retrieval_method: Method used (dynamic, fallback, full, etc.)
        
    Returns:
        Additional prompt text for the LLM
    """
    if retrieval_method == "dynamic" and confidence > 0.7:
        return """
NOTE: The schema provided below has been dynamically selected based on relevance to your question.
This is a subset of the full database schema, containing only the most relevant tables and columns.
If you need other tables, mention them explicitly and they will be included.
"""
    elif retrieval_method in ("fallback", "error_fallback"):
        return """
NOTE: The complete database schema is provided below.
The schema retrieval system could not confidently filter to relevant tables, so full schema context is provided.
"""
    else:
        return ""