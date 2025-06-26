import os
import uuid
from PIL import Image

def handle_jpg_to_pdf(files):
    """
    Convert a list of uploaded JPG images to a single PDF.
    :param files: list of FileStorage objects from Flask (images)
    :return: path to generated PDF
    """
    # Ensure directories
    UPLOAD_DIR = 'uploads'
    OUTPUT_DIR = 'output'
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    image_paths = []
    # Save uploaded images
    for f in files:
        filename = f.filename
        path = os.path.join(UPLOAD_DIR, filename)
        f.save(path)
        image_paths.append(path)

    if not image_paths:
        raise ValueError("No images provided for conversion.")

    # Open images and convert to RGB
    pil_images = []
    for img_path in image_paths:
        img = Image.open(img_path)
        # Ensure image is in RGB mode
        if img.mode in ("RGBA", "LA"):
            img = img.convert("RGB")
        elif img.mode == "P":
            img = img.convert("RGB")
        pil_images.append(img)

    # Define output PDF path
    output_filename = f"jpg_to_pdf_{uuid.uuid4().hex}.pdf"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Save first image and append the rest
    first_image, rest_images = pil_images[0], pil_images[1:]
    first_image.save(
        output_path,
        "PDF",
        resolution=100.0,
        save_all=True,
        append_images=rest_images
    )

    # Cleanup uploaded image files
    for path in image_paths:
        try:
            os.remove(path)
        except OSError:
            pass

    return output_path
