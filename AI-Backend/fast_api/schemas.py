from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# CHAT REQUEST
# ============================================================

class ChatRequest(BaseModel):

    query: str = Field(
        ...,
        description="User query or task instructions."
    )

    file_path: Optional[str] = Field(
        default="",
        description="Optional path to an input document or image."
    )

    thread_id: Optional[str] = Field(
        default=None,
        description="Conversation session ID for memory persistence. A new ID is generated when omitted."
    )


# ============================================================
# AGENT STATE INFO
# ============================================================

class AgentStateInfo(BaseModel):

    model_role: Optional[str] = None

    model_name: Optional[str] = None

    verified: Optional[bool] = None

    verification_reason: Optional[str] = None

    verification_attempts: Optional[int] = None

    tools_used: List[str] = Field(
        default_factory=list
    )

    created_files: List[str] = Field(
        default_factory=list
    )

    file_directory: Optional[str] = None

    output_directory: Optional[str] = None

    analysis: Optional[Dict[str, Any]] = None


# ============================================================
# CHAT RESPONSE
# ============================================================

class ChatResponse(BaseModel):

    query: str

    response: str

    created_files: List[str] = Field(
        default_factory=list,
        description="Full disk paths of files created by the model."
    )

    file_directory: Optional[str] = Field(
        default=None,
        description="Directory where created files are stored."
    )

    output_directory: Optional[str] = Field(
        default=None,
        description="Canonical output directory path."
    )

    tools_used: List[str] = Field(
        default_factory=list
    )

    model_role: Optional[str] = None

    model_name: Optional[str] = None

    verified: Optional[bool] = None

    verification_reason: Optional[str] = None

    thread_id: str

    agent_state: Optional[AgentStateInfo] = None