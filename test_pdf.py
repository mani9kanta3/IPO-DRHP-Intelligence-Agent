import pdfplumber

with pdfplumber.open("data/sample_drhps/swiggy_drhp.pdf") as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print(f"\nFirst 500 chars of page 1:")
    print(pdf.pages[0].extract_text()[:500])