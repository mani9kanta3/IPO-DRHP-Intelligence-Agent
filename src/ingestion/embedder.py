import chromadb
from chromadb.utils import embedding_functions
import hashlib
from typing import List
from langchain_core.documents import Document
import os
from dotenv import load_dotenv

load_dotenv()


def get_pdf_hash(pdf_path: str) -> str:
    """Generate MD5 hash of PDF file for caching."""
    with open(pdf_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_chroma_client():
    return chromadb.PersistentClient(path="chroma_db")


def get_collection(collection_name: str = "drhp_chunks"):
    client = get_chroma_client()
    embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model_name="models/embedding-001"
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn
    )
    return collection


def embed_chunks(chunks: List[Document], pdf_path: str, collection_name: str = "drhp_chunks") -> bool:
    """Embed chunks into ChromaDB. Returns True if embedded, False if cache hit."""
    pdf_hash = get_pdf_hash(pdf_path)

    collection = get_collection(collection_name)

    # Check cache — if this PDF was already embedded, skip
    existing = collection.get(where={"pdf_hash": pdf_hash}, limit=1)
    if existing and existing["ids"]:
        print(f"Cache hit! PDF already embedded. Skipping.")
        return False

    print(f"Embedding {len(chunks)} chunks into ChromaDB...")

    # Embed in batches of 100
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.add(
            documents=[c.page_content for c in batch],
            metadatas=[{"chunk_id": c.metadata["chunk_id"], "pdf_hash": pdf_hash} for c in batch],
            ids=[f"{pdf_hash}_{c.metadata['chunk_id']}" for c in batch]
        )
        print(f"  Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks...")

    print("Embedding complete!")
    return True


def search(query: str, top_k: int = 10, collection_name: str = "drhp_chunks") -> List[dict]:
    """Search ChromaDB for most relevant chunks."""
    collection = get_collection(collection_name)
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"content": doc, "metadata": meta})
    return chunks


if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf
    from src.ingestion.chunker import chunk_text

    result = load_pdf("data/sample_drhps/swiggy_drhp.pdf")
    chunks = chunk_text(result["text"])

    embed_chunks(chunks, "data/sample_drhps/swiggy_drhp.pdf")

    print("\n--- Testing search ---")
    results = search("promoter shareholding and pledging")
    print(f"Found {len(results)} results")
    print(f"\nTop result preview:")
    print(results[0]["content"][:400])