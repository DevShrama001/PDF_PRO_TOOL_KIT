from PyPDF2 import PdfMerger, PdfReader, errors
import os
import uuid

def handle_merge(files, password=None):
    merger = PdfMerger()
    temp_paths = []

    try:
        # Save uploaded files
        for f in files:
            path = os.path.join('uploads', f.filename)
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
        output_file = os.path.join('output', f'merged_{uuid.uuid4().hex}.pdf')
        with open(output_file, 'wb') as out:
            merger.write(out)

        return output_file

    finally:
        merger.close()
        for p in temp_paths:
            if os.path.exists(p):
                os.remove(p)