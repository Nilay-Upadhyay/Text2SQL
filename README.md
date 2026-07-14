# Enterprise Text2SQL Platform

An enterprise-ready Text-to-SQL platform that converts natural language into secure PostgreSQL queries using LLMs, dynamic schema retrieval, and fine-grained authorization.

The platform is designed for large enterprise databases where exposing the complete schema to an LLM is impractical or violates security requirements.

---

# Features

- Natural language to PostgreSQL SQL generation
- Dynamic schema retrieval using PGVector
- Metadata-driven query planning
- Business dictionary based semantic understanding
- Fine-grained metadata authorization using SpiceDB
- Secure SQL validation (SELECT only)
- PostgreSQL execution layer
- Streamlit web interface
- Modular architecture for enterprise deployment

---

# Architecture

```
                    User Question
                          │
                          ▼
              Dynamic Schema Retrieval
                     (PGVector)
                          │
                          ▼
              Metadata Authorization
                     (SpiceDB)
                          │
                          ▼
              Authorized Metadata
                          │
                          ▼
                   LLM Query Planner
                          │
        ┌─────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
   SQL Generated           Insufficient Authorization /
                                  Out Of Scope
        │
        ▼
   SQL Validation
        │
        ▼
 PostgreSQL Database
```

---

# Repository Structure

```
streamlit_app.py                Streamlit application

src/
├── authorization/              SpiceDB integration
├── db/                         Database execution and validation
├── metadata/                   Metadata management and PGVector retrieval
├── planner/                    Prompt generation and LLM planning

docker-compose.yml
README.md
```

---

# Core Components

| Component | Responsibility |
|------------|---------------|
| PGVector | Dynamic schema retrieval |
| Metadata Loader | Loads schema and business metadata |
| SpiceDB | Metadata authorization |
| Planner | SQL generation |
| Validator | SQL safety validation |
| Executor | Database execution |

---

# Prerequisites

- Python 3.12+
- PostgreSQL
- PGVector Extension
- SpiceDB
- Groq API Key

---

# Installation

Clone the repository

```bash
git clone <repository>
cd text2sql
```

Install dependencies

```bash
pip install -e .
```

---

# Configuration

```bash
cp .env.example .env
```

Edit .env with your keys.

---

# Metadata Initialization

Generate and index metadata.

```bash
python -m src.metadata.migrate_pgvector
```

Seed SpiceDB relationships.

```bash
python -m src.authorization.seed_relationships
```

---

# Running the Application

```bash
docker compose up -d
```

```bash
streamlit run streamlit_app.py
```

---

# Security Model

The platform enforces multiple security layers.

- Dynamic metadata retrieval
- Metadata authorization through SpiceDB
- Prompt constrained to authorized metadata only
- SQL validation
- Read-only query execution
- No SQL approximation for unauthorized metadata

If the requested information cannot be generated from the authorized metadata, the planner returns:

- `INSUFFICIENT_AUTHORIZATION`
- `OUT_OF_SCOPE`

No SQL is generated in these scenarios.

---

# Development

Key locations:

```
src/planner/
src/metadata/
src/authorization/
src/db/
```

The system is designed so that retrieval, authorization, planning, validation, and execution remain independent modules.

---

# Technology Stack

- Python
- PostgreSQL
- PGVector
- SpiceDB
- Groq LLM
- SQLAlchemy
- Streamlit

---

# License

Internal Project