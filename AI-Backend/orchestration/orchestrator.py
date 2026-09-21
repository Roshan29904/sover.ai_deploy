from typing import TypedDict, Annotated, NotRequired
from pathlib import Path
import sqlite3

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from query_analysis.query_analyzer import (
    QueryAnalysis,
    analyze_query,
)

from model_routing.model_router import route_model
from model_routing.model_config import MODEL_CONFIG
from model_routing.model_manager import get_model

from agents.agent import build_agent
from tools.image_tool import analyze_image
from verification.verifier import verify_response


# ============================================================
# STATE
# ============================================================

class AgentState(TypedDict):

    # Current user query
    query: str

    # Optional local file
    file_path: NotRequired[str]

    # User identifier
    user_id: NotRequired[str]

    # Query analysis
    analysis: NotRequired[dict]

    # Selected model
    model_role: NotRequired[str]
    model_name: NotRequired[str]

    # Final response
    response: NotRequired[str]

    # Verification
    verified: NotRequired[bool]
    verification_reason: NotRequired[str]
    verification_attempts: NotRequired[int]

    # IMPORTANT:
    # LangGraph will append new messages to this list.
    #
    # SQLite checkpointer persists this state using
    # thread_id.
    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]

    # Files created by tools
    created_files: NotRequired[list[str]]


# ============================================================
# ANALYSIS NORMALIZATION
# ============================================================

def _normalize_analysis_dict(raw):

    if raw is None:
        return {}

    # Pydantic v2
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()

    # Pydantic v1
    elif hasattr(raw, "dict"):
        raw = raw.dict()

    if not isinstance(raw, dict):
        return {}

    normalized = {}

    for key, value in raw.items():

        clean_key = (
            str(key)
            .strip()
            .strip("\"'")
            .replace(" ", "_")
            .lower()
        )

        if clean_key:
            normalized[clean_key] = value

    return normalized


# ============================================================
# ANALYSIS NODE
# ============================================================

def analysis_node(state: AgentState):

    query = state["query"]

    # --------------------------------------------------------
    # Analyze only the current request.
    #
    # The actual conversation history will be given to the
    # agent later.
    # --------------------------------------------------------

    analysis = analyze_query(query)

    if isinstance(analysis, dict):

        analysis = QueryAnalysis.model_validate(
            _normalize_analysis_dict(analysis)
        )

    return {
        "analysis": analysis.model_dump()
    }


# ============================================================
# MODEL ROUTING NODE
# ============================================================

def routing_node(state: AgentState):

    analysis = state.get(
        "analysis",
        {}
    )

    model_role = route_model(
        analysis
    )

    model_name = MODEL_CONFIG.get(
        model_role
    )

    if not model_name:

        raise ValueError(
            f"No model configured for role: "
            f"{model_role}"
        )

    return {

        "model_role":
            model_role,

        "model_name":
            model_name,
    }


# ============================================================
# BUILD USER MESSAGE
# ============================================================

def _build_user_message(
    state: AgentState
):

    query = state["query"]

    file_path = (
        state.get("file_path")
    )

    # --------------------------------------------------------
    # Normal query
    # --------------------------------------------------------

    if not file_path:

        return HumanMessage(
            content=query
        )

    # --------------------------------------------------------
    # Query with local file
    # --------------------------------------------------------

    content = f"""
User task:

{query}

A local file has been attached:

{file_path}

The file is available locally.

Use the appropriate available local tool to inspect
or process the file.

Do not assume the file contents without reading it.
"""

    return HumanMessage(
        content=content
    )


# ============================================================
# EXTRACT CREATED FILES
# ============================================================

def _extract_created_files(
    messages
):

    created_files = []

    for message in messages:

        # ----------------------------------------------------
        # Tool message
        # ----------------------------------------------------

        if isinstance(
            message,
            ToolMessage
        ):

            content = message.content

            if not isinstance(
                content,
                str
            ):
                continue

            if content.startswith(
                "DOCUMENT_CREATED:"
            ):

                path = content.split(
                    ":",
                    1
                )[1].strip()

                if path:

                    created_files.append(
                        path
                    )

    return created_files


