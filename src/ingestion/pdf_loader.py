import pdfplumber
import PyPDF2
import re
from pathlib import Path


def clean_text(text: str) -> str:
    # Fix broken words from line breaks
    text = re.sub(r'-\n', '', text)
    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove page numbers standalone on a line
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Fix multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def extract_tables_from_page(page) -> str:
    tables = page.extract_tables()
    if not tables:
        return ""
    
    table_text = ""
    for table in tables:
        for row in table:
            # Filter None values
            row_clean = [cell if cell else "" for cell in row]
            table_text += " | ".join(row_clean) + "\n"
        table_text += "\n"
    return table_text


def load_pdf(pdf_path: str) -> dict:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    print(f"Loading PDF: {path.name}")
    
    full_text = ""
    tables_data = []
    total_pages = 0

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")

        for i, page in enumerate(pdf.pages):
            # Extract text
            page_text = page.extract_text() or ""
            page_text = clean_text(page_text)

            # Extract tables separately
            table_text = extract_tables_from_page(page)
            if table_text:
                tables_data.append({
                    "page": i + 1,
                    "content": table_text
                })

            full_text += f"\n[PAGE {i+1}]\n{page_text}\n"

            if (i + 1) % 50 == 0:
                print(f"  Processed {i+1}/{total_pages} pages...")

    print(f"Extraction complete. Total characters: {len(full_text)}")
    print(f"Tables found: {len(tables_data)}")

    return {
        "text": full_text,
        "tables": tables_data,
        "total_pages": total_pages,
        "file_name": path.name
    }


if __name__ == "__main__":
    result = load_pdf("data/sample_drhps/swiggy_drhp.pdf")
    print("\n--- Sample from page 1 ---")
    # Print first 1000 chars
    print(result["text"][:1000])
    print("\n--- Sample table ---")
    if result["tables"]:
        print(result["tables"][0])