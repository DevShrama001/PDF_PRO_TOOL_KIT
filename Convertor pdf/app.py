import io
import os
import uuid
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, session, after_this_request
from PyPDF2 import PdfMerger, PdfReader
from tools import compress, merger, split, pdf_to_jpg, watermark
from tools.jpg_to_pdf import handle_jpg_to_pdf
from tools.pdf_to_jpg import handle_pdf_to_jpg
from tools.protect import handle_protect
from tools.word_to_pdf import handle_word_to_pdf
from tools.pdf_to_word import handle_pdf_to_word
import zipfile
import tempfile
import fitz  # PyMuPDF
import threading
import time

# Create necessary folders
os.makedirs('uploads', exist_ok=True)
os.makedirs('output', exist_ok=True)
os.makedirs('temp', exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your-strong-secret-key'

@app.route('/')
def home_page():
    return render_template('index.html')

@app.route('/merge', methods=['GET', 'POST'])
def merge_route():
    if request.method == 'POST':
        files = request.files.getlist('pdfs')
        password = request.form.get('password', '')
        merger_instance = PdfMerger()
        input_paths = []
        for file in files:
            path = os.path.join('uploads', file.filename)
            file.save(path)
            input_paths.append(path)
            try:
                reader = PdfReader(path)
                if reader.is_encrypted:
                    if password:
                        try:
                            reader.decrypt(password)
                            merger_instance.append(reader)
                        except Exception:
                            flash(f"error||Incorrect password for '{file.filename}'.")
                            for p in input_paths:
                                if os.path.exists(p):
                                    os.remove(p)
                            return redirect(url_for('merge_route'))
                    else:
                        flash(f"error||The file '{file.filename}' is password protected. Please provide a password.")
                        for p in input_paths:
                            if os.path.exists(p):
                                os.remove(p)
                        return redirect(url_for('merge_route'))
                else:
                    merger_instance.append(reader)
            except Exception as e:
                flash(f"error||Failed to read '{file.filename}': {str(e)}")
                for p in input_paths:
                    if os.path.exists(p):
                        os.remove(p)
                return redirect(url_for('merge_route'))
        output_path = os.path.join('output', f'merged_{uuid.uuid4().hex}.pdf')
        try:
            with open(output_path, 'wb') as f:
                merger_instance.write(f)
            merger_instance.close()
        except Exception as e:
            flash(f"error||Failed to create output file: {str(e)}")
            for p in input_paths:
                if os.path.exists(p):
                    os.remove(p)
            return redirect(url_for('merge_route'))
        flash("success||PDFs merged successfully and downloading.")
        @after_this_request
        def remove_files(response):
            try:
                for p in input_paths:
                    if os.path.exists(p):
                        os.remove(p)
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return send_file(output_path, as_attachment=True)
    return render_template('merge.html')

@app.route("/split", methods=["GET", "POST"])
def split_route():
    if request.method == "POST":
        file = request.files["pdf"]
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        start = int(request.form["start"])
        end = int(request.form["end"])
        password = request.form.get("password", "")
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        if os.path.exists(input_path):
                            os.remove(input_path)
                        return redirect(request.url)
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    return redirect(request.url)
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(request.url)
        path = split.handle_split(file, start, end, password)
        if path is None:
            if os.path.exists(input_path):
                os.remove(input_path)
            flash("error||Failed to create output file.")
            return redirect(request.url)
        @after_this_request
        def remove_files(response):
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return send_file(path, as_attachment=True)
    return render_template("split.html")

@app.route('/pdf-to-jpg', methods=['GET', 'POST'])
def pdf_to_jpg_route():
    if request.method == 'POST':
        try:
            file = request.files.get('pdf')
            if not file:
                log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"[ERROR] Route: No file selected.\n")
                    logf.flush()
                flash("error||No file selected.")
                return redirect(url_for('pdf_to_jpg_route'))

            password = request.form.get('password', '')
            file_bytes = file.read()
            print(f"[DEBUG] Route: Received file '{file.filename}' with {len(file_bytes)} bytes")

            # Use fitz for protection check
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if doc.needs_pass:
                    print("[DEBUG] Route: PDF is encrypted")
                    if not password:
                        log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
                        with open(log_path, "a", encoding="utf-8") as logf:
                            logf.write(f"[ERROR] Route: PDF is encrypted but no password provided.\n")
                            logf.flush()
                        flash("error||This PDF is password protected. Please provide a password.")
                        return redirect(url_for('pdf_to_jpg_route'))
                    if not doc.authenticate(password):
                        log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
                        with open(log_path, "a", encoding="utf-8") as logf:
                            logf.write(f"[ERROR] Route: Incorrect password for protected PDF.\n")
                            logf.flush()
                        flash("error||Incorrect password for protected PDF.")
                        return redirect(url_for('pdf_to_jpg_route'))
                    print("[DEBUG] Authentication successful.")
                # Only access page count after authentication
                print(f"[DEBUG] Route: PDF has {doc.page_count} pages")
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
                try:
                    with open(log_path, "a", encoding="utf-8") as logf:
                        logf.write(f"\n[ERROR] Route failed to open/read PDF: {str(e)}\nTraceback:\n{tb}\n{'-'*60}\n")
                        logf.flush()
                    print(f"[ERROR] Route failed to open/read PDF: {e}\nTraceback written to: {log_path}")
                except Exception as log_e:
                    print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")
                flash(f"error||Failed to read PDF: {str(e)}")
                return redirect(url_for('pdf_to_jpg_route'))

            # Call the actual handler
            try:
                path = handle_pdf_to_jpg(file_bytes, password)
            except Exception as e:
                log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
                import traceback
                tb = traceback.format_exc()
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"[ERROR] Route: handle_pdf_to_jpg raised: {str(e)}\nTraceback:\n{tb}\n")
                    logf.flush()
                flash(f"error||{str(e)}")
                return redirect(url_for('pdf_to_jpg_route'))

            if not path or not os.path.exists(path):
                log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"[ERROR] Route: Failed to create output file.\n")
                    logf.flush()
                flash("error||Failed to create output file.")
                return redirect(url_for('pdf_to_jpg_route'))

            flash("success||PDF converted to JPG successfully.")

            def delayed_remove(file_path):
                time.sleep(2)  # Wait for 2 seconds to ensure file is not locked
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"[DEBUG] Cleaned up file: {file_path}")
                except Exception as e:
                    print(f"[ERROR] Failed to clean up file: {e}")

            @after_this_request
            def cleanup(response):
                threading.Thread(target=delayed_remove, args=(path,)).start()
                return response

            return send_file(path, as_attachment=True)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log_path = os.path.abspath(os.path.join("output", "pdf_to_jpg_error.log"))
            try:
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"\n[ERROR] Route outer exception: {str(e)}\nTraceback:\n{tb}\n{'-'*60}\n")
                    logf.flush()
                print(f"[ERROR] Route outer exception: {e}\nTraceback written to: {log_path}")
            except Exception as log_e:
                print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{log_e}")
            flash(f"error||{str(e)}")
            return redirect(url_for('pdf_to_jpg_route'))

    return render_template("pdf_to_jpg.html")

