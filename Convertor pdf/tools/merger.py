import os
import shutil
import uuid
from PyPDF2 import PdfMerger

def handle_merge(files):
    """
    Merges multiple PDF files into a single PDF and saves it to the output directory.
    Returns the output file path.
    """
    output_dir = os.path.join(os.getcwd(), 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'merged_{uuid.uuid4().hex}.pdf')
    merger = PdfMerger()
    for file in files:
        file_path = file if isinstance(file, str) else getattr(file, '_path', None)
        if file_path and os.path.exists(file_path):
            merger.append(file_path)
    merger.write(output_path)
    merger.close()
    return output_path
