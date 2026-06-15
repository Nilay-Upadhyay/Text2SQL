# Quick Reference: PGVector Dynamic Schema Retrieval

## Installation (2 minutes)
```bash
# 1. Install pgvector
brew install pgvector  # macOS
# OR: sudo apt-get install postgresql-<version>-pgvector  # Linux
# OR: Docker with pgvector pre-installed

# 2. Install Python package
pip install pgvector
pip install -e .  # Install all dependencies

# 3. Configure
cp .env.example .env
# Edit .env: add GROQ_API_KEY and database config
```

## Setup (3 minutes)
```bash
# 1. Verify setup
python validate_pgvector_setup.py

# 2. Index schema
python -m src.metadata.migrate_pgvector

# 3. Check indexing
python -c "import psycopg; conn = psycopg.connect(...); print(conn.execute('SELECT COUNT(*) FROM schema_metadata_vectors').fetchone())"
```

## Usage

### Streamlit App
```bash
streamlit run streamlit_app.py
# Feature works automatically - see confidence badge
```

### Python Script
```python
from src.planner.planner import load_config, plan_query

load_config()
sql, metadata = plan_query("Your question")

print(f"SQL: {sql}")
print(f"Confidence: {metadata['confidence']:.0%}")
print(f"Tables: {metadata['tables_selected']}")
```

### Command Line
```bash
python example_dynamic_schema.py
```

## Configuration

### Enable/Disable
```bash
# Enable (default)
USE_DYNAMIC_SCHEMA=true

# Disable (use full schema)
USE_DYNAMIC_SCHEMA=false
```

### Adjust Confidence Threshold
```bash
# More selective (40% reduction)
SCHEMA_CONFIDENCE_THRESHOLD=0.5

# Standard (50% reduction)  
SCHEMA_CONFIDENCE_THRESHOLD=0.3

# Aggressive (60% reduction)
SCHEMA_CONFIDENCE_THRESHOLD=0.1
```

### Embedding Model
```bash
# Use same model as LLM
GROQ_EMBEDDING_MODEL=mixtral-8x7b-32768

# Or use different model
GROQ_EMBEDDING_MODEL=llama-2-70b-chat
```

## Common Commands

### Re-index schema after changes
```bash
python -m src.metadata.migrate_pgvector --clear
```

### Check indexed entities
```sql
SELECT entity_type, COUNT(*) FROM schema_metadata_vectors GROUP BY entity_type;
```

### Monitor a query
```python
from src.planner.planner import load_config, plan_query
load_config()
sql, meta = plan_query("your query")
print(meta)  # See full retrieval metadata
```

### Troubleshoot low confidence
1. Lower threshold: `SCHEMA_CONFIDENCE_THRESHOLD=0.1`
2. Re-index: `python -m src.metadata.migrate_pgvector --clear`
3. Check Groq API: `python validate_pgvector_setup.py`

## Expected Performance

| Metric | Value |
|--------|-------|
| Token Reduction | 40-70% |
| Embedding Time | 200-500ms |
| Search Time | 50-100ms |
| Fallback Latency | +300ms |
| Confidence Range | 0.2-1.0 |

## Retrieval Methods

| Method | Trigger | When Used |
|--------|---------|-----------|
| `dynamic` | High confidence | Most queries on indexed schema |
| `fallback` | Low confidence | When vector search fails |
| `error_fallback` | Error during retrieval | System error occurred |
| `full` | Disabled | `USE_DYNAMIC_SCHEMA=false` |

## Environment Variables Checklist

Required:
- [ ] `GROQ_API_KEY`
- [ ] `GROQ_MODEL`
- [ ] `POSTGRES_DB` or `DATABASE_URL`

Optional:
- [ ] `USE_DYNAMIC_SCHEMA=true` (default)
- [ ] `SCHEMA_CONFIDENCE_THRESHOLD=0.3` (default)
- [ ] `GROQ_EMBEDDING_MODEL` (defaults to `GROQ_MODEL`)

## Diagnostics

### Full health check
```bash
python validate_pgvector_setup.py
```

### Test specific component
```python
# Test embeddings
from src.metadata.embedding_manager import EmbeddingManager
manager = EmbeddingManager()
emb = manager.get_embedding("test text")
print(f"Embedding dimension: {len(emb)}")

# Test vector search
from src.metadata.vector_retriever import VectorRetriever
retriever = VectorRetriever()
results = retriever.retrieve_relevant_schema("your query")
print(results)

# Test planner
from src.planner.planner import load_config, plan_query
load_config()
sql, meta = plan_query("your query")
print(f"Confidence: {meta['confidence']}")
```

## FAQ

**Q: How much token reduction will I see?**
A: Typically 40-70% depending on your schema size and query specificity.

**Q: Can I use a different embedding model?**
A: Yes, set `GROQ_EMBEDDING_MODEL` to any Groq model. You can also implement a custom `EmbeddingManager`.

**Q: What happens if vector search fails?**
A: System automatically falls back to full schema. No errors to user.

**Q: Do I need to re-index when schema changes?**
A: Yes, run: `python -m src.metadata.migrate_pgvector --clear`

**Q: Can I disable this feature?**
A: Yes, set `USE_DYNAMIC_SCHEMA=false` to always use full schema.

**Q: Does this work with existing code?**
A: Yes, return type of `plan_query()` changed to tuple. Unpack as: `sql, meta = plan_query(q)`

## Resources

- 📖 Full docs: [DYNAMIC_SCHEMA_README.md](DYNAMIC_SCHEMA_README.md)
- 🔧 Setup guide: [SETUP_PGVECTOR.md](SETUP_PGVECTOR.md)
- 📝 Examples: [example_dynamic_schema.py](example_dynamic_schema.py)
- 🎯 Summary: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## Support

For issues:
1. Run `python validate_pgvector_setup.py`
2. Check logs: `python example_dynamic_schema.py`
3. See [SETUP_PGVECTOR.md](SETUP_PGVECTOR.md) troubleshooting section
4. Review [DYNAMIC_SCHEMA_README.md](DYNAMIC_SCHEMA_README.md) for detailed info
