import json
import re
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = (
    BASE_DIR
    / "prompts"
    / "query_analyzer.txt"
)


# ============================================================
# QUERY ANALYSIS SCHEMA
# ============================================================

class QueryAnalysis(BaseModel):

    task_type: str = Field(
        description="Type of task the user wants to perform"
    )

    needs_rag: bool = Field(
        description="Whether organizational documents or knowledge base are needed"
    )

    needs_vision: bool = Field(
        description="Whether images or scanned documents need to be understood"
    )

    needs_tools: bool = Field(
        description="Whether local tools are needed"
    )

    output_format: str = Field(
        description="Expected output format"
    )

    complexity: str = Field(
        description="Task complexity: low, medium, or high"
    )


# ============================================================
# DEFAULT ANALYSIS
# ============================================================

DEFAULT_ANALYSIS = QueryAnalysis(
    task_type="other",
    needs_rag=False,
    needs_vision=False,
    needs_tools=False,
    output_format="text",
    complexity="low",
)


# ============================================================
# HUGGING FACE MODEL
# ============================================================

llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-3B-Instruct",
    temperature=0,
    max_new_tokens=512,
)

chat_llm = ChatHuggingFace(
    llm=llm
)


# ============================================================
# LOAD PROMPT
# ============================================================

def load_prompt():
    """
    Load the query analyzer prompt.
    """

    with open(
        PROMPT_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


# ============================================================
# EXTRACT JSON
# ============================================================

def _extract_json_object(text):
    """
    Extract the first JSON object from model output.

    Handles:
    - Plain JSON
    - ```json ... ```
    - Extra text around JSON
    - Python-style single quoted dictionaries
    """

    if text is None:
        return {}

    if isinstance(text, dict):
        return text

    if hasattr(text, "model_dump"):
        return _extract_json_object(
            text.model_dump()
        )

    if not isinstance(text, str):
        return {}

    cleaned = text.strip()

    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    cleaned = cleaned.strip()

    # --------------------------------------------------------
    # Try direct JSON parsing
    # --------------------------------------------------------

    try:

        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except (json.JSONDecodeError, TypeError):
        pass

    # --------------------------------------------------------
    # Find JSON object inside surrounding text
    # --------------------------------------------------------

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end > start:

        candidate = cleaned[start:end + 1]

        try:

            parsed = json.loads(candidate)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Try Python-style dictionary
    # --------------------------------------------------------

    try:

        candidate = cleaned[start:end + 1]

        candidate = candidate.replace(
            "'",
            '"'
        )

        parsed = json.loads(candidate)

        if isinstance(parsed, dict):
            return parsed

    except Exception:
        pass

    return {}


# ============================================================
# NORMALIZE ANALYSIS
# ============================================================

def _normalize_analysis_dict(raw_response):
    """
    Normalize malformed LLM output.

    Examples:

        "1. task_type" -> "task_type"

        "needs_rag": "yes" -> True

        "Complexity": "HIGH" -> "high"
    """

    response = _extract_json_object(
        raw_response
    )

    if not isinstance(response, dict):
        return {}

    normalized = {}

    # --------------------------------------------------------
    # Normalize keys
    # --------------------------------------------------------

    for key, value in response.items():

        clean_key = str(key).strip()

        # Remove numbering such as:
        # 1.
        # 2-
        # 3_
        clean_key = re.sub(
            r"^[\d\s._-]+",
            "",
            clean_key
        )

        clean_key = clean_key.replace(
            " ",
            "_"
        )

        clean_key = clean_key.strip(
            "_"
        )

        clean_key = clean_key.strip(
            "\"'"
        )

        clean_key = clean_key.lower()

        if clean_key:
            normalized[clean_key] = value

    # --------------------------------------------------------
    # Normalize boolean fields
    # --------------------------------------------------------

    boolean_fields = (
        "needs_rag",
        "needs_vision",
        "needs_tools",
    )

    for field in boolean_fields:

        if field not in normalized:
            continue

        value = normalized[field]

        if isinstance(value, str):

            normalized[field] = (
                value.strip().lower()
                in {
                    "true",
                    "yes",
                    "y",
                    "1"
                }
            )

        else:

            normalized[field] = bool(value)

    # --------------------------------------------------------
    # Normalize string fields
    # --------------------------------------------------------

    string_fields = (
        "task_type",
        "output_format",
        "complexity",
    )

    for field in string_fields:

        if field in normalized:

            normalized[field] = str(
                normalized[field]
            ).strip().lower()

    # --------------------------------------------------------
    # Defaults
    # --------------------------------------------------------

    defaults = {
        "task_type": "other",
        "needs_rag": False,
        "needs_vision": False,
        "needs_tools": False,
        "output_format": "text",
        "complexity": "low",
    }

    for key, value in defaults.items():

        normalized.setdefault(
            key,
            value
        )

    return normalized


# ============================================================
# COERCE PAYLOAD
# ============================================================

def _coerce_analysis_payload(value):
    """
    Convert different response types into a clean dictionary.
    """

    if value is None:
        return {}

    # Already a dictionary
    if isinstance(value, dict):

        cleaned = {}

        for key, item in value.items():

            clean_key = (
                str(key)
                .strip()
                .strip("\"'")
                .lower()
            )

            if clean_key:
                cleaned[clean_key] = item

        return cleaned

    # String containing JSON
    if isinstance(value, str):

        extracted = _extract_json_object(
            value
        )

        if isinstance(extracted, dict):
            return _coerce_analysis_payload(
                extracted
            )

    # Pydantic model
    if hasattr(value, "model_dump"):

        return _coerce_analysis_payload(
            value.model_dump()
        )

    return {}


# ============================================================
# ANALYZE QUERY
# ============================================================

def analyze_query(query):
    """
    Analyze the user's query and return QueryAnalysis.
    """

    prompt = load_prompt()

    final_prompt = f"""
{prompt}

User query:
{query}

Return ONLY valid JSON.

Do not use markdown.
Do not explain anything.
Do not add extra text.

Required JSON format:

{{
    "task_type": "string",
    "needs_rag": true,
    "needs_vision": false,
    "needs_tools": false,
    "output_format": "text",
    "complexity": "low"
}}
"""

    # --------------------------------------------------------
    # Try twice in case the model returns malformed JSON
    # --------------------------------------------------------

    prompts = [
        final_prompt,

        final_prompt + """

IMPORTANT:
Return exactly one JSON object.
Use double quotes around all keys and string values.
Boolean values must be true or false.
"""
    ]

    for attempt_prompt in prompts:

        try:

            response = chat_llm.invoke(
                attempt_prompt
            )

            content = getattr(
                response,
                "content",
                response
            )

            normalized = _normalize_analysis_dict(
                content
            )

            normalized = _coerce_analysis_payload(
                normalized
            )

            if not normalized:
                continue

            return QueryAnalysis.model_validate(
                {
                    "task_type": normalized.get(
                        "task_type",
                        "other"
                    ),

                    "needs_rag": normalized.get(
                        "needs_rag",
                        False
                    ),

                    "needs_vision": normalized.get(
                        "needs_vision",
                        False
                    ),

                    "needs_tools": normalized.get(
                        "needs_tools",
                        False
                    ),

                    "output_format": normalized.get(
                        "output_format",
                        "text"
                    ),

                    "complexity": normalized.get(
                        "complexity",
                        "low"
                    ),
                }
            )

        except Exception:
            continue

    # --------------------------------------------------------
    # Safe fallback
    # --------------------------------------------------------

    return DEFAULT_ANALYSIS