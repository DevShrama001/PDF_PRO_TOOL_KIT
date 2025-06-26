import io
import os
import uuid
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file
from PyPDF2 import PdfMerger, PdfReader
from tools import compress, merger, split, pdf_to_jpg, watermark
from tools.jpg_to_pdf import handle_jpg_to_pdf
from tools.protect import handle_protect
from tools.word_to_pdf import handle_word_to_pdf
from tools.pdf_to_word import handle_pdf_to_word

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

        for file in files:
            path = os.path.join('uploads', file.filename)
            file.save(path)
            reader = PdfReader(path)
            if reader.is_encrypted:
                if password:
                    try:
                        reader.decrypt(password)
                        merger_instance.append(reader)
                    except:
                        flash(f"error||Incorrect password for '{file.filename}'.")
                        return redirect(url_for('merge_route'))
                else:
                    flash(f"error||The file '{file.filename}' is password protected. Please provide a password.")
                    return redirect(url_for('merge_route'))
            else:
                merger_instance.append(reader)

        output_path = os.path.join('output', f'merged_{uuid.uuid4().hex}.pdf')
        with open(output_path, 'wb') as f:
            merger_instance.write(f)
        merger_instance.close()

        flash("success||PDFs merged successfully and downloading.")
        return send_file(output_path, as_attachment=True)

    return render_template('merge.html')

@app.route("/split", methods=["GET", "POST"])
def split_route():
    if request.method == "POST":
        file = request.files["pdf"]
        start = int(request.form["start"])
        end = int(request.form["end"])
        password = request.form.get("password", "")
        path = split.handle_split(file, start, end, password)
        if path is None:
            return redirect(request.url)
        return send_file(path, as_attachment=True)
    return render_template("split.html")

@app.route('/pdf-to-jpg', methods=['GET', 'POST'])
def pdf_to_jpg_route():
    if request.method == 'POST':
        try:
            file = request.files.get('pdf')
            password = request.form.get('password', '')

            if not file:
                flash("error||No file selected.")
                return redirect(url_for('pdf_to_jpg_route'))

            print("[DEBUG] File received:", file.filename)

            path = pdf_to_jpg.handle_pdf_to_jpg(file, password)
            flash("success||PDF converted to JPG successfully.")
            return send_file(path, as_attachment=True)

        except Exception as e:
            print("[DEBUG] Exception in JPG route:", e)
            flash(f"error||{str(e)}")
            return redirect(url_for('pdf_to_jpg_route'))

    return render_template('pdf_to_jpg.html')

@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf_route():
    if request.method == 'POST':
        imgs = request.files.getlist('images')
        path = handle_jpg_to_pdf(imgs)
        flash("success||JPGs converted to PDF successfully.")
        return send_file(path, as_attachment=True)
    return render_template('jpg_to_pdf.html')


@app.route('/protect', methods=['GET', 'POST'])
def protect_route():
    if request.method == 'POST':
        file = request.files['pdf']
        pwd = request.form['password']
        path = handle_protect(file, pwd)
        return send_file(path, as_attachment=True)
    return render_template('protect.html')

@app.route('/watermark', methods=['GET', 'POST'])
def watermark_route():
    if request.method == 'POST':
        file = request.files['pdf']
        watermark_text = request.form.get('watermark', '')
        image = request.files.get('image')
        color = request.form.get('color', '#000000')
        opacity = request.form.get('opacity', 0.3)
        path = watermark.handle_watermark(file, watermark_text, image, color=color, opacity=opacity)
        return send_file(path, as_attachment=True)
    return render_template('watermark.html')


@app.route('/word-to-pdf', methods=['GET', 'POST'])
def word_to_pdf_route():
    if request.method == 'POST':
        file = request.files['docx']
        path = handle_word_to_pdf(file)
        return send_file(path, as_attachment=True)
    return render_template('word_to_pdf.html')

@app.route('/pdf-to-word', methods=['GET', 'POST'])
def pdf_to_word_route():
    if request.method == 'POST':
        file = request.files['pdf']
        path = handle_pdf_to_word(file)
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
def check_pdf_protection_single():
    if 'file' not in request.files:
        return jsonify({'protected': False})

    file = request.files['file']
    if file.filename.endswith('.pdf'):
        try:
            reader = PdfReader(io.BytesIO(file.read()))
            return jsonify({'protected': reader.is_encrypted})
        except:
            return jsonify({'protected': False})
    return jsonify({'protected': False})

if __name__ == '__main__':
    app.run(debug=True)
