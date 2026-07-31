import fitz  # PyMuPDF
from typing import List, Dict

def parse_pdf(file_path: str) -> List[Dict[str, str]]:
    """
    Extracts text from a PDF file.
    Returns a list of dictionaries containing page text and metadata.
    """
    pages_content = []
    
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                pages_content.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "source": str(file_path)
                })
        doc.close()
    except Exception as e:
        print(f"Error parsing PDF {file_path}: {e}")
        
    return pages_content
