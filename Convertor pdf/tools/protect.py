import os
import uuid
import pikepdf

def handle_protect(input_path, password: str):
    """
    Protect an uploaded PDF with a password using AES-256 encryption.
    :param input_path: Path to uploaded PDF file
    :param password: string password to encrypt PDF
    :return: path to encrypted PDF
    """
    # Avoid logging the raw password for security reasons
    masked_pw = '*' * len(password) if password else ''
    print(f"[DEBUG] handle_protect: input_path={input_path}, password=<{masked_pw}>")
    OUTPUT_DIR = 'output'
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        if not os.path.exists(input_path):
            raise Exception(f"Input file does not exist: {input_path}")
        if os.path.getsize(input_path) == 0:
            raise Exception(f"Input file is empty: {input_path}")
        output_filename = f'protected_{uuid.uuid4().hex}.pdf'
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with pikepdf.open(input_path) as pdf:
            pdf.save(output_path, encryption=pikepdf.Encryption(owner=password, user=password, R=6))
        print(f"[DEBUG] handle_protect: Output written to {output_path}")
        return output_path
    except Exception as e:
        print(f"[DEBUG] handle_protect: Exception: {e}")
        raise Exception(
            "error||PDF protection failed: "
            + str(e)
            + "\nNote: Some PDFs may use unsupported or proprietary encryption. Only standard password protection (RC4, AES-128, AES-256) is supported. For best results, use PDFs created or saved with common tools like Adobe Acrobat."
        )
