from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from PIL import Image
import io, os, uuid, glob
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register all TTF fonts in static/fonts and subfolders
font_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts')
ttf_files = glob.glob(os.path.join(font_dir, '**', '*.ttf'), recursive=True)
REGISTERED_FONTS = []
for ttf_path in ttf_files:
    font_name = os.path.splitext(os.path.basename(ttf_path))[0]
    try:
        pdfmetrics.registerFont(TTFont(font_name, ttf_path))
        REGISTERED_FONTS.append(font_name)
    except Exception:
        pass

def create_text_watermark_pdf(text, font, color, opacity, page_size, angle=-45):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=page_size)
    # Use only registered fonts
    if font not in REGISTERED_FONTS:
        font = "Helvetica"
    try:
        can.setFont(font, 40)
    except Exception:
        can.setFont("Helvetica", 40)
        font = "Helvetica"
    can.setFillColor(HexColor(color), alpha=float(opacity))
    width, height = page_size
    can.saveState()
    # Move to center, rotate, then draw text
    can.translate(width/2, height/2)
    can.rotate(angle)
    can.drawCentredString(0, 0, text)
    can.restoreState()
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def create_image_watermark_pdf(image_bytes, opacity, position, page_size, img_scale=0.3):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = page_size

    # Resize watermark to be about img_scale of page width
    img_ratio = image.width / image.height
    target_width = width * img_scale
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
    can = canvas.Canvas(packet, pagesize=page_size)
    can.drawImage(ImageReader(img_io), pos_x, pos_y, width=image.width, height=image.height, mask='auto')
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def handle_watermark(file, watermark_text=None, image=None, font="Helvetica", color="#000000", opacity=0.3, img_position="center", img_scale=0.3, angle=-45):
    try:
        reader = PdfReader(file)
        writer = PdfWriter()

        for page in reader.pages:
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            page_size = (page_width, page_height)
            watermark_pdf = None
            if watermark_text:
                watermark_pdf = create_text_watermark_pdf(watermark_text, font, color, opacity, page_size, angle)
            elif image:
                image_bytes = image.read()
                if not image_bytes:
                    raise Exception("error||No image data provided for watermark.")
                watermark_pdf = create_image_watermark_pdf(image_bytes, opacity, img_position, page_size, img_scale)
            else:
                raise Exception("error||No watermark text or image provided.")

            if not watermark_pdf.pages:
                raise Exception("error||Watermark PDF has no pages.")

            page.merge_page(watermark_pdf.pages[0])
            writer.add_page(page)

        output_path = os.path.join("output", f"watermarked_{uuid.uuid4().hex}.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        return output_path

    except Exception as e:
        raise Exception(f"error||Watermarking failed: {str(e)}")
