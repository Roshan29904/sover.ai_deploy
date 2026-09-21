from pathlib import Path

from openpyxl import Workbook
from langchain_core.tools import tool


@tool
def create_excel(title: str, content: str, output_path: str) -> str:
    """
    Create an Excel workbook from the provided content.

    Content should contain one row per line, with columns separated by '|'.
    Example:
    Month | Sales
    January | 50000
    February | 62000
    March | 71000
    """

    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Report"

        sheet["A1"] = title

        rows = content.strip().split("\n")

        for row_number, row in enumerate(rows, start=2):

            columns = [value.strip() for value in row.split("|")]

            for column_number, value in enumerate(columns, start=1):
                sheet.cell(
                    row=row_number,
                    column=column_number,
                    value=value
                )

        workbook.save(path)

        return f"DOCUMENT_CREATED:{path.resolve()}"

    except Exception as e:
        return f"Unable to create Excel file: {e}"