from PyPDF2 import PdfReader, PdfWriter, errors
import os
import uuid

def handle_split(file, start, end, password=None):
    filename = f"protected_{uuid.uuid4().hex}.pdf"
    input_path = os.path.join("temp", filename)
    file.save(input_path)

    try:
        reader = PdfReader(input_path)
        if reader.is_encrypted:
            if not reader.decrypt(password or ""):
                raise errors.FileNotDecryptedError("Incorrect password")

        writer = PdfWriter()
        for page_num in range(start - 1, end):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])
        
        output_path = os.path.join("temp", f"split_{uuid.uuid4().hex}.pdf")
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        return output_path

    except errors.FileNotDecryptedError:
        return None

    except Exception as e:
        return None
