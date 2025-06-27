import os
import uuid
import datetime
import docx
from docx2pdf import convert

try:
    import pythoncom  # For COM initialization on Windows
except Exception:  # ImportError or other issues
    pythoncom = None

def handle_word_to_pdf(input_path):
    """
    Convert a .docx file (by path) to PDF using docx2pdf.
    :param input_path: Path to uploaded DOCX file
    :return: path to generated PDF
    """

    # Directories setup
    OUTPUT_DIR = 'output'
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    LOG_PATH = os.path.abspath(os.path.join(OUTPUT_DIR, "word_to_pdf_error.log"))

    def log_event(msg):
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as logf:
                logf.write(f"[{datetime.datetime.now()}] {msg}\n")
        except Exception as e:
            print(f"[LOGGING ERROR] Could not write to log file: {LOG_PATH}\n{e}")

    original_name = os.path.basename(input_path)
    file_size = os.path.getsize(input_path)
    log_event(f"[INFO] Saved DOCX: {input_path}, size: {file_size} bytes")

    # Check for empty file
    if file_size == 0:
        log_event(f"[ERROR] Uploaded DOCX is empty: {input_path}")
        os.remove(input_path)
        raise ValueError("Uploaded Word file is empty.")

    # Check for text content in DOCX
    try:
        doc = docx.Document(input_path)
        has_text = any(p.text.strip() for p in doc.paragraphs)
        if not has_text:
            log_event(f"[ERROR] DOCX contains no extractable text: {input_path}")
            os.remove(input_path)
            raise ValueError("Uploaded Word file contains no text.")
    except Exception as e:
        log_event(f"[ERROR] Failed to read DOCX for text check: {input_path}: {e}")
        os.remove(input_path)
        raise ValueError("Failed to read Word file. Please upload a valid .docx file.")

    # Generate a unique output filename
    base_name = os.path.splitext(original_name)[0]
    output_pdf_name = f"{base_name}_{uuid.uuid4().hex}.pdf"
    output_pdf_path = os.path.join(OUTPUT_DIR, output_pdf_name)

    try:
        # Initialize COM before docx2pdf if available (Windows)
        if pythoncom and hasattr(pythoncom, "CoInitialize"):
            pythoncom.CoInitialize()
        log_event(f"[INFO] Starting docx2pdf conversion: {input_path} -> {OUTPUT_DIR}")
        convert(input_path, OUTPUT_DIR)

        # Expected output file (same name, .pdf)
        generated_pdf_path = os.path.join(OUTPUT_DIR, f"{base_name}.pdf")
        if not os.path.exists(generated_pdf_path):
            log_event(f"[ERROR] docx2pdf did not create expected output: {generated_pdf_path}")
            raise RuntimeError("docx2pdf failed to create output PDF.")

        # Rename to UUID-based filename
        os.replace(generated_pdf_path, output_pdf_path)
        log_event(f"[INFO] Output PDF created: {output_pdf_path}, size: {os.path.getsize(output_pdf_path)} bytes")

    except Exception as e:
        log_event(f"[ERROR] Exception during docx2pdf conversion: {str(e)}")
        raise
    finally:
        if pythoncom and hasattr(pythoncom, "CoUninitialize"):
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
        # Cleanup uploaded DOCX
        try:
            os.remove(input_path)
            log_event(f"[INFO] Cleaned up uploaded DOCX: {input_path}")
        except Exception as e:
            log_event(f"[ERROR] Failed to delete uploaded DOCX: {e}")

    return output_pdf_path
