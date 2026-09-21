from pathlib import Path

from langchain_core.tools import tool


@tool
def read_text_file(file_path: str) -> str:
    """Read and return the contents of a local text file."""

    try:
        path = Path(file_path)

        if not path.exists():
            return f"File not found: {file_path}"

        if not path.is_file():
            return f"Not a file: {file_path}"

        return path.read_text(encoding="utf-8")

    except Exception as e:
        return f"Unable to read file: {e}"