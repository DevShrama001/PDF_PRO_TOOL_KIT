import os
import sys
import importlib
from docx import Document

# reload module after monkeypatching pythoncom

def create_sample_docx(path):
    doc = Document()
    doc.add_paragraph("Hello")
    doc.save(path)


def fake_convert(in_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(in_path))[0]
    out_file = os.path.join(out_dir, f"{base}.pdf")
    with open(out_file, "wb") as f:
        f.write(b"%PDF-1.4")

def test_word_to_pdf_basic(monkeypatch, tmp_path):
    docx_path = tmp_path / "sample.docx"
    create_sample_docx(docx_path)

    monkeypatch.setattr('docx2pdf.convert', fake_convert)

    # Simulate absence of pythoncom
    if 'pythoncom' in sys.modules:
        monkeypatch.setitem(sys.modules, 'pythoncom', None)

    import Convertor_pdf.tools.word_to_pdf as mod
    importlib.reload(mod)

    monkeypatch.chdir(tmp_path)
    pdf_path = mod.handle_word_to_pdf(str(docx_path))

    assert os.path.exists(pdf_path)
    assert not docx_path.exists()

