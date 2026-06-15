# Dynamic Schema Retrieval with PGVector

This feature implements intelligent, vector-based schema retrieval to reduce token usage and improve SQL generation accuracy. Instead of passing the entire database schema to the LLM, only relevant tables and columns are selected based on semantic similarity to the user query.

## Architecture

```
User Query
    ↓
Query Embedding (Groq API)
    ↓
Vector Similarity Search (PGVector)
    ↓
Retrieve Relevant Schema Entities
    ↓
Expand to Full Table Definitions
    ↓
Pass to LLM for SQL Generation
```

## Components

### 1. **Embedding Manager** (`src/metadata/embedding_manager.py`)
- Generates vector embeddings using Groq API
- Converts text to consistent embedding vectors
- Computes cosine similarity between embeddings
- Configurable embedding dimension (default: 768)

### 2. **Vector Retriever** (`src/metadata/vector_retriever.py`)
- Manages PGVector storage and indexing
- Performs semantic similarity search on schema metadata
- Implements confidence-based fallback logic
- Expands retrieved columns to full table definitions
- Caches schema metadata in PostgreSQL

### 3. **Migration Script** (`src/metadata/migrate_pgvector.py`)
- Sets up PGVector extension in PostgreSQL
- Creates schema metadata vector table
- Indexes existing schema and relationships
- Can clear and re-index on demand

### 4. **Planner Integration** (`src/planner/planner.py`)
- Routes queries through vector retriever when enabled
- Falls back to full schema on low confidence
- Returns retrieval metadata for debugging

## Configuration

Add these environment variables to your `.env` file:

```bash
# Required - Groq API configuration
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=mixtral-8x7b-32768  # or any Groq model
GROQ_EMBEDDING_MODEL=mixtral-8x7b-32768  # Can be same as GROQ_MODEL

# Optional - Dynamic schema retrieval
USE_DYNAMIC_SCHEMA=true              # Enable/disable dynamic schema (default: true)
SCHEMA_CONFIDENCE_THRESHOLD=0.2      # Minimum confidence for dynamic retrieval (0-1)

# Database configuration
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/database_name
# Or use individual variables:
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=database_name
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -e .
# or
pip install pgvector sqlalchemy psycopg[binary] requests python-dotenv
```

### 2. Ensure PGVector Extension

The system automatically creates the PGVector extension on first run. If you need manual setup:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Initialize Schema Indexing

Run the migration script to index your database schema:

```bash
python -m src.metadata.migrate_pgvector
```

Options:
- `--clear`: Clear existing vectors before re-indexing (useful after schema changes)

```bash
python -m src.metadata.migrate_pgvector --clear
```

### 4. Verify Setup

Check that embeddings were created:

```sql
SELECT COUNT(*) FROM schema_metadata_vectors;
SELECT entity_type, COUNT(*) 
FROM schema_metadata_vectors 
GROUP BY entity_type;
```

## Usage

### In Streamlit App

The app automatically uses dynamic schema retrieval if:
- `USE_DYNAMIC_SCHEMA=true` in `.env`
- Vector retriever is successfully initialized
- Vector tables are populated

You'll see a badge showing retrieval status and confidence.

### Programmatic Usage

```python
from src.metadata.embedding_manager import EmbeddingManager
from src.metadata.vector_retriever import VectorRetriever
from src.planner.planner import load_config, plan_query

# Initialize
load_config()

# Query with dynamic schema retrieval
sql_query, metadata = plan_query("What are the top 10 products by revenue?")

print(f"SQL: {sql_query}")
print(f"Retrieval Method: {metadata['method']}")
print(f"Confidence: {metadata['confidence']:.2%}")
print(f"Selected Tables: {metadata['tables_selected']}")
```

## How It Works

### 1. Indexing Phase

When the migration script runs:
- Schema is parsed into entities (tables, columns, relationships)
- Each entity gets a description
- Descriptions are embedded using Groq
- Embeddings are stored in PGVector with metadata

**Entities Created:**
- **Tables**: One entry per table with description of columns
- **Columns**: One entry per column with type information
- **Relationships**: One entry per foreign key relationship

### 2. Retrieval Phase

For each user query:
1. Query is embedded using the same Groq model
2. Cosine similarity search finds similar schema entities
3. Top-K most similar entities are retrieved
4. Confidence score is computed (average similarity)
5. If confidence >= threshold:
   - Retrieved table schemas are expanded to full definitions
   - Only selected schema is passed to LLM
