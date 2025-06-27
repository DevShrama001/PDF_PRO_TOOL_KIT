import os
import sys
import importlib
import types
import pytest

class DummyPDF:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    def save(self, output_path, encryption=None):
        with open(output_path, "wb") as f:
            f.write(b"PDF")

def test_handle_protect_masks_password(tmp_path, monkeypatch, capsys):
    input_pdf = tmp_path / "in.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%%EOF")

    # monkeypatch pikepdf.open and pikepdf.Encryption
    dummy_module = types.SimpleNamespace(
        open=lambda path: DummyPDF(),
        Encryption=lambda owner, user, R: None,
    )
    monkeypatch.setitem(sys.modules, 'pikepdf', dummy_module)
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import Convertor_pdf.tools.protect as protect
    importlib.reload(protect)

    out_path = protect.handle_protect(str(input_pdf), "secret")

    captured = capsys.readouterr().out
    assert "secret" not in captured
    assert os.path.exists(out_path)
    os.remove(out_path)
