# =============================================================================
# RAG Engine — Retrieval-Augmented Generation with FAISS
# Uses sentence-transformers for embeddings + FAISS for vector search
# =============================================================================
import os
import logging
import glob
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG dependencies not available. Falling back to keyword search.")


class FarmingRAGEngine:
    """
    Retrieval-Augmented Generation engine for agricultural knowledge.
    Loads .txt files from the knowledge base, chunks them, builds a FAISS
    index, and retrieves the top-k most relevant passages for any query.
    """

    CHUNK_SIZE = 500        # characters per chunk
    CHUNK_OVERLAP = 100     # character overlap between chunks
    TOP_K = 4               # number of passages to retrieve
    MODEL_NAME = "all-MiniLM-L6-v2"  # lightweight, fast embedding model

    def __init__(self, knowledge_base_path: str, vector_store_path: str):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.vector_store_path = Path(vector_store_path)
        self.chunks: list[str] = []
        self.chunk_sources: list[str] = []
        self.index = None
        self.model = None
        self._ready = False

        if RAG_AVAILABLE:
            self._initialize()
        else:
            self._load_raw_texts()

    # ── Initialization ─────────────────────────────────────────────────────
    def _initialize(self):
        """Load or build the FAISS index."""
        try:
            self.model = SentenceTransformer(self.MODEL_NAME)
            index_file = self.vector_store_path / "index.faiss"
            chunks_file = self.vector_store_path / "chunks.npy"
            sources_file = self.vector_store_path / "sources.npy"

            if index_file.exists() and chunks_file.exists():
                logger.info("Loading existing FAISS index...")
                self.index = faiss.read_index(str(index_file))
                self.chunks = list(np.load(str(chunks_file), allow_pickle=True))
                self.chunk_sources = list(np.load(str(sources_file), allow_pickle=True))
                self._ready = True
                logger.info(f"FAISS index loaded: {len(self.chunks)} chunks.")
            else:
                logger.info("Building new FAISS index from knowledge base...")
                self._build_index()
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            self._load_raw_texts()

    def _load_raw_texts(self):
        """Fallback: load raw texts for simple keyword search."""
        self.raw_texts = {}
        pattern = str(self.knowledge_base_path / "*.txt")
        for filepath in glob.glob(pattern):
            name = Path(filepath).stem
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.raw_texts[name] = f.read()
            except Exception as e:
                logger.warning(f"Could not load {filepath}: {e}")
        logger.info(f"Loaded {len(self.raw_texts)} raw text files (fallback mode).")

    def _chunk_text(self, text: str, source: str) -> list[tuple[str, str]]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk = text[start:end].strip()
            if len(chunk) > 50:  # ignore tiny fragments
                chunks.append((chunk, source))
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP
        return chunks

    def _build_index(self):
        """Build FAISS index from knowledge base files."""
        import numpy as np

        all_chunks = []
        pattern = str(self.knowledge_base_path / "*.txt")
        files = glob.glob(pattern)

        if not files:
            logger.warning("No knowledge base files found!")
            return

        for filepath in files:
            source = Path(filepath).stem
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
                all_chunks.extend(self._chunk_text(text, source))
            except Exception as e:
                logger.warning(f"Could not process {filepath}: {e}")

        if not all_chunks:
            logger.warning("No chunks generated from knowledge base.")
            return

        self.chunks = [c[0] for c in all_chunks]
        self.chunk_sources = [c[1] for c in all_chunks]

        logger.info(f"Encoding {len(self.chunks)} chunks...")
        embeddings = self.model.encode(self.chunks, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype=np.float32)

        # L2 normalize for cosine similarity
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product = cosine sim after normalize
        self.index.add(embeddings)

        # Save index and chunks
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.vector_store_path / "index.faiss"))
        np.save(str(self.vector_store_path / "chunks.npy"), np.array(self.chunks, dtype=object))
        np.save(str(self.vector_store_path / "sources.npy"), np.array(self.chunk_sources, dtype=object))

        self._ready = True
        logger.info(f"FAISS index built and saved: {len(self.chunks)} chunks.")

    # ── Retrieval ──────────────────────────────────────────────────────────
    def retrieve(self, query: str, top_k: int = None) -> str:
        """
        Retrieve the top-k most relevant passages for the given query.
        Returns a formatted string of passages for injection into the LLM prompt.
        """
        k = top_k or self.TOP_K

        if RAG_AVAILABLE and self._ready and self.index is not None:
            return self._faiss_retrieve(query, k)
        else:
            return self._keyword_retrieve(query)

    def _faiss_retrieve(self, query: str, k: int) -> str:
        """FAISS-based semantic retrieval."""
        import numpy as np
        try:
            query_embedding = self.model.encode([query])
            query_embedding = np.array(query_embedding, dtype=np.float32)
            faiss.normalize_L2(query_embedding)

            scores, indices = self.index.search(query_embedding, k)

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and score > 0.2:  # minimum relevance threshold
                    source = self.chunk_sources[idx].replace("_", " ").title()
                    results.append(f"[Source: {source}]\n{self.chunks[idx]}")

            if results:
                return "\n\n---\n\n".join(results)
            return "No highly relevant agricultural knowledge found for this query."
        except Exception as e:
            logger.error(f"FAISS retrieval error: {e}")
            return "Knowledge retrieval temporarily unavailable."

    def _keyword_retrieve(self, query: str) -> str:
        """Simple keyword-based fallback retrieval."""
        if not hasattr(self, 'raw_texts') or not self.raw_texts:
            return "Knowledge base not available."

        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for name, text in self.raw_texts.items():
            text_lower = text.lower()
            score = sum(1 for word in query_words if word in text_lower)
            if score > 0:
                scored.append((score, name, text))

        scored.sort(reverse=True, key=lambda x: x[0])

        results = []
        for _, name, text in scored[:2]:
            # Extract relevant sections (500 char windows around keyword matches)
            for word in query_words:
                pos = text.lower().find(word)
                if pos >= 0:
                    start = max(0, pos - 100)
                    end = min(len(text), pos + 400)
                    snippet = text[start:end].strip()
                    source = name.replace("_", " ").title()
                    results.append(f"[Source: {source}]\n{snippet}")
                    break

        return "\n\n---\n\n".join(results) if results else "No relevant information found."

    def rebuild_index(self) -> bool:
        """Force rebuild the FAISS index (call after adding new knowledge files)."""
        try:
            # Remove existing index
            index_file = self.vector_store_path / "index.faiss"
            if index_file.exists():
                index_file.unlink()
            self._initialize()
            return True
        except Exception as e:
            logger.error(f"Index rebuild failed: {e}")
            return False

    @property
    def is_ready(self) -> bool:
        return self._ready or hasattr(self, 'raw_texts')

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
