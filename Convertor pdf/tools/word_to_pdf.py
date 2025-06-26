import os
import uuid
from docx2pdf import convert

def handle_word_to_pdf(file):
    """
    Convert an uploaded .docx file to PDF using docx2pdf.
    :param file: FileStorage object (uploaded DOCX)
    :return: path to generated PDF
    """
    # Directories setup
    UPLOAD_DIR = 'uploads'
    OUTPUT_DIR = 'output'
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save uploaded DOCX
    original_name = file.filename
    if not original_name.lower().endswith('.docx'):
        raise ValueError("Unsupported file type. Please upload a .docx file.")
    input_path = os.path.join(UPLOAD_DIR, original_name)
    file.save(input_path)

    # Generate a unique output filename
    base_name = os.path.splitext(original_name)[0]
    output_pdf_name = f"{base_name}_{uuid.uuid4().hex}.pdf"
    output_pdf_path = os.path.join(OUTPUT_DIR, output_pdf_name)

    # Use docx2pdf to convert
    # docx2pdf.convert(input_path, OUTPUT_DIR) will create a PDF with same base name in OUTPUT_DIR
    convert(input_path, OUTPUT_DIR)

    # docx2pdf names result as base_name.pdf
    generated_pdf_path = os.path.join(OUTPUT_DIR, f"{base_name}.pdf")
    # Rename to our uuid filename
    os.replace(generated_pdf_path, output_pdf_path)

    # Cleanup original upload
    os.remove(input_path)

    return output_pdf_path
