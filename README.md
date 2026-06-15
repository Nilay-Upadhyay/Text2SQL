# Text2SQL

A lightweight Text-to-SQL planner built around a Groq-based LLM, Streamlit UI, and a PostgreSQL backend. The app converts natural language business questions into SQL queries using schema and business dictionary metadata, then validates and executes the generated SELECT statement safely.

## Key features

- Generate SQL from business questions using metadata-driven prompt engineering
- Load schema and business dictionary metadata from `src/metadata/generated/*.toon`
- **🆕 Dynamic schema retrieval with PGVector**: Intelligently select only relevant tables/columns using vector similarity, reducing token usage by 40-70%
- Enforce safe execution with a provider-side SQL validator that only allows single `SELECT` statements
- Execute SQL through SQLAlchemy and return results as pandas data frames
- Streamlit interface for interactive question input, query preview, and results display
- Optional Docker Compose setup for PostgreSQL and pgAdmin

## Repository structure

- `streamlit_app.py` — main Streamlit application entry point
- `src/planner/planner.py` — build prompts, call Groq, and extract SQL from model responses
- `src/planner/prompts.py` — planner prompt template used by the LLM
- `src/planner/metadata_loader.py` — loads schema and business dictionary metadata from `.toon` or `.json` files
- `src/db/executor.py` — database connection and SQL execution layer
- `src/db/validator.py` — SQL validation layer that blocks non-SELECT or multi-statement SQL
- `src/metadata/generated/` — generated metadata assets used to instruct the planner
- `src/metadata/embedding_manager.py` — **[NEW]** Groq-based embedding generation for vectors
- `src/metadata/vector_retriever.py` — **[NEW]** PGVector-based schema retrieval with semantic search
- `src/metadata/migrate_pgvector.py` — **[NEW]** Migration script to index schema into PGVector
- `docker-compose.yml` — optional local PostgreSQL + pgAdmin service definitions

### Documentation Files
- `IMPLEMENTATION_SUMMARY.md` — complete implementation overview and architecture
- `DYNAMIC_SCHEMA_README.md` — comprehensive guide to the dynamic schema feature
- `SETUP_PGVECTOR.md` — step-by-step setup and troubleshooting guide
- `QUICK_REFERENCE.md` — quick reference for common commands and configuration
- `.env.example` — configuration template with all available options
- `example_dynamic_schema.py` — example usage with sample queries
- `validate_pgvector_setup.py` — validation script to verify setup

## Setup

1. Install PostgreSQL and PGVector extension

```bash
# macOS
brew install postgresql pgvector

# Linux
sudo apt-get install postgresql postgresql-contrib
# For pgvector, either:
sudo apt-get install postgresql-<version>-pgvector
# Or build from source: https://github.com/pgvector/pgvector

# Docker
docker compose up -d  # includes PostgreSQL (pgvector pre-installed in latest images)
```

2. Install Python dependencies

```bash
python3 -m pip install -e .
```

> Or install individually:

```bash
python3 -m pip install python-dotenv pandas psycopg[binary] requests sqlalchemy sqlparse streamlit pgvector
```

3. Create a `.env` file in the repository root with the required settings:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=mixtral-8x7b-32768
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/database_name

# Optional: Dynamic schema retrieval (default: enabled)
USE_DYNAMIC_SCHEMA=true
SCHEMA_CONFIDENCE_THRESHOLD=0.3
GROQ_EMBEDDING_MODEL=mixtral-8x7b-32768
```

Alternatively, use `POSTGRES_*` variables if `DATABASE_URL` is not provided:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_DB=text2sql
```

4. **[NEW] Set up dynamic schema retrieval (optional but recommended)**

```bash
# Initialize PGVector indexes for faster retrieval
python -m src.metadata.migrate_pgvector

# Verify setup
python validate_pgvector_setup.py
```

See [SETUP_PGVECTOR.md](SETUP_PGVECTOR.md) for detailed instructions.

5. Start the Streamlit app

```bash
streamlit run streamlit_app.py
```

## Usage

- Open the Streamlit UI in your browser
- Enter a business question in the text area
- Click **Generate Query** to create SQL
- The generated query is shown in the UI
- The app executes the SQL and displays query results

## How it works

1. `streamlit_app.py` collects the user question and triggers `plan_query()`
2. **[NEW] Dynamic Schema Retrieval (if enabled)**:
   - User query is converted to a vector embedding using Groq API
   - Vector similarity search finds relevant tables/columns in PGVector
   - Confidence score determines if retrieved schema or full schema is used
   - Only selected schema is passed to the LLM (40-70% token reduction)
3. `src/planner/planner.py` constructs the prompt using (optionally filtered) metadata from `src/planner/metadata_loader.py`
4. The planner sends the prompt to the Groq API and extracts SQL from the model response
5. Generated SQL is passed to `src/db/executor.py`
6. `src/db/validator.py` validates that the SQL is a single `SELECT` statement
7. If valid, SQL is executed against the configured database and results are displayed

For more details on the dynamic schema feature, see [DYNAMIC_SCHEMA_README.md](DYNAMIC_SCHEMA_README.md)

## Security

- The executor layer validates SQL before execution
- Only one single statement is allowed
- Only `SELECT` queries are permitted
- This reduces the risk of SQL injection and malicious modifications

## Development

- Modify prompt templates in `src/planner/prompts.py`
- Add or update metadata in `src/metadata/generated/`
- Extend validation rules in `src/db/validator.py`
- Use `docker compose up -d` to start PostgreSQL and pgAdmin if desired
