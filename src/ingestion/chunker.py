from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document


def chunk_text(text: str, chunk_size: int = 2000, chunk_overlap: int = 200) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = splitter.create_documents([text])

    # Add chunk_id metadata to each chunk
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    return chunks


if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf

    result = load_pdf("data/sample_drhps/swiggy_drhp.pdf")
    chunks = chunk_text(result["text"])

    print(f"Total chunks: {len(chunks)}")
    print(f"\nFirst chunk preview:")
    print(chunks[0].page_content[:300])
    print(f"\nLast chunk preview:")
    print(chunks[-1].page_content[:300])