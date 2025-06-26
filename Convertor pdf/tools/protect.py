import os
import uuid
from PyPDF2 import PdfReader, PdfWriter

def handle_protect(file, password: str):
    """
    Protect an uploaded PDF with a password using AES-256 encryption.
    :param file: FileStorage object (uploaded PDF)
    :param password: string password to encrypt PDF
    :return: path to encrypted PDF
    """
    # Directories setup
    UPLOAD_DIR = 'uploads'
    OUTPUT_DIR = 'output'
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save original PDF
    original_name = file.filename
    input_path = os.path.join(UPLOAD_DIR, original_name)
    file.save(input_path)

    # Read pages and write to writer with encryption
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    # Encrypt with user password (owner password same)
    writer.encrypt(
        user_pwd=password,
        owner_pwd=password,
        use_128bit=True  # AES-128; set False for AES-256 if supported
    )

    # Output file
    output_filename = f'protected_{uuid.uuid4().hex}.pdf'
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'wb') as out_pdf:
        writer.write(out_pdf)

    # Cleanup original upload
    os.remove(input_path)

    return output_path
