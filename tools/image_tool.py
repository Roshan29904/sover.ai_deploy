from pathlib import Path
import base64

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from model_routing.model_manager import get_model


@tool
def analyze_image(image_path: str, question: str) -> str:
    """
    Analyze a local image using the local vision-language model.
    Use this for images, diagrams, charts, scanned drawings, and visual documents.
    """
    try:
        path = Path(image_path)

        if not path.exists():
            return f"Image not found: {image_path}"

        if not path.is_file():
            return f"Not a file: {image_path}"

        image_data = base64.b64encode(
            path.read_bytes()
        ).decode("utf-8")

        extension = path.suffix.lower()

        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp"
        }

        mime_type = mime_types.get(extension, "image/png")

        vision_model = get_model("Qwen/Qwen2.5-VL-3B-Instruct")

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": question
                },
                {
                    "type": "image_url",
                    "image_url": f"data:{mime_type};base64,{image_data}"
                }
            ]
        )

        response = vision_model.invoke([message])

        return response.content

    except Exception as e:
        return f"Unable to analyze image: {e}"