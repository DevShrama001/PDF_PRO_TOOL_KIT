import os
import uuid
from docx2pdf import convert
import datetime

def handle_word_to_pdf(file):
    """
    Convert an uploaded .docx file to PDF using docx2pdf.
    :param file: FileStorage object (uploaded DOCX)
    :return: path to generated PDF
    """
    # Directories setup
    UPLOAD_DIR = 'uploads'
    OUTPUT_DIR = 'output'
    LOG_PATH = os.path.abspath(os.path.join(OUTPUT_DIR, "word_to_pdf_error.log"))
    def log_event(msg):
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as logf:
                logf.write(f"[{datetime.datetime.now()}] {msg}\n")
                logf.flush()
        except Exception as e:
            print(f"[LOGGING ERROR] Could not write to log file: {LOG_PATH}\n{e}")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save uploaded DOCX
    original_name = file.filename
    if not original_name.lower().endswith('.docx'):
        log_event(f"[ERROR] Unsupported file type: {original_name}")
        raise ValueError("Unsupported file type. Please upload a .docx file.")
    input_path = os.path.join(UPLOAD_DIR, original_name)
    file.save(input_path)
    log_event(f"[INFO] Saved DOCX: {input_path}, size: {os.path.getsize(input_path)} bytes")

    # Generate a unique output filename
    base_name = os.path.splitext(original_name)[0]
    output_pdf_name = f"{base_name}_{uuid.uuid4().hex}.pdf"
    output_pdf_path = os.path.join(OUTPUT_DIR, output_pdf_name)

    try:
        # Use docx2pdf to convert
        log_event(f"[INFO] Starting docx2pdf conversion: {input_path} -> {OUTPUT_DIR}")
        convert(input_path, OUTPUT_DIR)
        generated_pdf_path = os.path.join(OUTPUT_DIR, f"{base_name}.pdf")
        if not os.path.exists(generated_pdf_path):
            log_event(f"[ERROR] docx2pdf did not create expected output: {generated_pdf_path}")
            raise RuntimeError("docx2pdf failed to create output PDF.")
        # Rename to our uuid filename
        os.replace(generated_pdf_path, output_pdf_path)
        log_event(f"[INFO] Output PDF created: {output_pdf_path}, size: {os.path.getsize(output_pdf_path)} bytes")
    except Exception as e:
        log_event(f"[ERROR] Exception during docx2pdf conversion: {str(e)}")
        raise
    finally:
        # Cleanup original upload
        try:
            os.remove(input_path)
            log_event(f"[INFO] Cleaned up uploaded DOCX: {input_path}")
        except Exception as e:
            log_event(f"[ERROR] Failed to cleanup uploaded DOCX: {input_path}: {e}")

    return output_pdf_path
