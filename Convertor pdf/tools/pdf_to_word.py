import os
import uuid
import pdfplumber
from docx import Document

def handle_pdf_to_word(file):
    """
    Convert an uploaded PDF file to a Word (.docx) document by extracting text.
    :param file: FileStorage object (uploaded PDF)
    :return: path to generated .docx file
    """
    # Directories
    UPLOAD_DIR = 'uploads'
    OUTPUT_DIR = 'output'
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save PDF to disk
    original_name = file.filename
    if not original_name.lower().endswith('.pdf'):
        raise ValueError("Unsupported file type. Please upload a PDF file.")
    input_path = os.path.join(UPLOAD_DIR, original_name)
    file.save(input_path)

    # Create a Word document
    doc = Document()

    # Open PDF and extract text
    with pdfplumber.open(input_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    doc.add_paragraph(line)
                # Add a page break in Word after each PDF page
                doc.add_page_break()

    # Save .docx
    base_name = os.path.splitext(original_name)[0]
    output_filename = f"{base_name}_{uuid.uuid4().hex}.docx"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    doc.save(output_path)

    # Cleanup upload
    os.remove(input_path)

    return output_path
