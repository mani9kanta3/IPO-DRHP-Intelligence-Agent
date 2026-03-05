import chromadb
import hashlib
from typing import List
from langchain_core.documents import Document
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client_genai = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def get_pdf_hash(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_embeddings(texts: List[str]) -> List[List[float]]:
    result = client_genai.models.embed_content(
        model="models/gemini-embedding-001",
        contents=texts
    )
    return [e.values for e in result.embeddings]


def get_chroma_client():
    return chromadb.PersistentClient(path="chroma_db")


def get_collection(collection_name: str = "drhp_chunks"):
    client = get_chroma_client()
    collection = client.get_or_create_collection(name=collection_name)
    return collection


def embed_chunks(chunks: List[Document], pdf_path: str, collection_name: str = "drhp_chunks") -> bool:
    pdf_hash = get_pdf_hash(pdf_path)
    collection = get_collection(collection_name)

    # Check cache
    existing = collection.get(where={"pdf_hash": pdf_hash}, limit=1)
    if existing and existing["ids"]:
        print("Cache hit! PDF already embedded. Skipping.")
        return False

    print(f"Embedding {len(chunks)} chunks into ChromaDB...")

    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c.page_content for c in batch]
        embeddings = get_embeddings(texts)

        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=[{"chunk_id": c.metadata["chunk_id"], "pdf_hash": pdf_hash} for c in batch],
            ids=[f"{pdf_hash}_{c.metadata['chunk_id']}" for c in batch]
        )
        print(f"  Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks...")

    print("Embedding complete!")
    return True


def search(query: str, top_k: int = 10, collection_name: str = "drhp_chunks", pdf_hash: str = None) -> List[dict]:
    collection = get_collection(collection_name)
    query_embedding = get_embeddings([query])[0]

    where_filter = {"pdf_hash": pdf_hash} if pdf_hash else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
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