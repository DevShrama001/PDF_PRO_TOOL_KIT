import os
import pytest
try:
    from PyPDF2 import PdfWriter
except ModuleNotFoundError:
    PdfWriter = None
    pytest.skip("PyPDF2 not installed", allow_module_level=True)
try:
    import fitz
except ModuleNotFoundError:
    fitz = None
    pytest.skip("PyMuPDF not installed", allow_module_level=True)


def create_sample_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(path, 'wb') as f:
        writer.write(f)


def handle_pdf_to_jpg(pdf_bytes, password=None):
    """
    Converts a PDF (as bytes) to JPG images and returns the path to a zip file containing the images.
    """
    import tempfile
    import zipfile
    import os
    import uuid
    temp_dir = tempfile.mkdtemp()
    images = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.needs_pass:
            if not password or not doc.authenticate(password):
                raise Exception("Incorrect or missing password for protected PDF.")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img_path = os.path.join(temp_dir, f'page_{page_num + 1}.jpg')
            pix.save(img_path)
            images.append(img_path)
        if not images:
            raise Exception("No images generated from PDF.")
        zip_path = os.path.join(temp_dir, f'pdf_to_jpg_{uuid.uuid4().hex}.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for img in images:
                zipf.write(img, arcname=os.path.basename(img))
        return zip_path
    except Exception as e:
        raise Exception(f"PDF to JPG conversion failed: {str(e)}")
    # Note: temp_dir will be cleaned up by the route after download


def test_temporary_directory_cleanup(monkeypatch, tmp_path):
    pdf_file = tmp_path / 'sample.pdf'
    create_sample_pdf(pdf_file)
    data = pdf_file.read_bytes()

    created_dirs = []

    def fake_mkdtemp():
        d = tmp_path / 'tempdir'
        os.mkdir(d)
        created_dirs.append(d)
        return str(d)

    monkeypatch.setattr('tempfile.mkdtemp', fake_mkdtemp)

    zip_path = handle_pdf_to_jpg(data)
    assert os.path.exists(zip_path)

    # ensure temporary directory removed
    assert not any(d.exists() for d in created_dirs)
    os.remove(zip_path)
