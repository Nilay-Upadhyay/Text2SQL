"""Vector-based schema retriever using PGVector for dynamic metadata retrieval."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from sqlalchemy import Column, String, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

from src.db.executor import get_engine
from src.metadata.embedding_manager import EmbeddingManager

load_dotenv()

logger = logging.getLogger(__name__)

Base = declarative_base()


class SchemaMetadataVector:
    """Represents a schema metadata entry with vector embedding."""

    def __init__(
        self,
        id: str,
        entity_type: str,
        entity_name: str,
        description: str,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        embedding: Optional[list[float]] = None,
    ):
        """Initialize a schema metadata vector.
        
        Args:
            id: Unique identifier
            entity_type: Type of entity (table, column, relationship, etc.)
            entity_name: Name of the entity
            description: Description/definition of the entity
            table_name: Associated table name (for columns)
            column_name: Column name (if applicable)
            embedding: Vector embedding (will be computed if not provided)
        """
        self.id = id
        self.entity_type = entity_type
        self.entity_name = entity_name
        self.description = description
        self.table_name = table_name
        self.column_name = column_name
        self.embedding = embedding

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "description": self.description,
            "table_name": self.table_name,
            "column_name": self.column_name,
        }


class VectorRetriever:
    """Retrieves relevant schema metadata using vector similarity search."""

    def __init__(
        self,
        embedding_manager: Optional[EmbeddingManager] = None,
        embedding_dimension: int = 768,
        similarity_threshold: float = 0.3,
        top_k: int = 5,
    ):
        """Initialize the vector retriever.
        
        Args:
            embedding_manager: EmbeddingManager instance (creates new if None)
            embedding_dimension: Dimension of embeddings
            similarity_threshold: Minimum similarity score for inclusion
            top_k: Number of top results to return
        """
        self.embedding_manager = embedding_manager or EmbeddingManager(
            embedding_dimension=embedding_dimension
        )
        self.embedding_dimension = embedding_dimension
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.engine = get_engine()
        self._ensure_pgvector_extension()

    def _ensure_pgvector_extension(self) -> None:
        """Ensure pgvector extension is installed in PostgreSQL."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("PGVector extension ensured")
        except Exception as e:
            logger.warning(f"Could not ensure pgvector extension: {e}")

    def _create_tables(self) -> None:
        """Create the schema_metadata_vectors table if it doesn't exist."""
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS schema_metadata_vectors (
            id VARCHAR(255) PRIMARY KEY,
            entity_type VARCHAR(50) NOT NULL,
            entity_name VARCHAR(255) NOT NULL,
            table_name VARCHAR(255),
            column_name VARCHAR(255),
            description TEXT,
            embedding vector({self.embedding_dimension}),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_entity_type ON schema_metadata_vectors(entity_type);
        CREATE INDEX IF NOT EXISTS idx_table_name ON schema_metadata_vectors(table_name);
        CREATE INDEX IF NOT EXISTS idx_embedding ON schema_metadata_vectors USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """

        try:
            with self.engine.connect() as conn:
                for statement in create_table_query.split(";"):
                    if statement.strip():
                        conn.execute(text(statement))
                conn.commit()
                logger.info("Schema metadata vectors table created")
        except Exception as e:
            logger.warning(f"Could not create schema metadata vectors table: {e}")

    def index_schema_metadata(
        self, schema: dict, relationships: list[dict], business_dict: Optional[dict] = None
    ) -> None:
        """Index schema metadata into PGVector.
        
        Args:
            schema: Database schema dictionary (tables and columns)
            relationships: List of foreign key relationships
            business_dict: Optional business dictionary
        """
        self._create_tables()

        metadata_entries = []

        # Create entries for tables
        for table_name, table_info in schema.items():
            table_id = f"table_{table_name}"
            columns_desc = ", ".join(table_info.get("columns", {}).keys())
            description = f"Table {table_name} with columns: {columns_desc}"

            metadata_entries.append(
                SchemaMetadataVector(
                    id=table_id,
                    entity_type="table",
                    entity_name=table_name,
                    description=description,
                    table_name=table_name,
                )
            )

            # Create entries for columns
            for column_name, column_type in table_info.get("columns", {}).items():
                column_id = f"column_{table_name}_{column_name}"
                column_desc = f"{column_name} of type {column_type}"

                metadata_entries.append(
                    SchemaMetadataVector(
                        id=column_id,
                        entity_type="column",
                        entity_name=f"{table_name}.{column_name}",
                        description=column_desc,
                        table_name=table_name,
                        column_name=column_name,
                    )
                )

        # Create entries for relationships
        for rel in relationships:
            rel_id = f"relationship_{rel['from_table']}_{rel['from_column']}"
            description = (
                f"Foreign key: {rel['from_table']}.{rel['from_column']} -> "
                f"{rel['to_table']}.{rel['to_column']}"
            )

            metadata_entries.append(
                SchemaMetadataVector(
                    id=rel_id,
                    entity_type="relationship",
                    entity_name=f"{rel['from_table']}.{rel['from_column']}",
                    description=description,
                    table_name=rel["from_table"],
                )
            )

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(metadata_entries)} metadata entries")
        for entry in metadata_entries:
            text_to_embed = f"{entry.entity_name} {entry.description}"
            entry.embedding = self.embedding_manager.get_embedding(text_to_embed)

        # Store in database
        self._store_metadata_vectors(metadata_entries)
        logger.info(f"Indexed {len(metadata_entries)} metadata entries")

    def _store_metadata_vectors(self, entries: list[SchemaMetadataVector]) -> None:
        """Store metadata vectors in database.
        
        Args:
            entries: List of SchemaMetadataVector entries
        """
        insert_query = """
        INSERT INTO schema_metadata_vectors 
        (id, entity_type, entity_name, table_name, column_name, description, embedding)
        VALUES (:id, :entity_type, :entity_name, :table_name, :column_name, :description, :embedding)
        ON CONFLICT (id) DO UPDATE SET
            description = EXCLUDED.description,
            embedding = EXCLUDED.embedding,
            updated_at = CURRENT_TIMESTAMP;
        """

        try:
            with self.engine.connect() as conn:
                for entry in entries:
                    embedding_str = "[" + ",".join(str(x) for x in entry.embedding) + "]"
                    conn.execute(
                        text(insert_query),
                        {
                            "id": entry.id,
                            "entity_type": entry.entity_type,
                            "entity_name": entry.entity_name,
                            "table_name": entry.table_name,
                            "column_name": entry.column_name,
                            "description": entry.description,
                            "embedding": embedding_str,
                        },
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing metadata vectors: {e}")
            raise

    def retrieve_relevant_schema(
        self, query: str, top_k: Optional[int] = None, confidence_threshold: Optional[float] = None
    ) -> dict:
        """Retrieve relevant schema based on query similarity.
        
        Args:
            query: User query to match against schema
            top_k: Override default top_k
            confidence_threshold: Override default similarity threshold
            
        Returns:
            Dictionary containing relevant schema, tables, columns, and confidence
        """
        top_k = top_k or self.top_k
        confidence_threshold = confidence_threshold or self.similarity_threshold

        # Generate embedding for query
        query_embedding = self.embedding_manager.get_embedding(query)

        # Search for similar schema entities
        search_query = """
        SELECT 
            id, entity_type, entity_name, table_name, column_name, description,
            1 - (embedding <=> :embedding) as similarity
        FROM schema_metadata_vectors
        WHERE 1 - (embedding <=> :embedding) > :threshold
        ORDER BY embedding <=> :embedding
        LIMIT :top_k;
        """

        try:
            with self.engine.connect() as conn:
                embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
                result = conn.execute(
                    text(search_query),
                    {"embedding": embedding_str, "threshold": confidence_threshold, "top_k": top_k},
                )

                rows = result.fetchall()
        except Exception as e:
            logger.error(f"Error retrieving schema: {e}")
            return self._get_fallback_schema()

        if not rows:
            logger.warning(f"No results found for query with threshold {confidence_threshold}")
            return self._get_fallback_schema()

        # Process results
        retrieved_tables = set()
        retrieved_columns = {}
        relationships_found = []
        total_confidence = 0.0

        for row in rows:
            entity_type = row[1]
            entity_name = row[2]
            table_name = row[3]
            column_name = row[4]
            similarity = row[6]
            total_confidence += similarity

            if entity_type == "table":
                retrieved_tables.add(entity_name)
            elif entity_type == "column" and table_name:
                retrieved_columns.setdefault(table_name, []).append(column_name)
                retrieved_tables.add(table_name)
            elif entity_type == "relationship":
                relationships_found.append((entity_name, similarity))

        avg_confidence = total_confidence / len(rows) if rows else 0.0

        return {
            "tables": list(retrieved_tables),
            "columns": retrieved_columns,
            "relationships": relationships_found,
            "confidence": avg_confidence,
            "result_count": len(rows),
            "threshold_applied": confidence_threshold,
        }

    def _get_fallback_schema(self) -> dict:
        """Get all schema as fallback when vector search fails or returns low confidence.
        
        Returns:
            Complete schema dictionary
        """
        get_all_query = """
        SELECT DISTINCT entity_type, table_name FROM schema_metadata_vectors
        ORDER BY table_name;
        """

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(get_all_query))
                rows = result.fetchall()

                tables = set()
                for row in rows:
                    if row[1]:  # table_name is not null
                        tables.add(row[1])

                return {
                    "tables": list(tables),
                    "columns": {},
                    "relationships": [],
                    "confidence": 0.0,
                    "fallback": True,
                }
        except Exception as e:
            logger.error(f"Error getting fallback schema: {e}")
            return {
                "tables": [],
                "columns": {},
                "relationships": [],
                "confidence": 0.0,
                "fallback": True,
                "error": str(e),
            }

    def get_table_definition(self, table_name: str, schema: dict) -> dict:
        """Get complete table definition including all columns.
        
        Args:
            table_name: Name of the table
            schema: Full schema dictionary from metadata
            
        Returns:
            Table definition with all columns and metadata
        """
        if table_name not in schema:
            return {"table": table_name, "columns": {}, "error": "Table not found"}

        table_info = schema[table_name]
        return {
            "table": table_name,
            "columns": table_info.get("columns", {}),
            "primary_keys": table_info.get("primary_keys", []),
        }

    def expand_retrieved_schema(
        self, retrieved: dict, full_schema: dict
    ) -> dict:
        """Expand retrieved schema entries to full table definitions.
        
        Args:
            retrieved: Retrieved schema entries
            full_schema: Full schema dictionary
            
        Returns:
            Expanded schema with complete table definitions
        """
        expanded_schema = {}

        for table_name in retrieved.get("tables", []):
            if table_name in full_schema:
                expanded_schema[table_name] = full_schema[table_name]

        return expanded_schema

    def clear_all_vectors(self) -> None:
        """Clear all stored vector embeddings. Useful for re-indexing."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("DELETE FROM schema_metadata_vectors;"))
                conn.commit()
                logger.info("Cleared all schema metadata vectors")
        except Exception as e:
            logger.error(f"Error clearing vectors: {e}")
