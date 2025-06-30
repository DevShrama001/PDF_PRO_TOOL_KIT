import os
import uuid
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from docx import Document
import zipfile
import shutil
import tempfile

def compress_docx_images(docx_path, output_path, image_quality=40):
    # Extract DOCX
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(docx_path, 'r') as zin:
            zin.extractall(tmpdir)
        # Compress images in word/media
        media_dir = os.path.join(tmpdir, 'word', 'media')
        if os.path.exists(media_dir):
            for fname in os.listdir(media_dir):
                fpath = os.path.join(media_dir, fname)
                try:
                    img = Image.open(fpath)
                    if img.format in ['JPEG', 'JPG', 'PNG']:
                        img = img.convert('RGB')
                        img.save(fpath, format='JPEG', quality=image_quality, optimize=True)
                except Exception:
                    pass  # Not an image or can't compress
        # Repackage DOCX
        with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, tmpdir)
                    zout.write(abs_path, rel_path)

def handle_compress(file, password="", target_size=None, target_unit="kb", lossless=False):
    ext = os.path.splitext(file.filename)[-1].lower()
    input_path = f'uploads/{uuid.uuid4().hex}{ext}'
    output_path = f'output/compressed_{uuid.uuid4().hex}{ext}'
    file.save(input_path)

    try:
        if ext == ".pdf":
            try:
                reader = PdfReader(input_path)
                if reader.is_encrypted:
                    if not password:
                        raise Exception("This PDF is protected. Please provide a password.")
                    try:
                        reader.decrypt(password)
                    except:
                        raise Exception("Incorrect PDF password.")
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                with open(output_path, "wb") as f_out:
                    writer.write(f_out)
            except Exception as e:
                # Clean up temp files on error
                if os.path.exists(input_path):
                    os.remove(input_path)
                raise e
            # Always try Ghostscript for compression
            try:
                import subprocess, shutil as sh
                # Allow manual override via environment variable
                gs_env_path = os.environ.get('GHOSTSCRIPT_PATH')
                gs_executables = []
                if gs_env_path:
                    gs_executables.append(gs_env_path)
                gs_executables += ['gs', 'gswin64c', 'gswin32c']
                gs_path = None
                for exe in gs_executables:
                    if sh.which(exe):
                        gs_path = exe
                        break
                if not gs_path:
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    raise Exception("Ghostscript not found. Please install Ghostscript and add it to your PATH, or set the GHOSTSCRIPT_PATH environment variable to the full path of gswin32c.exe or gswin64c.exe.")
                gs_output = output_path.replace('.pdf', '_gs.pdf')
                # Use /screen for most aggressive compression
                gs_cmd = [
                    gs_path, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen',
                    '-dNOPAUSE', '-dQUIET', '-dBATCH',
                    f'-sOutputFile={gs_output}', output_path
                ]
                result = subprocess.run(gs_cmd, capture_output=True)
                if result.returncode != 0:
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    if os.path.exists(gs_output):
                        os.remove(gs_output)
                    raise Exception(f"Ghostscript compression failed: {result.stderr.decode(errors='ignore')}")
                # Always keep the Ghostscript output, even if not smaller
                if os.path.exists(gs_output):
                    os.replace(gs_output, output_path)
            except Exception as e:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
                raise Exception(f"PDF compression failed: {str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)

        elif ext in [".jpg", ".jpeg", ".png"]:
            img = Image.open(input_path)
            if lossless or ext == ".png":
                output_path = output_path.rsplit('.', 1)[0] + '.png'
                img.save(output_path, optimize=True)
            else:
                rgb_img = img.convert('RGB')
                output_path = output_path.rsplit('.', 1)[0] + '.jpg'
                quality = 40
                rgb_img.save(output_path, optimize=True, quality=quality)
                if target_size:
                    if target_unit == "mb":
                        target_bytes = int(target_size) * 1024 * 1024
                    else:
                        target_bytes = int(target_size) * 1024
                    # Aggressively reduce quality and size
                    while os.path.getsize(output_path) > target_bytes and quality > 5:
                        quality -= 5
                        rgb_img.save(output_path, optimize=True, quality=quality)
                    # If still too big, resize
                    while os.path.getsize(output_path) > target_bytes and rgb_img.width > 100 and rgb_img.height > 100:
                        rgb_img = rgb_img.resize((int(rgb_img.width * 0.9), int(rgb_img.height * 0.9)), Image.LANCZOS)
                        rgb_img.save(output_path, optimize=True, quality=quality)
                    if os.path.getsize(output_path) > target_bytes:
                        if os.path.exists(input_path):
                            os.remove(input_path)
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        raise Exception("Image could not be compressed to the requested size. Try a smaller target or lower quality.")
            if os.path.exists(input_path):
                os.remove(input_path)
            # Return output_path for direct download
            return output_path

        elif ext in [".docx", ".doc"]:
            if not lossless:
                compress_docx_images(input_path, output_path, image_quality=40)
            else:
                with zipfile.ZipFile(input_path, 'r') as zin:
                    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                        for item in zin.infolist():
                            buffer = zin.read(item.filename)
                            zout.writestr(item, buffer)
            # Check if compression worked
            if target_size:
                if target_unit == "mb":
                    target_bytes = int(target_size) * 1024 * 1024
                else:
                    target_bytes = int(target_size) * 1024
                if os.path.getsize(output_path) > target_bytes:
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    raise Exception("DOCX could not be compressed to the requested size. Try a smaller target or lower quality images.")
            if os.path.exists(input_path):
                os.remove(input_path)
        else:
            if os.path.exists(input_path):
                os.remove(input_path)
            raise Exception("Unsupported file format")

        # Final check: if output is not smaller, warn
        if target_size:
            if target_unit == "mb":
                target_bytes = int(target_size) * 1024 * 1024
            else:
                target_bytes = int(target_size) * 1024
            if os.path.getsize(output_path) > target_bytes:
                if os.path.exists(output_path):
                    os.remove(output_path)
                raise Exception("File could not be compressed to the requested size. Try a smaller target or lower quality.")
        # If output is not smaller than input, warn
        # (Do not delete output, just warn)
    except Exception as e:
        # On error, clean up and raise error for feedback
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e
    return output_path