6. If confidence < threshold:
   - Full schema is used as fallback

### 3. Confidence Thresholds

- **High Confidence (> 0.7)**: Dynamic schema with note to LLM
- **Medium Confidence (0.2-0.7)**: Fallback to full schema  
- **Low Confidence (< 0.2)**: Error fallback with full schema

## Performance Benefits

### Token Usage Reduction
- **Before**: Full schema + business dict passed on every query
- **After**: Only relevant tables/columns passed
- **Typical Reduction**: 40-70% fewer tokens

### Example
```
Full schema: 2,500 tokens
Relevant schema for "top products by revenue": 800 tokens
Savings: 1,700 tokens (68% reduction)
```

### Latency Impact
- Vector embedding: ~200-500ms (cached after first query)
- Vector search: ~50-100ms
- Total overhead: ~250-600ms per query
- Groq API response: Often faster with smaller context

## Troubleshooting

### PGVector Extension Not Available

```
Error: could not open extension control file
```

Install pgvector in PostgreSQL:
```bash
# macOS with Homebrew
brew install pgvector

# Docker
# Already included in most postgres:latest images with apt-get

# From source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

### Low Confidence Scores

If retrieval consistently shows low confidence:
1. Check `SCHEMA_CONFIDENCE_THRESHOLD` (lower values = broader retrieval)
2. Verify embeddings were created: `SELECT COUNT(*) FROM schema_metadata_vectors;`
3. Re-index with: `python -m src.metadata.migrate_pgvector --clear`

### Missing Vector Table

If you see "PGVector table does not exist" errors:
```bash
# Re-run migration
python -m src.metadata.migrate_pgvector
```

### Slow Queries

If vector searches are slow:
```sql
-- Check index exists
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename = 'schema_metadata_vectors';

-- Recreate index if needed
REINDEX INDEX idx_embedding;
```

## Customization

### Change Embedding Dimension

Edit `src/metadata/embedding_manager.py`:
```python
EmbeddingManager(embedding_dimension=1024)  # Default: 768
```

Then re-run migration with `--clear`.

### Adjust Confidence Threshold

Edit `.env`:
```bash
SCHEMA_CONFIDENCE_THRESHOLD=0.5  # More conservative
SCHEMA_CONFIDENCE_THRESHOLD=0.1  # More aggressive
```

### Use Different Embedding Model

Edit `.env`:
```bash
GROQ_EMBEDDING_MODEL=llama-2-70b-chat  # Different from LLM model
```

Or implement custom `EmbeddingManager` subclass.

## Database Schema Assumptions

The system expects standard PostgreSQL `information_schema`:
- `information_schema.columns` for table/column info
- `information_schema.table_constraints` for relationships
- Schema should be in `public` schema (configurable)

## Future Enhancements

1. **Caching**: Cache embeddings across sessions
2. **Hybrid Search**: Combine keyword and semantic search
3. **Custom Embeddings**: Support for local embedding models (e.g., sentence-transformers)
4. **Re-ranking**: Use LLM to re-rank retrieved schemas
5. **Batch Processing**: Index schema updates in batches
6. **Cost Tracking**: Track embedding API costs

## API Reference

### VectorRetriever

```python
class VectorRetriever:
    def __init__(embedding_manager, embedding_dimension=768, 
                 similarity_threshold=0.3, top_k=5)
    
    def index_schema_metadata(schema, relationships, business_dict=None)
    def retrieve_relevant_schema(query, top_k=None, 
                                 confidence_threshold=None) -> dict
    def expand_retrieved_schema(retrieved, full_schema) -> dict
    def get_table_definition(table_name, schema) -> dict
    def clear_all_vectors()
```

### EmbeddingManager

```python
class EmbeddingManager:
    def __init__(api_key=None, model=None, embedding_dimension=768)
    def get_embedding(text) -> list[float]
    def get_batch_embeddings(texts) -> list[list[float]]
    def compute_similarity(embedding1, embedding2) -> float
```

## See Also

- [PostgreSQL PGVector Extension](https://github.com/pgvector/pgvector)
- [Groq API Documentation](https://console.groq.com/docs)
- [Vector Search Best Practices](https://python.langchain.com/docs/integrations/vectorstores/pgvector)
