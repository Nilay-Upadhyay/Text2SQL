"""Migration script to set up PGVector schema indexing."""

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.metadata.embedding_manager import EmbeddingManager
from src.metadata.vector_retriever import VectorRetriever

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_schema_and_relationships() -> tuple[dict, list[dict]]:
    """Load schema and relationships from generated metadata files.
    
    Returns:
        Tuple of (schema dict, relationships list)
    """
    metadata_dir = Path("src/metadata/generated")

    schema_path = metadata_dir / "schema.json"
    relationships_path = metadata_dir / "relationships.json"

    if not schema_path.exists() or not relationships_path.exists():
        raise FileNotFoundError(f"Metadata files not found in {metadata_dir}")

    with open(schema_path) as f:
        schema = json.load(f)

    with open(relationships_path) as f:
        relationships = json.load(f)

    return schema, relationships


def load_business_dictionary() -> dict:
    """Load business dictionary if available.
    
    Returns:
        Business dictionary or empty dict if not found
    """
    dict_path = Path("src/metadata/generated/business_dictionary.json")

    if dict_path.exists():
        with open(dict_path) as f:
            return json.load(f)

    return {}


def main(clear_existing: bool = False) -> None:
    """Set up PGVector indexing for schema metadata.
    
    Args:
        clear_existing: Whether to clear and re-index existing vectors
    """
    try:
        logger.info("Initializing PGVector schema indexing...")

        # Load metadata
        logger.info("Loading schema and relationships...")
        schema, relationships = load_schema_and_relationships()
        business_dict = load_business_dictionary()

        logger.info(f"Found {len(schema)} tables and {len(relationships)} relationships")

        # Initialize embedding manager
        logger.info("Initializing embedding manager...")
        embedding_manager = EmbeddingManager()

        # Initialize vector retriever
        logger.info("Initializing vector retriever...")
        retriever = VectorRetriever(embedding_manager=embedding_manager)

        # Clear existing vectors if requested
        if clear_existing:
            logger.info("Clearing existing vectors...")
            retriever.clear_all_vectors()

        # Index schema metadata
        logger.info("Indexing schema metadata into PGVector...")
        retriever.index_schema_metadata(
            schema=schema, relationships=relationships, business_dict=business_dict
        )

        logger.info("✓ PGVector schema indexing completed successfully!")
        logger.info(f"  - Tables indexed: {len(schema)}")
        logger.info(f"  - Relationships indexed: {len(relationships)}")
        logger.info(
            f"  - Total metadata entries: {len(schema) + len(schema) * 5 + len(relationships)}"
        )  # Approximate

        return True

    except Exception as e:
        logger.error(f"Error during PGVector setup: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Set up PGVector schema indexing")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing vectors before re-indexing",
    )

    args = parser.parse_args()

    success = main(clear_existing=args.clear)
    sys.exit(0 if success else 1)