# ============================================================
# REMOVE DUPLICATE FILES
# ============================================================

def _unique_files(
    files
):

    result = []

    seen = set()

    for file in files:

        if not file:
            continue

        file = str(file)

        if file not in seen:

            seen.add(file)

            result.append(file)

    return result


# ============================================================
# MAIN AGENT NODE
# ============================================================

def model_node(
    state: AgentState
):

    model_name = state[
        "model_name"
    ]

    # --------------------------------------------------------
    # Build agent with selected LOCAL model
    # --------------------------------------------------------

    agent = build_agent(
        model_name
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # state["messages"] already contains the previous
    # conversation because LangGraph restored it from SQLite.
    #
    # We only append the NEW user message.
    # --------------------------------------------------------

    user_message = _build_user_message(
        state
    )

    messages = list(
        state.get(
            "messages",
            []
        )
    )

    messages.append(
        user_message
    )

    # --------------------------------------------------------
    # Invoke agent WITH conversation history
    # --------------------------------------------------------

    result = agent.invoke(
        {
            "messages": messages
        }
    )

    result_messages = result.get(
        "messages",
        []
    )

    if not result_messages:

        raise RuntimeError(
            "Agent returned no messages."
        )

    # --------------------------------------------------------
    # Find final AI response
    # --------------------------------------------------------

    response = None

    for message in reversed(
        result_messages
    ):

        if isinstance(
            message,
            AIMessage
        ):

            if isinstance(
                message.content,
                str
            ):

                response = (
                    message.content
                )

                break

    # Fallback
    if response is None:

        last_message = (
            result_messages[-1]
        )

        response = str(
            getattr(
                last_message,
                "content",
                last_message
            )
        )

    # --------------------------------------------------------
    # Extract created files
    # --------------------------------------------------------

    created_files = list(
        state.get(
            "created_files",
            []
        )
    )

    created_files.extend(
        _extract_created_files(
            result_messages
        )
    )

    created_files = _unique_files(
        created_files
    )

    # --------------------------------------------------------
    # Return ALL new messages.
    #
    # add_messages will merge them into the existing state.
    # --------------------------------------------------------

    return {

        "messages":
            result_messages,

        "response":
            response,

        "created_files":
            created_files,
    }


# ============================================================
# VISION NODE
# ============================================================

def vision_node(
    state: AgentState
):

    file_path = state.get(
        "file_path"
    )

    if not file_path:

        response = (
            "No image file was provided."
        )

        return {

            "messages": [
                AIMessage(
                    content=response
                )
            ],

            "response":
                response,
        }

    # --------------------------------------------------------
    # Local vision tool
    # --------------------------------------------------------

    result = analyze_image.invoke(
        {
            "image_path":
                file_path,

            "question":
                state["query"],
        }
    )

    response = str(
        result
    )

    return {

        "messages": [
            AIMessage(
                content=response
            )
        ],

        "response":
            response,
    }


# ============================================================
# VERIFICATION NODE
# ============================================================

def verification_node(
    state: AgentState
):

    verification_model_name = (
        MODEL_CONFIG[
            "verification_model"
        ]
    )

    # --------------------------------------------------------
    # Local verification model
    # --------------------------------------------------------

    llm = get_model(
        verification_model_name
    )

    result = verify_response(

        llm,

        state["query"],

        state["response"]
    )

    attempts = (
        state.get(
            "verification_attempts",
            0
        )
        + 1
    )

    return {

        "verified":
            bool(
                result.get(
                    "verified",
                    False
                )
            ),

        "verification_reason":
            result.get(
                "reason",
                ""
            ),

        "verification_attempts":
            attempts,
    }


# ============================================================
# REGENERATION NODE
# ============================================================

def regeneration_node(
    state: AgentState
):

    agent = build_agent(
        state["model_name"]
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Regeneration also gets the COMPLETE conversation
    # history.
    # --------------------------------------------------------

    history = list(
        state.get(
            "messages",
            []
        )
    )

    correction_prompt = f"""
The previous response did not pass verification.

User's current request:

{state["query"]}

Previous response:

{state["response"]}

Verifier feedback:

{state.get(
    "verification_reason",
    ""
)}

Generate a corrected response.

Use the previous conversation context when necessary.

Do not mention the verification process to the user.
"""

    history.append(
        HumanMessage(
            content=correction_prompt
        )
    )

    result = agent.invoke(
        {
            "messages":
                history
        }
    )

    result_messages = result.get(
        "messages",
        []
    )

    if not result_messages:

        raise RuntimeError(
            "Regeneration agent returned no messages."
        )

    # --------------------------------------------------------
    # Find final AI response
    # --------------------------------------------------------

    response = None

    for message in reversed(
        result_messages
    ):

        if isinstance(
            message,
            AIMessage
        ):

            if isinstance(
                message.content,
                str
            ):

                response = (
                    message.content
                )

                break

    if response is None:

        response = str(
            result_messages[-1].content
        )

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    created_files = list(
        state.get(
            "created_files",
            []
        )
    )

    created_files.extend(
        _extract_created_files(
            result_messages
        )
    )

    created_files = _unique_files(
        created_files
    )

    # --------------------------------------------------------
    # We store the new AI response in state.
    # --------------------------------------------------------

    return {

        "messages":
            result_messages,

        "response":
            response,

        "created_files":
            created_files,
    }


# ============================================================
# MODEL SELECTION
# ============================================================

def choose_model(
    state: AgentState
):

    if (
        state.get(
            "model_role"
        )
        == "vision_model"
    ):

        return "vision"

    return "generate"


# ============================================================
# VERIFICATION ROUTER
# ============================================================

def verification_router(
    state: AgentState
):

    # --------------------------------------------------------
    # Verification successful
    # --------------------------------------------------------

    if state.get(
        "verified",
        False
    ):

        return "finish"

    # --------------------------------------------------------
    # Maximum attempts reached
    # --------------------------------------------------------

    if (
        state.get(
            "verification_attempts",
            0
        )
        >= 2
    ):

        return "finish"

    # --------------------------------------------------------
    # Vision regeneration disabled for now
    # --------------------------------------------------------

    if (
        state.get(
            "model_role"
        )
        == "vision_model"
    ):

        return "finish"

    return "regenerate"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph():

    graph = StateGraph(
        AgentState
    )

    # ========================================================
    # NODES
    # ========================================================

    graph.add_node(
        "analyze",
        analysis_node
    )

    graph.add_node(
        "route",
        routing_node
    )

    graph.add_node(
        "generate",
        model_node
    )

    graph.add_node(
        "vision",
        vision_node
    )

    graph.add_node(
        "verify",
        verification_node
    )

    graph.add_node(
        "regenerate",
        regeneration_node
    )

    # ========================================================
    # START
    # ========================================================

    graph.set_entry_point(
        "analyze"
    )

    # ========================================================
    # ANALYZE → ROUTE
    # ========================================================

    graph.add_edge(
        "analyze",
        "route"
    )

    # ========================================================
    # ROUTE → MODEL
    # ========================================================

    graph.add_conditional_edges(

        "route",

        choose_model,

        {

            "generate":
                "generate",

            "vision":
                "vision",
        }
    )

    # ========================================================
    # MODEL → VERIFY
    # ========================================================

    graph.add_edge(
        "generate",
        "verify"
    )

    graph.add_edge(
        "vision",
        "verify"
    )

    # ========================================================
    # REGENERATE → VERIFY
    # ========================================================

    graph.add_edge(
        "regenerate",
        "verify"
    )

    # ========================================================
    # VERIFY → FINISH / REGENERATE
    # ========================================================

    graph.add_conditional_edges(

        "verify",

        verification_router,

        {

            "finish":
                END,

            "regenerate":
                "regenerate",
        }
    )

    # ========================================================
    # SQLITE CHECKPOINTER
    # ========================================================

    db_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "checkpoints.db"
    )

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(

        str(db_path),

        check_same_thread=False
    )

    checkpointer = SqliteSaver(
        connection
    )

    # ========================================================
    # COMPILE
    # ========================================================

    return graph.compile(
        checkpointer=checkpointer
    )