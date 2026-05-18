"""Skein — a knowledge graph woven from embeddings, no autoregressive LLM per chunk."""
from skein.core import build_skein, neighbors_of
from skein.schema import schema_apply

__all__ = ["build_skein", "neighbors_of", "schema_apply"]
__version__ = "0.1.0"
