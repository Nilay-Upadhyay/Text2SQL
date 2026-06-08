import pandas as pd
from sqlalchemy import create_engine

sqlite_engine = create_engine(
    "sqlite:///data/olist.sqlite"
)

postgres_engine = create_engine(
    "postgresql+psycopg://postgres:text2sql_pgadmin@localhost:5432/text2sql"
)

tables = pd.read_sql(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    """,
    sqlite_engine,
)

for table in tables["name"]:
    df = pd.read_sql(f"SELECT * FROM {table}", sqlite_engine)

    df.to_sql(
        table,
        postgres_engine,
        if_exists="replace",
        index=False,
    )