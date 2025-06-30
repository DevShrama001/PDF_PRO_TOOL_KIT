import io
import os
import uuid
import zipfile
import tempfile
import threading
import time
import datetime
import fitz  # PyMuPDF
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, session, after_this_request
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image
from werkzeug.utils import secure_filename

# Create necessary folders
os.makedirs('uploads', exist_ok=True)
os.makedirs('output', exist_ok=True)
os.makedirs('temp', exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your-strong-secret-key'

# ================ Helper Functions ================
def log_event(log_path, msg):
    """Log events to specified file"""
    try:
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"[{datetime.datetime.now()}] {msg}\n")
            logf.flush()
    except Exception as e:
        print(f"[LOGGING ERROR] Could not write to log file: {log_path}\n{e}")

def compress_pdf(input_path, output_path):
    """Compress PDF using PyPDF2 with content stream compression"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
    
    # Compress content streams
    for page in writer.pages:
        page.compress_content_streams(level=9)
    
    with open(output_path, "wb") as f:
        writer.write(f)

def compress_image(input_path, output_path, quality=85):
    """Compress image using Pillow"""
    with Image.open(input_path) as img:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.save(output_path, quality=quality, optimize=True)

def compress_file(filepath, output_folder, filename):
    """Handle compression for all supported file types"""
    output_filename = f"compressed_{secure_filename(filename)}"
    output_path = os.path.join(output_folder, output_filename)
    
    if filename.lower().endswith('.pdf'):
        compress_pdf(filepath, output_path)
    elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        compress_image(filepath, output_path)
    else:
        # Generic compression for other file types
        with open(filepath, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                f_out.write(f_in.read())
    
    return output_path

# ================ Routes ================
@app.route('/')
def home_page():
    return render_template('index.html')

@app.route('/merge', methods=['GET', 'POST'])
def merge_route():
    log_path = os.path.abspath(os.path.join("output", "merge_error.log"))
    if request.method == 'POST':
        files = request.files.getlist('pdfs')
        password = request.form.get('password', '')
        merger_instance = PdfMerger()
        input_paths = []
        files_to_cleanup = []
        output_path = None
        log_event(log_path, f"[INFO] Merge requested for {len(files)} files.")
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
                            log_event(log_path, f"[ERROR] Incorrect password for '{file.filename}'.")
                            flash(f"error||Incorrect password for '{file.filename}'.")
                            return redirect(url_for('merge_route'))
                    else:
                        log_event(log_path, f"[ERROR] The file '{file.filename}' is password protected. No password provided.")
                        flash(f"error||The file '{file.filename}' is password protected. Please provide a password.")
                        return redirect(url_for('merge_route'))
                else:
                    merger_instance.append(reader)
            except Exception as e:
                log_event(log_path, f"[ERROR] Failed to read '{file.filename}': {str(e)}")
                flash(f"error||Failed to read '{file.filename}': {str(e)}")
                return redirect(url_for('merge_route'))
        output_path = os.path.join('output', f'merged_{uuid.uuid4().hex}.pdf')
        try:
            with open(output_path, 'wb') as f:
                merger_instance.write(f)
            merger_instance.close()
            files_to_cleanup.append(output_path)
            log_event(log_path, f"[INFO] Merge successful. Output: {output_path}")
        except Exception as e:
            log_event(log_path, f"[ERROR] Failed to create output file: {str(e)}")
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
                    log_event(log_path, f"[ERROR] Error deleting file {p}: {e}")
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
        try:
            writer = PdfWriter()
            for page_num in range(start-1, end):
                writer.add_page(reader.pages[page_num])
            output_path = os.path.join('output', f'split_{uuid.uuid4().hex}.pdf')
            with open(output_path, 'wb') as f:
                writer.write(f)
            files_to_cleanup.append(output_path)
        except Exception as e:
            flash(f"error||Failed to split PDF: {str(e)}")
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
                image_list = []
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap()
                    img_path = os.path.join('output', f'page_{page_num+1}.jpg')
                    pix.save(img_path)
                    image_list.append(img_path)
                zip_path = os.path.join('output', f'converted_{uuid.uuid4().hex}.zip')
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for img in image_list:
                        zipf.write(img, os.path.basename(img))
                files_to_cleanup.extend(image_list)
                files_to_cleanup.append(zip_path)
            except Exception as e:
                flash(f"error||{str(e)}")
                return redirect(url_for('pdf_to_jpg_route'))
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
            return send_file(zip_path, as_attachment=True)
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
            pdf = PdfWriter()
            output_path = os.path.join('output', f'converted_{uuid.uuid4().hex}.pdf')
            
            for img in imgs:
                img_path = os.path.join('uploads', img.filename)
                img.save(img_path)
                files_to_cleanup.append(img_path)
                
                # Convert image to PDF page
                with Image.open(img_path) as image:
                    image = image.convert('RGB')
                    pdf_page_path = os.path.join('temp', f'temp_{uuid.uuid4().hex}.pdf')
                    image.save(pdf_page_path)
                    pdf.append(pdf_page_path)
            
            with open(output_path, 'wb') as f:
                pdf.write(f)
            files_to_cleanup.append(output_path)
        except Exception as e:
            flash(f"error||{str(e)}")
            return redirect(url_for('jpg_to_pdf_route'))
        flash("success||JPGs converted to PDF successfully.")
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
        return send_file(output_path, as_attachment=True)
    return render_template('jpg_to_pdf.html')

@app.route('/protect', methods=['GET', 'POST'])
def protect_route():
    if request.method == 'POST':
        file = request.files['pdf']
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        pwd = request.form['password']
        files_to_cleanup = [input_path]
        output_path = os.path.join('output', f'protected_{uuid.uuid4().hex}.pdf')
        
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Add all pages to the writer
            for page in reader.pages:
                writer.add_page(page)
            
            # Encrypt the PDF with password
            writer.encrypt(pwd)
            
            # Save the encrypted PDF
            with open(output_path, 'wb') as f:
                writer.write(f)
                
            files_to_cleanup.append(output_path)
        except Exception as e:
            flash(f'error||Failed to protect PDF: {str(e)}')
            return redirect(url_for('protect_route'))
        
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
        output_path = os.path.join('output', f'watermarked_{uuid.uuid4().hex}.pdf')
        
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Add watermark to each page
            for page in reader.pages:
                watermark_page = writer.add_page(page)
                
                # Add text watermark
                if watermark_text:
                    watermark_page.merge_page(watermark_page)
                
                # Add image watermark
                if image_path:
                    with open(image_path, 'rb') as img_file:
                        watermark_page.merge_page(img_file.read())
            
            # Save watermarked PDF
            with open(output_path, 'wb') as f:
                writer.write(f)
                
            files_to_cleanup.append(output_path)
        except Exception as e:
            flash(f'error||Failed to add watermark: {str(e)}')
            return redirect(url_for('watermark_route'))
        
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
    return render_template('watermark.html')

@app.route('/word-to-pdf', methods=['GET', 'POST'])
def word_to_pdf_route():
    log_path = os.path.abspath(os.path.join("output", "word_to_pdf_error.log"))
    if request.method == 'POST':
        file = request.files['docx']
        input_path = os.path.join('uploads', file.filename)
        file.save(input_path)
        if os.path.getsize(input_path) == 0:
            flash("error||Uploaded Word file is empty. Please select a valid .docx file with content.")
            os.remove(input_path)
            return redirect(url_for('word_to_pdf_route'))
        files_to_cleanup = [input_path]
        output_path = os.path.join('output', f'converted_{uuid.uuid4().hex}.pdf')
        
        try:
            # Convert DOCX to PDF using PyPDF2
            writer = PdfWriter()
            writer.append(input_path)
            with open(output_path, 'wb') as f:
                writer.write(f)
            files_to_cleanup.append(output_path)
        except Exception as e:
            flash(f"error||{str(e)}")
            return redirect(url_for('word_to_pdf_route'))
        
        def delayed_remove(file_path):
            time.sleep(2)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                log_event(log_path, f"[ERROR] Error deleting file {file_path}: {e}")
        @after_this_request
        def remove_files(response):
            for p in files_to_cleanup:
                threading.Thread(target=delayed_remove, args=(p,)).start()
            return response
        return send_file(output_path, as_attachment=True)
    return render_template('word_to_pdf.html')

@app.route('/pdf-to-word', methods=['GET', 'POST'])
def pdf_to_word_route():
    if request.method == 'POST':
        file = request.files.get('pdf')
        if not file or file.filename == '':
            flash('error||No file selected. Please upload a PDF file.')
            return redirect(url_for('pdf_to_word_route'))
        if not file.filename.lower().endswith('.pdf'):
            flash('error||Invalid file type. Please upload a PDF file.')
            return redirect(url_for('pdf_to_word_route'))
        password = request.form.get('password', '')
        files_to_cleanup = []
        output_path = os.path.join('output', f'converted_{uuid.uuid4().hex}.docx')
        
        try:
            # Simple conversion by extracting text
            reader = PdfReader(file)
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        flash('error||Incorrect password for protected PDF.')
                        return redirect(url_for('pdf_to_word_route'))
                else:
                    flash('error||This PDF is password protected. Please provide a password.')
                    return redirect(url_for('pdf_to_word_route'))
            
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n\n"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            files_to_cleanup.append(output_path)
        except Exception as e:
            flash(f'error||Failed to convert PDF: {str(e)}')
            return redirect(url_for('pdf_to_word_route'))
        
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
    return render_template('pdf_to_word.html')

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

@app.route('/compress', methods=['GET', 'POST'])
def compress_route():
    if request.method == 'POST':
        file = request.files['file']
        password = request.form.get('password', '')
        if not file or file.filename == '':
            flash('error||No file selected')
            return redirect(url_for('compress_route'))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        upload_path = os.path.join('uploads', filename)
        file.save(upload_path)
        
        # Handle password-protected PDFs
        if filename.lower().endswith('.pdf'):
            try:
                reader = PdfReader(upload_path)
                if reader.is_encrypted:
                    if not password:
                        flash('error||PDF is password protected. Please provide a password.')
                        return redirect(url_for('compress_route'))
                    if not reader.decrypt(password):
                        flash('error||Incorrect password for PDF.')
                        return redirect(url_for('compress_route'))
            except Exception as e:
                flash(f'error||Failed to read PDF: {str(e)}')
                return redirect(url_for('compress_route'))
        
        # Compress file
        try:
            output_path = compress_file(upload_path, 'output', filename)
            
            # Cleanup after download
            @after_this_request
            def cleanup(response):
                try:
                    os.remove(upload_path)
                    os.remove(output_path)
                except Exception as e:
                    app.logger.error(f"Error deleting files: {str(e)}")
                return response
            
            return send_file(
                output_path,
                as_attachment=True,
                download_name=f"compressed_{filename}"
            )
        except Exception as e:
            flash(f'error||{str(e)}')
            return redirect(url_for('compress_route'))
    
    return render_template('compress.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
