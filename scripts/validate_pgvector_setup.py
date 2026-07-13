"""Validation script for PGVector dynamic schema setup."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment
load_dotenv()


def check_environment():
    """Check all required environment variables."""
    print("🔍 Checking Environment Configuration...")
    print("-" * 60)

    required = {
        "GROQ_API_KEY": "Groq API key",
        "GROQ_MODEL": "Groq model name",
    }

    optional = {
        "USE_DYNAMIC_SCHEMA": "Enable dynamic schema (default: true)",
        "SCHEMA_CONFIDENCE_THRESHOLD": "Schema confidence threshold (default: 0.3)",
        "GROQ_EMBEDDING_MODEL": "Embedding model (defaults to GROQ_MODEL)",
    }

    database = {
        "POSTGRES_HOST": "Database host",
        "POSTGRES_PORT": "Database port",
        "POSTGRES_DB": "Database name",
        "POSTGRES_USER": "Database user",
    }

    errors = []
    warnings = []

    for key, desc in required.items():
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: {desc}")
        else:
            errors.append(f"❌ {key}: {desc} - NOT SET")

    print()
    for key, desc in optional.items():
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: {desc} = {value}")
        else:
            print(f"⚠️  {key}: {desc} (using default)")

    print()
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print(f"✅ DATABASE_URL: Using connection string")
    else:
        all_set = all(os.getenv(k) for k in database.keys())
        if all_set:
            print(f"✅ Database: Using POSTGRES_* variables")
        else:
            missing = [k for k in database.keys() if not os.getenv(k)]
            errors.append(f"❌ Missing database config: {', '.join(missing)}")

    return errors, warnings


def check_dependencies():
    """Check if required Python packages are installed."""
    print("\n🔍 Checking Python Dependencies...")
    print("-" * 60)

    packages = {
        "pgvector": "PGVector support",
        "sqlalchemy": "Database ORM",
        "psycopg": "PostgreSQL adapter",
        "requests": "HTTP client",
        "dotenv": "Environment variables",
    }

    errors = []

    for package, desc in packages.items():
        try:
            __import__(package)
            print(f"✅ {package}: {desc}")
        except ImportError:
            errors.append(f"❌ {package}: {desc} - NOT INSTALLED")

    return errors


def check_database_connection():
    """Check database connection."""
    print("\n🔍 Checking Database Connection...")
    print("-" * 60)

    try:
        from src.db.executor import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Database connection: OK")
            return []
    except Exception as e:
        return [f"❌ Database connection: {str(e)}"]


def check_pgvector_extension():
    """Check if pgvector extension is available."""
    print("\n🔍 Checking PGVector Extension...")
    print("-" * 60)

    try:
        from sqlalchemy import text

        from src.db.executor import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            # Try to enable extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("✅ PGVector extension: Available")

            # Check version
            result = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
            version = result.scalar()
            if version:
                print(f"   Version: {version}")

            return []
    except Exception as e:
        if "does not exist" in str(e).lower():
            return [
                f"❌ PGVector extension: NOT INSTALLED",
                "   Install with: brew install pgvector (macOS)",
                "   or: sudo apt-get install postgresql-<version>-pgvector (Linux)",
            ]
        return [f"❌ PGVector extension: {str(e)}"]


def check_vector_tables():
    """Check if vector metadata table exists."""
    print("\n🔍 Checking Vector Metadata Table...")
    print("-" * 60)

    try:
        from sqlalchemy import text

        from src.db.executor import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM schema_metadata_vectors")
            )
            count = result.scalar()
            print(f"✅ Vector metadata table: EXISTS")
            print(f"   Indexed entries: {count}")

            if count == 0:
                return ["⚠️  No entries indexed - run: python -m src.metadata.migrate_pgvector"]

            return []
    except Exception as e:
        if "does not exist" in str(e).lower():
            return [
                "⚠️  Vector metadata table: DOES NOT EXIST",
                "   Run setup: python -m src.metadata.migrate_pgvector",
            ]
        return [f"❌ Vector table check: {str(e)}"]


def check_groq_connection():
    """Check Groq API connection."""
    print("\n🔍 Checking Groq API Connection...")
    print("-" * 60)

    try:
        from src.metadata.embedding_manager import EmbeddingManager

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return ["❌ GROQ_API_KEY not set"]

        manager = EmbeddingManager()
        # Test with a simple embedding
        embedding = manager.get_embedding("test")
        print("✅ Groq API connection: OK")
        print(f"   Embedding dimension: {len(embedding)}")
        return []
    except Exception as e:
        return [f"❌ Groq API connection: {str(e)}"]


def main():
    """Run all checks."""
    print("\n" + "=" * 60)
    print("📋 PGVector Dynamic Schema Setup Validation")
    print("=" * 60)

    all_errors = []
    all_warnings = []

    # Run all checks
    env_errors, env_warnings = check_environment()
    all_errors.extend(env_errors)
    all_warnings.extend(env_warnings)

    dep_errors = check_dependencies()
    all_errors.extend(dep_errors)

    # Only check further if dependencies are OK
    if not any("pgvector" in e.lower() or "psycopg" in e.lower() for e in dep_errors):
        db_errors = check_database_connection()
        all_errors.extend(db_errors)

        if not db_errors:
            pgv_errors = check_pgvector_extension()
            all_errors.extend(pgv_errors)

            vec_errors = check_vector_tables()
            all_errors.extend(vec_errors)
            all_warnings.extend([e for e in vec_errors if e.startswith("⚠️")])

        groq_errors = check_groq_connection()
        all_errors.extend(groq_errors)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Validation Summary")
    print("=" * 60)

    if all_errors:
        print(f"\n❌ {len(all_errors)} error(s) found:")
        for error in all_errors:
            print(f"   {error}")

    if all_warnings:
        print(f"\n⚠️  {len(all_warnings)} warning(s):")
        for warning in all_warnings:
            print(f"   {warning}")

    if not all_errors and not all_warnings:
        print("\n✅ All checks passed! System is ready for dynamic schema retrieval.")
        return 0
    elif not all_errors:
        print("\n✅ All critical checks passed. Warnings above are informational.")
        return 0
    else:
        print("\n❌ Please fix the errors above before proceeding.")
        print("\nFor help, see: SETUP_PGVECTOR.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
