import json
from src.agents.state import ResearchState
from src.agents.llm import get_llm
from src.ingestion.embedder import search


def section_identifier_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 1] Section Identifier running...")
    
    llm = get_llm(complex_task=False)
    
    sections = {
        "business_overview": [],
        "risk_factors": [],
        "financials": [],
        "promoter": [],
        "litigation": [],
        "objects_of_issue": [],
        "other": []
    }

    # Get all chunks from ChromaDB using broad queries
    queries = [
        "business overview company description operations",
        "risk factors warnings threats",
        "financial statements revenue profit loss balance sheet",
        "promoter management key people founders",
        "litigation legal proceedings court cases",
        "objects of issue use of funds proceeds"
    ]

    seen_chunk_ids = set()
    all_chunks = []

    for query in queries:
        results = search(query, top_k=50)
        for chunk in results:
            cid = chunk["metadata"]["chunk_id"]
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                all_chunks.append(chunk)

    print(f"  Total unique chunks to classify: {len(all_chunks)}")

    # Classify in batches of 10
    batch_size = 10
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        
        batch_text = ""
        for j, chunk in enumerate(batch):
            batch_text += f"\n---CHUNK {j}---\n{chunk['content'][:300]}\n"

        prompt = f"""You are classifying sections of an Indian IPO DRHP document.

Classify each chunk into exactly one of these sections:
- business_overview
- risk_factors
- financials
- promoter
- litigation
- objects_of_issue
- other

{batch_text}

Return ONLY a JSON array with the section for each chunk in order.
Example: ["business_overview", "risk_factors", "financials"]
No explanation, just the JSON array."""

        try:
            response = llm.invoke(prompt)
            content = response.content.strip()
            # Clean markdown if present
            content = content.replace("```json", "").replace("```", "").strip()
            labels = json.loads(content)

            for j, label in enumerate(labels):
                if label in sections and j < len(batch):
                    sections[label].append(batch[j]["content"])
        except Exception as e:
            print(f"  Warning: batch {i} classification failed: {e}")
            for chunk in batch:
                sections["other"].append(chunk["content"])

        if (i + batch_size) % 50 == 0:
            print(f"  Classified {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks...")

    # Print summary
    for section, chunks in sections.items():
        print(f"  {section}: {len(chunks)} chunks")

    state["sections"] = sections
    state["status"] = "sections_identified"
    return state


if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf
    from src.ingestion.chunker import chunk_text
    from src.ingestion.embedder import embed_chunks

    result = load_pdf("data/sample_drhps/swiggy_drhp.pdf")

    state = ResearchState(
        drhp_text=result["text"],
        pdf_path="data/sample_drhps/swiggy_drhp.pdf",
        file_name=result["file_name"],
        total_pages=result["total_pages"],
        sections={},
        red_flags=[],
        risk_score=0,
        financials={},
        promoter_report=[],
        valuation={},
        final_report="",
        verdict="",
        revision_count=0,
        status="started",
        errors=[]
    )

    state = section_identifier_agent(state)
    print("\nSection identification complete!")