import os
import uuid
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from docx import Document

def handle_compress(file, password=""):
    ext = os.path.splitext(file.filename)[-1].lower()
    input_path = f'uploads/{uuid.uuid4().hex}{ext}'
    output_path = f'output/compressed_{uuid.uuid4().hex}{ext}'
    file.save(input_path)

    if ext == ".pdf":
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                if not password:
                    raise Exception("This PDF is protected. Please provide a password.")
                try:
                    reader.decrypt(password)
                except:
                    raise Exception("Incorrect PDF password.")
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
        except Exception as e:
            raise e

    elif ext in [".jpg", ".jpeg", ".png"]:
        img = Image.open(input_path)
        img.save(output_path, optimize=True, quality=40)

    elif ext in [".docx", ".doc"]:
        doc = Document(input_path)
        doc.save(output_path)  # No real compression but saving as new

    else:
        raise Exception("Unsupported file format")

    return output_path
