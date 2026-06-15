"""Embedding manager using a local BGE-M3 model for embeddings."""

import os
from typing import Optional

import torch
from dotenv import load_dotenv
from transformers import AutoModel, AutoTokenizer

load_dotenv()


class EmbeddingManager:
    """Manages embedding generation using a local BGE-M3 model."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        embedding_dimension: Optional[int] = None,
    ):
        """Initialize the local embedding manager.

        Args:
            model_path: Local path to the embedding model directory.
            embedding_dimension: Target embedding dimension; inferred from model by default.
        """
        self.model_path = (
            model_path
            or os.getenv("LOCAL_EMBEDDING_MODEL_PATH")
            or "/Users/nilayupadhyay/Desktop/local-rag/models/embeddings/bge-m3"
        )
        self.embedding_dimension = embedding_dimension

        if not self.model_path or not os.path.isdir(self.model_path):
            raise ValueError(f"Embedding model path not found: {self.model_path}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, use_fast=True)
        self.model = AutoModel.from_pretrained(self.model_path).to(self.device)
        self.model.eval()

        if self.embedding_dimension is None:
            self.embedding_dimension = self.model.config.hidden_size

    def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for a given text using the local model.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text:
            return [0.0] * self.embedding_dimension

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=2048,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)

        if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
            embedding = outputs.pooler_output[0].cpu().numpy()
        elif hasattr(outputs, "last_hidden_state") and outputs.last_hidden_state is not None:
            embedding = outputs.last_hidden_state[:, 0, :][0].cpu().numpy()
        else:
            raise RuntimeError("Unable to extract embedding from model outputs.")

        embedding = embedding.tolist()

        if len(embedding) < self.embedding_dimension:
            embedding.extend([0.0] * (self.embedding_dimension - len(embedding)))
        elif len(embedding) > self.embedding_dimension:
            embedding = embedding[: self.embedding_dimension]

        return embedding

    def get_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self.get_embedding(text) for text in texts]

    def compute_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        import math

        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimension")

        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
