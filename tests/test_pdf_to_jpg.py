import os
from PyPDF2 import PdfWriter

from Convertor_pdf.tools.pdf_to_jpg import handle_pdf_to_jpg


def create_sample_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(path, 'wb') as f:
        writer.write(f)


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
