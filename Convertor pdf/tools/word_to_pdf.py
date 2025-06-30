import os
try:
    from docx import Document
    import docx2pdf
except ImportError:
    Document = None
    docx2pdf = None
import uuid

def handle_word_to_pdf(docx_path):
    """
    Converts a DOCX file to PDF and returns the output PDF path using docx2pdf.
    Always saves the PDF in the output directory.
    Raises an error if conversion fails or output PDF is empty.
    """
    if docx2pdf is None:
        raise RuntimeError("docx2pdf is not installed. Please install it to use this feature.")
    out_dir = os.path.abspath("output")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(docx_path))[0]
    out_file = os.path.join(out_dir, f"{base}.pdf")
    try:
        docx2pdf.convert(docx_path, out_dir)
        os.remove(docx_path)
        if not os.path.exists(out_file) or os.path.getsize(out_file) == 0:
            raise RuntimeError("PDF conversion failed. Please ensure Microsoft Word is installed and the DOCX file is valid.")
        return out_file
    except Exception as e:
        raise RuntimeError(f"Word to PDF conversion failed: {str(e)}")

