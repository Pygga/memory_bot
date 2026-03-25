from PIL import Image

_processor = None
_model = None


def describe_image(file_path: str) -> str:
    global _processor, _model
    if _model is None:
        from transformers import BlipForConditionalGeneration, BlipProcessor
        _processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    image = Image.open(file_path).convert("RGB")
    inputs = _processor(image, return_tensors="pt")
    output = _model.generate(**inputs, max_new_tokens=64)
    return _processor.decode(output[0], skip_special_tokens=True)
