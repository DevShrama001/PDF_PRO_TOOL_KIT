from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from PIL import Image
import io, os, uuid

def create_text_watermark_pdf(text, font, color, opacity):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont(font, 40)
    can.setFillColor(HexColor(color), alpha=float(opacity))
    width, height = letter
    can.drawCentredString(width / 2, height / 2, text)
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def create_image_watermark_pdf(image_bytes, opacity, position):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = letter

    # Resize watermark to be about 30% of page width
    img_ratio = image.width / image.height
    target_width = width * 0.3
    image = image.resize((int(target_width), int(target_width / img_ratio)))

    # Apply opacity
    alpha = image.split()[3].point(lambda p: int(p * float(opacity)))
    image.putalpha(alpha)

    img_io = io.BytesIO()
    image.save(img_io, format='PNG')
    img_io.seek(0)

    pos_x, pos_y = {
        "top-left": (50, height - image.height - 50),
        "top-right": (width - image.width - 50, height - image.height - 50),
        "bottom-left": (50, 50),
        "bottom-right": (width - image.width - 50, 50),
        "center": ((width - image.width) / 2, (height - image.height) / 2)
    }.get(position, ((width - image.width) / 2, (height - image.height) / 2))

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.drawImage(img_io, pos_x, pos_y, width=image.width, height=image.height, mask='auto')
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def handle_watermark(file, watermark_text=None, image=None, font="Helvetica", color="#000000", opacity=0.3, img_position="center"):
    try:
        reader = PdfReader(file)
        writer = PdfWriter()

        watermark_pdf = None
        if watermark_text:
            watermark_pdf = create_text_watermark_pdf(watermark_text, font, color, opacity)
        elif image:
            watermark_pdf = create_image_watermark_pdf(image.read(), opacity, img_position)
        else:
            raise Exception("error||No watermark text or image provided.")

        if not watermark_pdf.pages:
            raise Exception("error||Watermark PDF has no pages.")

        for page in reader.pages:
            page.merge_page(watermark_pdf.pages[0])
            writer.add_page(page)

        output_path = os.path.join("output", f"watermarked_{uuid.uuid4().hex}.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        return output_path

    except Exception as e:
        raise Exception(f"error||Watermarking failed: {str(e)}")
