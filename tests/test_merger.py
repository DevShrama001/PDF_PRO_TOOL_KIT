import os
import shutil
import types
import pytest

try:
    from PyPDF2 import PdfWriter
except ModuleNotFoundError:
    PdfWriter = None
    pytest.skip("PyPDF2 not installed", allow_module_level=True)

from Convertor_pdf.tools.merger import handle_merge

class DummyFile:
    def __init__(self, path, filename):
        self._path = path
        self.filename = filename
    def save(self, dst):
        shutil.copy(self._path, dst)


def create_sample_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as f:
        writer.write(f)


def test_handle_merge_creates_output_and_cleans(tmp_path, monkeypatch):
    pdf1 = tmp_path / "a.pdf"
    pdf2 = tmp_path / "b.pdf"
    create_sample_pdf(pdf1)
    create_sample_pdf(pdf2)

    files = [DummyFile(str(pdf1), "a.pdf"), DummyFile(str(pdf2), "b.pdf")]

    monkeypatch.chdir(tmp_path)
    out_path = handle_merge(files)

    assert os.path.exists(out_path)
    assert os.listdir("uploads") == []
    os.remove(out_path)
