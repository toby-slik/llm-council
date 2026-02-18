"""Document handling for text and PDF files."""

import pdfplumber
from io import BytesIO
from typing import Optional


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        file_content: Raw bytes of the PDF file
    
    Returns:
        Extracted text content
    """
    text_parts = []
    
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num}]\n{page_text}")
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")
    
    if not text_parts:
        raise ValueError("No text could be extracted from the PDF")
    
    return "\n\n".join(text_parts)


def extract_text_from_file(filename: str, content: bytes) -> str:
    """
    Extract text from a file based on its extension.
    
    Args:
        filename: Original filename (used to determine file type)
        content: Raw bytes of the file content
    
    Returns:
        Extracted text content
    """
    lower_name = filename.lower()
    
    if lower_name.endswith('.pdf'):
        return extract_text_from_pdf(content)
    elif lower_name.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(BytesIO(content))
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            raise ValueError(f"Failed to parse Word document: {str(e)}")
    elif lower_name.endswith(('.txt', '.md', '.csv', '.json', '.xml', '.html', '.py', '.js', '.ts', '.jsx', '.tsx', '.css', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.log')):
        # Text-based files - try to decode as UTF-8, fallback to latin-1
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return content.decode('latin-1')
            except UnicodeDecodeError:
                raise ValueError(f"Could not decode text file: {filename}")
    else:
        # Attempt to decode as text anyway
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError(f"Unsupported file type or binary file: {filename}")


def format_document_context(documents: list[dict]) -> str:
    """
    Format multiple documents into a context string for the LLM.
    
    Args:
        documents: List of dicts with 'filename' and 'content' keys
    
    Returns:
        Formatted context string
    """
    if not documents:
        return ""
    
    context_parts = ["The user has attached the following documents for reference:\n"]
    
    for i, doc in enumerate(documents, start=1):
        context_parts.append(f"--- Document {i}: {doc['filename']} ---")
        context_parts.append(doc['content'])
        context_parts.append("")  # Empty line between documents
    
    context_parts.append("--- End of Documents ---\n")
    
    return "\n".join(context_parts)
