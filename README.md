# Text2SQL

A lightweight Text-to-SQL planner built around a Groq-based LLM, Streamlit UI, and a PostgreSQL backend. The app converts natural language business questions into SQL queries using schema and business dictionary metadata, then validates and executes the generated SELECT statement safely.

## Key features

- Generate SQL from business questions using metadata-driven prompt engineering
- Load schema and business dictionary metadata from `src/metadata/generated/*.toon`
- Enforce safe execution with a provider-side SQL validator that only allows single `SELECT` statements
- Execute SQL through SQLAlchemy and return results as pandas data frames
- Streamlit interface for interactive question input, query preview, and results display
- Optional Docker Compose setup for PostgreSQL and pgAdmin

## Repository structure

- `streamlit_app.py` — main Streamlit application entry point
- `src/planner/planner.py` — build prompts, call Groq, and extract SQL from model responses
- `src/planner/prompts.py` — planner prompt template used by the LLM
- `src/planner/metadata_loader.py` — loads schema and business dictionary metadata from `.toon` files
- `src/db/executor.py` — database connection and SQL execution layer
- `src/db/validator.py` — SQL validation layer that blocks non-SELECT or multi-statement SQL
- `src/metadata/generated/` — generated metadata assets used to instruct the planner
- `docker-compose.yml` — optional local PostgreSQL + pgAdmin service definitions

## Setup

1. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

> If `requirements.txt` is not present, install from `pyproject.toml`:

```bash
python3 -m pip install python-dotenv pandas psycopg[binary] requests sqlalchemy sqlparse streamlit
```

2. Create a `.env` file in the repository root with the required settings:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_groq_model
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/database_name
```

Alternatively, use `POSTGRES_*` variables if `DATABASE_URL` is not provided:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_DB=text2sql
```

3. Start PostgreSQL locally if needed

```bash
docker compose up -d
```

4. Run the Streamlit app

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
2. `src/planner/planner.py` constructs the prompt using metadata from `src/planner/metadata_loader.py`
3. The planner sends the prompt to the Groq API and extracts SQL from the model response
4. Generated SQL is passed to `src/db/executor.py`
5. `src/db/validator.py` validates that the SQL is a single `SELECT` statement
6. If valid, SQL is executed against the configured database and results are displayed

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
