def _normalize_analysis_mapping(raw):
    """
    Normalize the task analysis output into a clean dictionary.
    Supports both normal dicts and Pydantic-style objects.
    """

    if raw is None:
        return {}

    # Pydantic v2
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()

    # Pydantic v1 fallback
    elif hasattr(raw, "dict"):
        raw = raw.dict()

    if not isinstance(raw, dict):
        return {}

    normalized = {}

    for key, value in raw.items():
        clean_key = str(key).strip().strip("\"'")
        clean_key = clean_key.replace(" ", "_").lower()

        if clean_key:
            normalized[clean_key] = value

    return normalized


def route_model(analysis):
    """
    Select the model based on task analysis.

    Returns one of:
        - general_model
        - coding_model
        - reasoning_model
        - vision_model
    """

    payload = _normalize_analysis_mapping(analysis)

    task_type = str(
        payload.get("task_type", "other")
    ).strip().strip("\"'").lower()

    complexity = str(
        payload.get("complexity", "low")
    ).strip().strip("\"'").lower()

    needs_vision = payload.get("needs_vision", False)

    # Handle string values such as "true", "yes", "1"
    if isinstance(needs_vision, str):
        needs_vision = needs_vision.strip().lower() in {
            "true",
            "yes",
            "y",
            "1"
        }
    else:
        needs_vision = bool(needs_vision)

    # 1. Vision has highest priority
    if needs_vision:
        return "vision_model"

    # 2. Coding tasks
    if task_type == "coding":
        return "coding_model"

    # 3. Complex reasoning tasks
    if complexity == "high":
        return "reasoning_model"

    # 4. Default
    return "general_model"