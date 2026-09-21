from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from langchain_core.tools import tool


@tool
def create_pdf(title: str, content: str, output_path: str) -> str:
    """
    Create a PDF document locally with a title and text content.
    """

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        document = SimpleDocTemplate(
            str(path),
            pagesize=A4
        )

        styles = getSampleStyleSheet()

        elements = []

        elements.append(
            Paragraph(title, styles["Title"])
        )

        elements.append(Spacer(1, 20))

        for paragraph in content.split("\n"):
            if paragraph.strip():
                elements.append(
                    Paragraph(
                        paragraph.strip(),
                        styles["BodyText"]
                    )
                )
                elements.append(Spacer(1, 10))

        document.build(elements)

        return f"DOCUMENT_CREATED:{path.resolve()}"

    except Exception as e:
        return f"Unable to create PDF: {e}"