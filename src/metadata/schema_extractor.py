import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

DATABASE_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)

OUTPUT_DIR = Path(__file__).parent / "generated"
OUTPUT_DIR.mkdir(exist_ok=True)


def extract_schema():
    query = text("""
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)

    schema = {}

    with engine.connect() as conn:
        rows = conn.execute(query)

        for row in rows:
            table_name = row.table_name
            column_name = row.column_name
            data_type = row.data_type

            if table_name not in schema:
                schema[table_name] = {
                    "columns": {}
                }

            schema[table_name]["columns"][column_name] = data_type

    return schema


def extract_primary_keys(schema):
    query = text("""
        SELECT
            tc.table_name,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_type = 'PRIMARY KEY';
    """)

    with engine.connect() as conn:
        rows = conn.execute(query)

        for row in rows:
            table_name = row.table_name
            column_name = row.column_name

            schema.setdefault(table_name, {})

            schema[table_name].setdefault(
                "primary_keys",
                []
            )

            schema[table_name]["primary_keys"].append(
                column_name
            )

    return schema


def extract_relationships():
    query = text("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY';
    """)

    relationships = []

    with engine.connect() as conn:
        rows = conn.execute(query)

        for row in rows:
            relationships.append(
                {
                    "from_table": row.table_name,
                    "from_column": row.column_name,
                    "to_table": row.foreign_table_name,
                    "to_column": row.foreign_column_name,
                }
            )

    return relationships


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


def main():
    print("Extracting schema...")

    schema = extract_schema()
    schema = extract_primary_keys(schema)

    relationships = extract_relationships()

    save_json(
        schema,
        OUTPUT_DIR / "schema.json"
    )

    save_json(
        relationships,
        OUTPUT_DIR / "relationships.json"
    )

    print("Done.")
    print(f"Schema tables: {len(schema)}")
    print(f"Relationships: {len(relationships)}")


if __name__ == "__main__":
    main()