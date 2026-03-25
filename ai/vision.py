import pytesseract
from PIL import Image


def describe_image(file_path: str) -> str:
    image = Image.open(file_path).convert("RGB")
    text = pytesseract.image_to_string(image, lang="rus+eng").strip()
    return text if text else "фото без текста"
