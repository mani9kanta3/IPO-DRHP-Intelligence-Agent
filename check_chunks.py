from src.ingestion.embedder import get_chroma_client, get_pdf_hash

client = get_chroma_client()
col = client.get_collection('drhp_chunks')
h = get_pdf_hash('data/sample_drhps/swiggy_drhp.pdf')

results = col.get(
    where={"pdf_hash": h},
    limit=3
)

# Print actual IDs
for doc_id, meta in zip(results['ids'], results['metadatas']):
    print(f"ID: {doc_id}, chunk_id: {meta['chunk_id']}")