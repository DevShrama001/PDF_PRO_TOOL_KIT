import os
import uuid
import zipfile
import tempfile
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader


def handle_pdf_to_jpg(file, password=""):
    try:
        file_bytes = file.read()

        # Check if PDF is encrypted
        reader = PdfReader(file)
        if reader.is_encrypted:
            if not password:
                raise Exception("error||This file is password-protected. Please provide a password.")
            try:
                reader.decrypt(password)
            except:
                raise Exception("error||Incorrect password provided.")

        # Convert to images
        images = convert_from_bytes(file_bytes, dpi=200, fmt="jpeg", userpw=password if password else None)

        # Save all images
        output_folder = tempfile.mkdtemp()
        image_paths = []

        for i, img in enumerate(images, start=1):
            filename = f"page_{i}.jpg"
            full_path = os.path.join(output_folder, filename)
            img.save(full_path, "JPEG")
            image_paths.append(full_path)

        # Zip all images
        zip_filename = f"pdf_to_jpg_{uuid.uuid4().hex}.zip"
        zip_path = os.path.join("output", zip_filename)
        os.makedirs("output", exist_ok=True)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for img_path in image_paths:
                zipf.write(img_path, os.path.basename(img_path))

        return zip_path

    except Exception as e:
        raise Exception(f"error||PDF to JPG conversion failed: {str(e)}")