@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf_route():
    if request.method == 'POST':
        imgs = request.files.getlist('images')
        input_paths = []
        for img in imgs:
            img_path = os.path.join('uploads', img.filename)
            img.save(img_path)
            input_paths.append(img_path)
        try:
            path = handle_jpg_to_pdf([open(p, 'rb') for p in input_paths])
            if not path or not os.path.exists(path):
                flash("error||Failed to create output file.")
                for p in input_paths:
                    if os.path.exists(p):
                        os.remove(p)
                return redirect(url_for('jpg_to_pdf_route'))
        except Exception as e:
            flash(f"error||{str(e)}")
            for p in input_paths:
                if os.path.exists(p):
                    os.remove(p)
            return redirect(url_for('jpg_to_pdf_route'))
        flash("success||JPGs converted to PDF successfully.")
        @after_this_request
        def remove_files(response):
            try:
                for p in input_paths:
                    if os.path.exists(p):
                        os.remove(p)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return send_file(path, as_attachment=True)
    return render_template('jpg_to_pdf.html')


@app.route('/protect', methods=['GET', 'POST'])
def protect_route():
    if request.method == 'POST':
        file = request.files['pdf']
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        pwd = request.form['password']
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                if not pwd:
                    flash("error||This PDF is password protected. Please provide a password.")
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    return redirect(url_for('protect_route'))
                try:
                    reader.decrypt(pwd)
                except Exception:
                    flash("error||Incorrect password for protected PDF.")
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    return redirect(url_for('protect_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('protect_route'))
        path = handle_protect(input_path, pwd)
        if not path or not os.path.exists(path):
            flash("error||Failed to create output file.")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('protect_route'))
        @after_this_request
        def remove_files(response):
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return send_file(path, as_attachment=True)
    return render_template('protect.html')

@app.route('/watermark', methods=['GET', 'POST'])
def watermark_route():
    if request.method == 'POST':
        file = request.files['pdf']
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        watermark_text = request.form.get('watermark', '')
        image = request.files.get('image')
        image_path = None
        if image and image.filename:
            image_path = os.path.join('uploads', image.filename)
            image.save(image_path)
        font = request.form.get('font', 'Helvetica')
        color = request.form.get('color', '#000000')
        opacity = request.form.get('opacity', 0.3)
        img_position = request.form.get('img_position', 'center')
        img_scale = float(request.form.get('img_scale', 0.3))
        angle = float(request.form.get('angle', -45))
        try:
            reader = PdfReader(input_path)
            password = request.form.get('password', '')
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        if os.path.exists(input_path):
                            os.remove(input_path)
                        if image_path and os.path.exists(image_path):
                            os.remove(image_path)
                        return redirect(url_for('watermark_route'))
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                    return redirect(url_for('watermark_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            return redirect(url_for('watermark_route'))
        path = watermark.handle_watermark(
            open(input_path, 'rb'),
            watermark_text if watermark_text else None,
            open(image_path, 'rb') if image_path else None,
            font=font,
            color=color,
            opacity=opacity,
            img_position=img_position,
            img_scale=img_scale,
            angle=angle
        )
        if not path or not os.path.exists(path):
            flash("error||Failed to create output file.")
            if os.path.exists(input_path):
                os.remove(input_path)
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            return redirect(url_for('watermark_route'))
        @after_this_request
        def remove_files(response):
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return send_file(path, as_attachment=True)
    return render_template('watermark.html')


@app.route('/word-to-pdf', methods=['GET', 'POST'])
def word_to_pdf_route():
    if request.method == 'POST':
        file = request.files['docx']
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        try:
            # No password protection for docx
            path = handle_word_to_pdf(open(input_path, 'rb'))
            if not path or not os.path.exists(path):
                flash("error||Failed to create output file.")
                if os.path.exists(input_path):
                    os.remove(input_path)
                return redirect(url_for('word_to_pdf_route'))
        except Exception as e:
            flash(f"error||{str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('word_to_pdf_route'))
        @after_this_request
        def remove_files(response):
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return send_file(path, as_attachment=True)
    return render_template('word_to_pdf.html')

@app.route('/pdf-to-word', methods=['GET', 'POST'])
def pdf_to_word_route():
    if request.method == 'POST':
        file = request.files['pdf']
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        try:
            reader = PdfReader(input_path)
            password = request.form.get('password', '')
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        if os.path.exists(input_path):
                            os.remove(input_path)
                        return redirect(url_for('pdf_to_word_route'))
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    return redirect(url_for('pdf_to_word_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('pdf_to_word_route'))
        path = handle_pdf_to_word(open(input_path, 'rb'))
        if not path or not os.path.exists(path):
            flash("error||Failed to create output file.")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('pdf_to_word_route'))
        @after_this_request
        def remove_files(response):
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return send_file(path, as_attachment=True)
    return render_template('pdf_to_word.html')

@app.route('/check-pdf-protection', methods=['POST'])
def check_pdf_protection_merge():
    files = request.files.getlist('pdfs') or request.files.getlist('pdf')
    for file in files:
        try:
            reader = PdfReader(file)
            if reader.is_encrypted:
                return {'protected': True}
        except:
            return {'protected': True}
    return {'protected': False}

@app.route('/check-protection', methods=['POST'])
def check_protection():
    try:
        file = request.files.get("file")
        if not file:
            return {"protected": False}
        pdf_bytes = file.read()

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return {"protected": doc.needs_pass}
    except Exception as e:
        print(f"[ERROR] check_protection failed: {e}")
        return {"protected": False}

@app.route('/download/<filename>')
def download_file(filename):
    output_path = os.path.join('output', filename)
    if not os.path.exists(output_path):
        flash('error||File not found.')
        return redirect(url_for('compress_route'))
    return send_file(output_path, as_attachment=True)

@app.route('/compress', methods=['GET', 'POST'])
def compress_route():
    if request.method == 'POST':
        file = request.files.get('file')
        password = request.form.get('password', '')
        target_size = request.form.get('target_size')
        target_unit = request.form.get('target_unit', 'kb')
        lossless = bool(request.form.get('lossless'))
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        if target_size:
            target_size = int(target_size)
        else:
            target_size = None
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        if os.path.exists(input_path):
                            os.remove(input_path)
                        return redirect(url_for('compress_route'))
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    return redirect(url_for('compress_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('compress_route'))
        try:
            path = compress.handle_compress(open(input_path, 'rb'), password, target_size, target_unit, lossless)
            if not path or not os.path.exists(path):
                flash("error||Failed to create output file.")
                if os.path.exists(input_path):
                    os.remove(input_path)
                return redirect(url_for('compress_route'))
            # Check output file size
            if target_size:
                if target_unit == 'mb':
                    target_bytes = target_size * 1024 * 1024
                else:
                    target_bytes = target_size * 1024
                actual_size = os.path.getsize(path)
                if actual_size > target_bytes:
                    flash(f"warning||File could not be compressed to the requested size. Output: {round(actual_size/1024,2)} KB. Download is best effort.")
                else:
                    flash(f"success||File compressed to {round(actual_size/1024,2)} KB.")
            else:
                actual_size = os.path.getsize(path)
                flash(f"success||File compressed to {round(actual_size/1024,2)} KB.")
            session['compressed_file'] = os.path.basename(path)
        except Exception as e:
            flash(f"error||{str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('compress_route'))
        @after_this_request
        def remove_files(response):
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                app.logger.error(f"Error deleting files: {e}")
            return response
        return redirect(url_for('compress_route'))
    # GET request: show download link if available
    download_link = None
    if 'compressed_file' in session:
        filename = session.pop('compressed_file')
        download_link = url_for('download_file', filename=filename)
    return render_template('compress.html', download_link=download_link)

if __name__ == '__main__':
    app.run(debug=True)
