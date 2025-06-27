import os
import uuid
import zipfile
import tempfile
import fitz  # PyMuPDF

try:
    log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write("[DEBUG] Manual log test\n")
        logf.flush()
    print("[DEBUG] Manual log write succeeded")
except Exception as e:
    print("[DEBUG] Manual log write failed:", e)

def handle_pdf_to_jpg(pdf_bytes, password=""):
    print("[DEBUG] handle_pdf_to_jpg CALLED")
    doc = None
    output_dir = None
    image_paths = []
    try:
        print("[DEBUG] Attempting to open PDF with PyMuPDF...")
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            os.makedirs("output", exist_ok=True)
            log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
            try:
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"\n[ERROR] Failed to open PDF: {str(e)}\nTraceback:\n{tb}\n{'-'*60}\n")
                    logf.flush()
                print(f"[ERROR] Failed to open PDF: {e}\nTraceback written to: {log_path}")
            except Exception as log_e:
                print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")
            raise Exception(f"error||Failed to open PDF: {str(e)}\nLog saved to {log_path}")

        # Log encryption info before authentication
        enc_info = f"is_encrypted={getattr(doc, 'is_encrypted', 'N/A')}, needs_pass={getattr(doc, 'needs_pass', 'N/A')}, permissions={getattr(doc, 'permissions', 'N/A')}"
        log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
        print(f"[DEBUG] PDF encryption info BEFORE auth: {enc_info}")
        try:
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"[INFO] PDF encryption info BEFORE auth: {enc_info}\n")
                logf.flush()
            print(f"[DEBUG] Wrote encryption info to: {log_path}")
        except Exception as log_e:
            print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")

        if doc.needs_pass:
            print("[DEBUG] PDF is encrypted.")
            if not password:
                raise Exception("error||This PDF is password protected. Please provide a password.")
            auth_result = doc.authenticate(password)
            # Log authentication attempt
            try:
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"[INFO] Attempted authentication with password: '{password}'. Result: {auth_result}\n")
                    logf.flush()
                print(f"[DEBUG] Wrote authentication attempt to: {log_path}")
            except Exception as log_e:
                print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")
            if not auth_result:
                os.makedirs("output", exist_ok=True)
                fail_path = os.path.join("output", "failed_input.pdf")
                with open(fail_path, "wb") as f:
                    f.write(pdf_bytes)
                # Log encryption info after failed auth
                enc_info_after = f"is_encrypted={getattr(doc, 'is_encrypted', 'N/A')}, needs_pass={getattr(doc, 'needs_pass', 'N/A')}, permissions={getattr(doc, 'permissions', 'N/A')}"
                try:
                    with open(log_path, "a", encoding="utf-8") as logf:
                        logf.write(f"[INFO] PDF encryption info AFTER failed auth: {enc_info_after}\n")
                        logf.flush()
                    print(f"[DEBUG] Wrote failed auth info to: {log_path}")
                except Exception as log_e:
                    print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")
                raise Exception(f"error||Incorrect password provided. PDF saved to {fail_path} for inspection.")
            print("[DEBUG] Password authentication successful.")
            # Log encryption info after successful auth
            enc_info_after = f"is_encrypted={getattr(doc, 'is_encrypted', 'N/A')}, needs_pass={getattr(doc, 'needs_pass', 'N/A')}, permissions={getattr(doc, 'permissions', 'N/A')}"
            try:
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"[INFO] PDF encryption info AFTER successful auth: {enc_info_after}\n")
                    logf.flush()
                print(f"[DEBUG] Wrote successful auth info to: {log_path}")
            except Exception as log_e:
                print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")

        print(f"[DEBUG] Total pages: {doc.page_count}")
        if doc.page_count == 0:
            raise Exception("error||The PDF has no pages to convert.")

        output_dir = tempfile.mkdtemp()
        for i in range(doc.page_count):
            try:
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=200)
                img_path = os.path.join(output_dir, f"page_{i+1}.jpg")
                pix.save(img_path)
                image_paths.append(img_path)
                print(f"[DEBUG] Page {i+1} converted to image.")
            except Exception as page_e:
                import traceback
                tb_page = traceback.format_exc()
                try:
                    with open(log_path, "a", encoding="utf-8") as logf:
                        logf.write(f"[ERROR] Failed to convert page {i+1}: {str(page_e)}\nTraceback:\n{tb_page}\n")
                        logf.flush()
                    print(f"[DEBUG] Wrote page error to: {log_path}")
                except Exception as log_e:
                    print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")
                raise Exception(f"error||Failed to convert page {i+1}: {str(page_e)}\nLog saved to {log_path}")

        if not image_paths:
            raise Exception("error||No images generated from PDF.")

        zip_filename = f"pdf_to_jpg_{uuid.uuid4().hex}.zip"
        os.makedirs("output", exist_ok=True)
        zip_path = os.path.join("output", zip_filename)

        with zipfile.ZipFile(zip_path, "w") as zipf:
            for img_path in image_paths:
                zipf.write(img_path, os.path.basename(img_path))
                print(f"[DEBUG] Added {img_path} to zip.")

        print(f"[DEBUG] PDF to JPG conversion successful. Output: {zip_path}")
        return zip_path

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
        try:
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"\n[ERROR] {str(e)}\nTraceback:\n{tb}\n{'-'*60}\n")
                logf.flush()
            print(f"[ERROR] {e}\nTraceback written to: {log_path}")
        except Exception as log_e:
            print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")
        raise Exception(f"error||{str(e)}\nLog saved to {log_path}")

    finally:
        # Cleanup temporary files and close document
        try:
            if doc:
                doc.close()
        except Exception:
            pass
        for img_path in image_paths:
            try:
                os.remove(img_path)
            except Exception:
                pass
        if output_dir:
            try:
                os.rmdir(output_dir)
            except Exception:
                pass
