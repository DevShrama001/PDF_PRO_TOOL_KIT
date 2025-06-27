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
    import datetime
    log_path = os.path.abspath(os.path.join("output", "merge_error.log"))
    def log_event(msg):
        try:
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"[{datetime.datetime.now()}] {msg}\n")
                logf.flush()
        except Exception as e:
            print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{e}")
    if request.method == 'POST':
        files = request.files.getlist('pdfs')
        password = request.form.get('password', '')
        merger_instance = PdfMerger()
        input_paths = []
        files_to_cleanup = []
        output_path = None
        log_event(f"[INFO] Merge requested for {len(files)} files.")
        for file in files:
            path = os.path.join('uploads', file.filename)
            file.save(path)
            input_paths.append(path)
            files_to_cleanup.append(path)
            try:
                reader = PdfReader(path)
                if reader.is_encrypted:
                    if password:
                        try:
                            reader.decrypt(password)
                            merger_instance.append(reader)
                        except Exception:
                            log_event(f"[ERROR] Incorrect password for '{file.filename}'.")
                            flash(f"error||Incorrect password for '{file.filename}'.")
                            return redirect(url_for('merge_route'))
                    else:
                        log_event(f"[ERROR] The file '{file.filename}' is password protected. No password provided.")
                        flash(f"error||The file '{file.filename}' is password protected. Please provide a password.")
                        return redirect(url_for('merge_route'))
                else:
                    merger_instance.append(reader)
            except Exception as e:
                log_event(f"[ERROR] Failed to read '{file.filename}': {str(e)}")
                flash(f"error||Failed to read '{file.filename}': {str(e)}")
                return redirect(url_for('merge_route'))
        output_path = os.path.join('output', f'merged_{uuid.uuid4().hex}.pdf')
        try:
            with open(output_path, 'wb') as f:
                merger_instance.write(f)
            merger_instance.close()
            files_to_cleanup.append(output_path)
            log_event(f"[INFO] Merge successful. Output: {output_path}")
        except Exception as e:
            log_event(f"[ERROR] Failed to create output file: {str(e)}")
            flash(f"error||Failed to create output file: {str(e)}")
            return redirect(url_for('merge_route'))
        flash("success||PDFs merged successfully and downloading.")
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    log_event(f"[ERROR] Error deleting file {p}: {e}")
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
        output_path = None
        files_to_cleanup = [input_path]
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        return redirect(request.url)
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    return redirect(request.url)
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            return redirect(request.url)
        output_path = split.handle_split(file, start, end, password)
        if output_path:
            files_to_cleanup.append(output_path)
        else:
            flash("error||Failed to create output file.")
            return redirect(request.url)
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    app.logger.error(f"Error deleting file {p}: {e}")
            return response
        return send_file(output_path, as_attachment=True)
    return render_template("split.html")

@app.route('/pdf-to-jpg', methods=['GET', 'POST'])
def pdf_to_jpg_route():
    if request.method == 'POST':
        files_to_cleanup = []
        try:
            file = request.files.get('pdf')
            if not file:
                flash("error||No file selected.")
                return redirect(url_for('pdf_to_jpg_route'))
            password = request.form.get('password', '')
            file_bytes = file.read()
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if doc.needs_pass:
                    if not password:
                        flash("error||This PDF is password protected. Please provide a password.")
                        return redirect(url_for('pdf_to_jpg_route'))
                    if not doc.authenticate(password):
                        flash("error||Incorrect password for protected PDF.")
                        return redirect(url_for('pdf_to_jpg_route'))
            except Exception as e:
                flash(f"error||Failed to read PDF: {str(e)}")
                return redirect(url_for('pdf_to_jpg_route'))
            try:
                path = handle_pdf_to_jpg(file_bytes, password)
            except Exception as e:
                flash(f"error||{str(e)}")
                return redirect(url_for('pdf_to_jpg_route'))
            if not path or not os.path.exists(path):
                flash("error||Failed to create output file.")
                return redirect(url_for('pdf_to_jpg_route'))
            files_to_cleanup.append(path)
            flash("success||PDF converted to JPG successfully.")
            @after_this_request
            def cleanup(response):
                for p in files_to_cleanup:
                    try:
                        if p and os.path.exists(p):
                            os.remove(p)
                    except Exception as e:
                        app.logger.error(f"Error deleting file {p}: {e}")
                return response
            return send_file(path, as_attachment=True)
        except Exception as e:
            flash(f"error||{str(e)}")
            return redirect(url_for('pdf_to_jpg_route'))
    return render_template("pdf_to_jpg.html")

