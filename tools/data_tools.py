from pathlib import Path

import pandas as pd
from langchain_core.tools import tool


@tool
def analyze_dataset(file_path: str, operation: str) -> str:
    """
    Analyze a local CSV or Excel dataset.

    operation describes what analysis the user wants,
    such as 'show columns', 'summary statistics',
    'number of rows', or 'missing values'.
    """

    try:
        path = Path(file_path)

        if not path.exists():
            return f"File not found: {file_path}"

        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)

        elif path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(path)

        else:
            return "Unsupported file type. Use CSV or Excel."

        operation = operation.lower()

        if "column" in operation:
            return f"Columns:\n{list(df.columns)}"

        if "row" in operation:
            return f"Number of rows: {len(df)}"

        if "missing" in operation:
            return df.isnull().sum().to_string()

        if "summary" in operation or "statistics" in operation:
            return df.describe(include="all").to_string()

        return (
            f"Dataset shape: {df.shape}\n\n"
            f"Columns: {list(df.columns)}"
        )

    except Exception as e:
        return f"Unable to analyze dataset: {e}"