from PyPDF2 import PdfMerger, PdfReader, errors
import os
import uuid

def handle_merge(files, password=None):
    """Merge a sequence of uploaded PDFs into a single PDF."""
    merger = PdfMerger()
    temp_paths = []

    # Ensure required directories exist
    UPLOAD_DIR = 'uploads'
    OUTPUT_DIR = 'output'
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        # Save uploaded files with unique names
        for f in files:
            ext = os.path.splitext(f.filename)[1]
            path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
            f.save(path)
            temp_paths.append(path)

        for path in temp_paths:
            reader = PdfReader(path)

            if reader.is_encrypted:
                # Try to decrypt using the provided password
                if not password or not reader.decrypt(password):
                    raise ValueError("error@@Password is incorrect. Please try again.")

            merger.append(reader, import_outline=False)

        # Save merged file
        output_file = os.path.join(OUTPUT_DIR, f"merged_{uuid.uuid4().hex}.pdf")
        with open(output_file, 'wb') as out:
            merger.write(out)

        return output_file

    finally:
        merger.close()
        for p in temp_paths:
            if os.path.exists(p):
                os.remove(p)