@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf_route():
    if request.method == 'POST':
        imgs = request.files.getlist('images')
        files_to_cleanup = []
        try:
            path = handle_jpg_to_pdf(imgs)
            if not path or not os.path.exists(path):
                flash("error||Failed to create output file.")
                return redirect(url_for('jpg_to_pdf_route'))
            files_to_cleanup.append(path)
        except Exception as e:
            for img in imgs:
                try:
                    os.remove(os.path.join('uploads', img.filename))
                except Exception:
                    pass
            flash(f"error||{str(e)}")
            return redirect(url_for('jpg_to_pdf_route'))
        flash("success||JPGs converted to PDF successfully.")
        import threading, time
        def delayed_remove(file_path):
            time.sleep(2)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                app.logger.error(f"Error deleting file {file_path}: {e}")
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                threading.Thread(target=delayed_remove, args=(p,)).start()
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
        files_to_cleanup = [input_path]
        path = None
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                if not pwd:
                    flash("error||This PDF is password protected. Please provide a password.")
                    return redirect(url_for('protect_route'))
                try:
                    reader.decrypt(pwd)
                except Exception:
                    flash("error||Incorrect password for protected PDF.")
                    return redirect(url_for('protect_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            return redirect(url_for('protect_route'))
        path = handle_protect(input_path, pwd)
        if not path or not os.path.exists(path):
            flash("error||Failed to create output file.")
            return redirect(url_for('protect_route'))
        files_to_cleanup.append(path)
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    app.logger.error(f"Error deleting file {p}: {e}")
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
        files_to_cleanup = [input_path]
        if image and image.filename:
            image_path = os.path.join('uploads', image.filename)
            image.save(image_path)
            files_to_cleanup.append(image_path)
        font = request.form.get('font', 'Helvetica')
        color = request.form.get('color', '#000000')
        opacity = request.form.get('opacity', 0.3)
        img_position = request.form.get('img_position', 'center')
        img_scale = float(request.form.get('img_scale', 0.3))
        angle = float(request.form.get('angle', -45))
        path = None
        try:
            reader = PdfReader(input_path)
            password = request.form.get('password', '')
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        return redirect(url_for('watermark_route'))
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    return redirect(url_for('watermark_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
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
            return redirect(url_for('watermark_route'))
        files_to_cleanup.append(path)
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    app.logger.error(f"Error deleting file {p}: {e}")
            return response
        return send_file(path, as_attachment=True)
    return render_template('watermark.html')


@app.route('/word-to-pdf', methods=['GET', 'POST'])
def word_to_pdf_route():
    import datetime
    log_path = os.path.abspath(os.path.join("output", "word_to_pdf_error.log"))
    def log_event(msg):
        try:
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"[{datetime.datetime.now()}] {msg}\n")
                logf.flush()
        except Exception as e:
            print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{e}")
    if request.method == 'POST':
        file = request.files['docx']
        print("[DEBUG] file.filename:", file.filename)
        print("[DEBUG] file.content_length:", getattr(file, 'content_length', 'N/A'))
        print("[DEBUG] file.mimetype:", file.mimetype)
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        print("[DEBUG] Saved file size:", os.path.getsize(input_path))
        # Check for empty file
        if os.path.getsize(input_path) == 0:
            log_event(f"[ERROR] Uploaded DOCX is empty: {input_path}")
            flash("error||Uploaded Word file is empty. Please select a valid .docx file with content.")
            os.remove(input_path)
            return redirect(url_for('word_to_pdf_route'))
        files_to_cleanup = [input_path]
        path = None
        try:
            log_event(f"[INFO] Word to PDF requested for file: {file.filename}")
            # Pass file path instead of file object
            path = handle_word_to_pdf(input_path)
            if not path or not os.path.exists(path):
                log_event(f"[ERROR] Failed to create output file for: {file.filename}")
                flash("error||Failed to create output file.")
                return redirect(url_for('word_to_pdf_route'))
            files_to_cleanup.append(path)
            log_event(f"[INFO] Word to PDF conversion successful. Output: {path}")
        except Exception as e:
            log_event(f"[ERROR] Exception: {str(e)}")
            if "CoInitialize has not been called" in str(e):
                flash("error||Word automation failed on the server. Please try again later or contact support.")
            else:
                flash(f"error||{str(e)}")
            return redirect(url_for('word_to_pdf_route'))
        import threading, time
        def delayed_remove(file_path):
            time.sleep(2)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                log_event(f"[ERROR] Error deleting file {file_path}: {e}")
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                threading.Thread(target=delayed_remove, args=(p,)).start()
            return response
        return send_file(path, as_attachment=True)
    return render_template('word_to_pdf.html')

@app.route('/pdf-to-word', methods=['GET', 'POST'])
def pdf_to_word_route():
    if request.method == 'POST':
        file = request.files['pdf']
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        files_to_cleanup = [input_path]
        path = None
        try:
            reader = PdfReader(input_path)
            password = request.form.get('password', '')
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        return redirect(url_for('pdf_to_word_route'))
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    return redirect(url_for('pdf_to_word_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            return redirect(url_for('pdf_to_word_route'))
        # Pass FileStorage object directly
        path = handle_pdf_to_word(file)
        if not path or not os.path.exists(path):
            flash("error||Failed to create output file.")
            return redirect(url_for('pdf_to_word_route'))
        files_to_cleanup.append(path)
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    app.logger.error(f"Error deleting file {p}: {e}")
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
        files_to_cleanup = [input_path]
        if target_size:
            target_size = int(target_size)
        else:
            target_size = None
        path = None
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash("error||Incorrect password for protected PDF.")
                        return redirect(url_for('compress_route'))
                else:
                    flash("error||This PDF is password protected. Please provide a password.")
                    return redirect(url_for('compress_route'))
        except Exception as e:
            flash(f"error||Failed to read PDF: {str(e)}")
            return redirect(url_for('compress_route'))
        try:
            path = compress.handle_compress(open(input_path, 'rb'), password, target_size, target_unit, lossless)
            if not path or not os.path.exists(path):
                flash("error||Failed to create output file.")
                return redirect(url_for('compress_route'))
            files_to_cleanup.append(path)
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
            return redirect(url_for('compress_route'))
        @after_this_request
        def remove_files(response):
            import threading, time
            def delayed_remove(file_path):
                time.sleep(2)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    app.logger.error(f"Error deleting file {file_path}: {e}")
            for p in files_to_cleanup:
                threading.Thread(target=delayed_remove, args=(p,)).start()
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
