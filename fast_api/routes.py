import json
import re
import shutil
import sys
import uuid

from pathlib import Path
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.routing import APIRoute


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent

for path in (BASE_DIR, REPO_DIR):

    path_str = str(path)

    if path_str not in sys.path:
        sys.path.insert(0, path_str)


# ============================================================
# IMPORTS
# ============================================================

try:

    from fast_api.schemas import (
        AgentStateInfo,
        ChatRequest,
        ChatResponse,
    )

except (ImportError, ModuleNotFoundError):

    from schemas import (
        AgentStateInfo,
        ChatRequest,
        ChatResponse,
    )


from orchestration.orchestrator import build_graph


# ============================================================
# DIRECTORIES
# ============================================================

OUTPUTS_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"

OUTPUTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# BUILD GRAPH
# ============================================================

graph = build_graph()


# ============================================================
# LONG-TERM USER MEMORY
# ============================================================

USER_MEMORY_PATH = (
    DATA_DIR / "user_memory.json"
)

USER_MEMORY: Dict[
    str,
    Dict[str, str]
] = {}


def _load_user_memory():

    if not USER_MEMORY_PATH.exists():
        return {}

    try:

        with open(
            USER_MEMORY_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def _save_user_memory():

    try:

        with open(
            USER_MEMORY_PATH,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                USER_MEMORY,
                f,
                indent=2,
                ensure_ascii=False
            )

    except Exception:
        pass


USER_MEMORY = _load_user_memory()


# ============================================================
# THREAD ID
# ============================================================

def _normalize_thread_id(
    value: Optional[str]
) -> str:

    """
    Conversation memory is tied to thread_id.

    The frontend should normally send the same
    thread_id for the same conversation.
    """

    if value is None:
        return "default-user"

    value = str(value).strip()

    if not value:
        return "default-user"

    if value.lower() == "string":
        return "default-user"

    return value


# ============================================================
# NAME MEMORY
# ============================================================

def _normalize_name(
    value: str
) -> str:

    return re.sub(
        r"\s+",
        " ",
        value.strip()
    )


def _remember_user_name(
    thread_id: str,
    query: str
) -> Optional[str]:

    if not thread_id:
        return None

    text = (
        query or ""
    ).strip()

    if not text:
        return None

    # --------------------------------------------------------
    # Handle:
    #
    # I m Roshan
    # i  m  Roshan
    #
    # as:
    #
    # I am Roshan
    # --------------------------------------------------------

    text = re.sub(
        r"\bi\s+m\b",
        "i am",
        text,
        flags=re.IGNORECASE
    )

    patterns = [

        r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z'\-]*)",

        r"\bmy\s+name['’]s\s+([A-Za-z][A-Za-z'\-]*)",

        r"\bi\s+am\s+([A-Za-z][A-Za-z'\-]*)",

        r"\bi['’]m\s+([A-Za-z][A-Za-z'\-]*)",

        r"\bcall\s+me\s+([A-Za-z][A-Za-z'\-]*)",

        r"\byou\s+can\s+call\s+me\s+([A-Za-z][A-Za-z'\-]*)",

        r"\bpeople\s+call\s+me\s+([A-Za-z][A-Za-z'\-]*)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            name = _normalize_name(
                match.group(1)
            )

            if name:

                USER_MEMORY.setdefault(
                    thread_id,
                    {}
                )

                USER_MEMORY[
                    thread_id
                ]["name"] = name

                _save_user_memory()

                return name

    return None


def _get_user_name(
    thread_id: str
) -> Optional[str]:

    return USER_MEMORY.get(
        thread_id,
        {}
    ).get("name")


def _is_name_lookup(
    query: str
) -> bool:

    query = re.sub(
        r"\s+",
        " ",
        (query or "").strip().lower()
    )

    return query in {

        "what is my name",

        "what is my name?",

        "what's my name",

        "what's my name?",

        "whats my name",

        "whats my name?",

        "who am i",

        "who am i?",
    }


# ============================================================
# WINDOWS JSON PATH FIX
# ============================================================

def sanitize_json_string(
    text: str
) -> str:

    if not text:
        return text

    text = re.sub(
        r'"([a-zA-Z]:[\\/][^"\r\n]*)"',
        lambda match:
            '"'
            + match.group(1).replace(
                "\\",
                "/"
            )
            + '"',
        text
    )

    text = re.sub(
        r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})',
        r'\\\\',
        text
    )

    return text


# ============================================================
# CUSTOM ROUTE
# ============================================================

class WindowsPathJsonRoute(APIRoute):

    def get_route_handler(self):

        original_handler = (
            super().get_route_handler()
        )

        async def custom_handler(
            request: Request
        ) -> Response:

            content_type = (
                request.headers.get(
                    "content-type",
                    ""
                )
            )

            if "application/json" in content_type:

                body = await request.body()

                if body:

                    clean_text = (
                        sanitize_json_string(
                            body.decode(
                                "utf-8",
                                errors="replace"
                            )
                        )
                    )

                    clean_bytes = (
                        clean_text.encode(
                            "utf-8"
                        )
                    )

                    async def receive():

                        return {
                            "type":
                                "http.request",

                            "body":
                                clean_bytes,

                            "more_body":
                                False,
                        }

                    request._receive = receive
                    request._body = clean_bytes

            return await original_handler(
                request
            )

        return custom_handler


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(

    prefix="/api",

    tags=[
        "Sovereign AI Workbench"
    ],

    route_class=
        WindowsPathJsonRoute,
)


# ============================================================
# FILE RESOLUTION
# ============================================================

def _resolve_created_files(
    raw_files: List[str]
) -> List[str]:

    resolved = []
    seen: Set[str] = set()

    output_dir = (
        OUTPUTS_DIR.resolve()
    )

    for item in raw_files:

        if not item:
            continue

        clean = (
            str(item)
            .strip()
            .strip("'\"")
        )

        if clean.upper().startswith(
            "DOCUMENT_CREATED:"
        ):

            clean = clean.split(
                ":",
                1
            )[1].strip()

        if not clean:
            continue

        candidate = Path(
            clean
        )

        candidates = [

            candidate,

            OUTPUTS_DIR /
            candidate.name,

            BASE_DIR /
            candidate.name,

            Path.cwd() /
            candidate.name,
        ]

        found = None

        for path in candidates:

            try:

                if (
                    path.exists()
                    and path.is_file()
                ):

                    found = (
                        path.resolve()
                    )

                    break

            except OSError:

                continue

        if found is None:
            continue

        # ----------------------------------------------------
        # Ensure output stays inside outputs/
        # ----------------------------------------------------

        try:

            found.relative_to(
                output_dir
            )

        except ValueError:

            target = (
                OUTPUTS_DIR /
                found.name
            )

            try:

                if target.exists():

                    target = (
                        OUTPUTS_DIR /
                        (
                            f"{target.stem}_"
                            f"{uuid.uuid4().hex[:8]}"
                            f"{target.suffix}"
                        )
                    )

                shutil.move(
                    str(found),
                    str(target)
                )

                found = (
                    target.resolve()
                )

            except Exception:

                continue

        path_string = str(
            found
        )

        if path_string not in seen:

            seen.add(
                path_string
            )

            resolved.append(
                path_string
            )

    return resolved


# ============================================================
# TOOL EXTRACTION
# ============================================================

def _extract_tools_used(
    messages: list
) -> List[str]:

    tools = []

    for message in messages:

        name = getattr(
            message,
            "name",
            None
        )

        if (
            name
            and name not in tools
        ):

            tools.append(
                name
            )

        tool_calls = getattr(
            message,
            "tool_calls",
            None
        )

        if not isinstance(
            tool_calls,
            list
        ):
            continue

        for tool_call in tool_calls:

            if isinstance(
                tool_call,
                dict
            ):

                tool_name = (
                    tool_call.get(
                        "name"
                    )
                )

            else:

                tool_name = getattr(
                    tool_call,
                    "name",
                    None
                )

            if (
                tool_name
                and tool_name not in tools
            ):

                tools.append(
                    tool_name
                )

    return tools


# ============================================================
# CHAT ENDPOINT
# ============================================================

@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat_endpoint(
    payload: ChatRequest
):

    try:

        # ====================================================
        # 1. STABLE THREAD ID
        # ====================================================

        thread_id = (
            _normalize_thread_id(
                payload.thread_id
            )
        )

        # ====================================================
        # 2. REMEMBER LONG-TERM USER INFO
        # ====================================================

        _remember_user_name(
            thread_id,
            payload.query
        )

        # ====================================================
        # 3. NAME LOOKUP
        #
        # This does NOT call the LLM.
        # ====================================================

        if _is_name_lookup(
            payload.query
        ):

            name = _get_user_name(
                thread_id
            )

            if name:

                response = (
                    f"Your name is "
                    f"{name}."
                )

            else:

                response = (
                    "I don't have your "
                    "name saved yet."
                )

            return ChatResponse(

                query=payload.query,

                response=response,

                created_files=[],

                file_directory=None,

                output_directory=
                    str(
                        OUTPUTS_DIR.resolve()
                    ),

                tools_used=[],

                model_role="memory",

                model_name="local-memory",

                verified=True,

                verification_reason=(
                    "Retrieved from "
                    "local persistent memory."
                ),

                thread_id=thread_id,

                agent_state=
                    AgentStateInfo(

                        model_role="memory",

                        model_name=
                            "local-memory",

                        verified=True,

                        verification_reason=(
                            "Retrieved from "
                            "local persistent memory."
                        ),

                        verification_attempts=0,

                        tools_used=[],

                        created_files=[],

                        file_directory=None,

                        output_directory=
                            str(
                                OUTPUTS_DIR.resolve()
                            ),

                        analysis={

                            "task_type":
                                "memory",

                            "needs_rag":
                                False,

                            "needs_vision":
                                False,

                            "needs_tools":
                                False,

                            "output_format":
                                "text",

                            "complexity":
                                "low",
                        },
                    ),
            )

        # ====================================================
        # 4. LANGGRAPH CONFIG
        #
        # THIS IS THE IMPORTANT PART FOR HISTORY.
        # ====================================================

        config = {

            "configurable": {

                "thread_id":
                    thread_id
            }
        }

        # ====================================================
        # 5. FILE PATH
        # ====================================================

        file_path = (

            payload.file_path.strip()

            if payload.file_path

            else ""
        )

        if file_path:

            file_obj = Path(
                file_path
            )

            if not file_obj.is_absolute():

                file_obj = (
                    BASE_DIR /
                    file_obj
                ).resolve()

            else:

                file_obj = (
                    file_obj.resolve()
                )

            if not file_obj.exists():

                raise HTTPException(

                    status_code=400,

                    detail=(
                        "Input file does not "
                        "exist: "
                        f"{file_obj}"
                    )
                )

            if not file_obj.is_file():

                raise HTTPException(

                    status_code=400,

                    detail=(
                        "Input path is not "
                        "a file: "
                        f"{file_obj}"
                    )
                )

            file_path = str(
                file_obj
            )

        # ====================================================
        # 6. SNAPSHOT OUTPUTS
        # ====================================================

        before_outputs = {

            path.resolve()

            for path
            in OUTPUTS_DIR.glob("*")

            if path.is_file()
        }

        # ====================================================
        # 7. IMPORTANT:
        # DO NOT CREATE A NEW THREAD.
        #
        # LangGraph retrieves the previous state
        # automatically from SqliteSaver using
        # this thread_id.
        # ====================================================

        initial_state = {

            "query":
                payload.query,

            "file_path":
                file_path,

            "verification_attempts":
                0,

            "created_files":
                [],

            "messages":
                [],

            "user_id":
                thread_id,
        }

        # ====================================================
        # 8. RUN GRAPH
        # ====================================================

        result = graph.invoke(

            initial_state,

            config=config
        )

        # ====================================================
        # 9. RESPONSE
        # ====================================================

        response = result.get(
            "response",
            "No response generated."
        )

        if not isinstance(
            response,
            str
        ):

            response = str(
                response
            )

        # ====================================================
        # 10. HISTORY RETURNED BY GRAPH
        # ====================================================

        messages = result.get(
            "messages",
            []
        )

        # ====================================================
        # 11. TOOLS
        # ====================================================

        tools_used = (
            _extract_tools_used(
                messages
            )
        )

        # ====================================================
        # 12. CREATED FILES
        # ====================================================

        raw_created = list(
            result.get(
                "created_files",
                []
            )
        )

        # ====================================================
        # 13. NEW OUTPUT FILES
        # ====================================================

        after_outputs = {

            path.resolve()

            for path
            in OUTPUTS_DIR.glob("*")

            if path.is_file()
        }

        new_outputs = [

            str(path)

            for path in (
                after_outputs
                - before_outputs
            )
        ]

        created_files = (
            _resolve_created_files(

                raw_created
                + new_outputs
            )
        )

        # ====================================================
        # 14. ANALYSIS
        # ====================================================

        analysis = result.get(
            "analysis"
        )

        if hasattr(
            analysis,
            "model_dump"
        ):

            analysis = (
                analysis.model_dump()
            )

        elif not isinstance(
            analysis,
            dict
        ):

            analysis = None

        # ====================================================
        # 15. OUTPUT DIRECTORY
        # ====================================================

        output_directory = str(
            OUTPUTS_DIR.resolve()
        )

        file_directory = (

            output_directory

            if created_files

            else None
        )

        # ====================================================
        # 16. AGENT STATE
        # ====================================================

        agent_state = (
            AgentStateInfo(

                model_role=
                    result.get(
                        "model_role"
                    ),

                model_name=
                    result.get(
                        "model_name"
                    ),

                verified=
                    result.get(
                        "verified"
                    ),

                verification_reason=
                    result.get(
                        "verification_reason"
                    ),

                verification_attempts=
                    result.get(
                        "verification_attempts"
                    ),

                tools_used=
                    tools_used,

                created_files=
                    created_files,

                file_directory=
                    file_directory,

                output_directory=
                    output_directory,

                analysis=
                    analysis,
            )
        )

        # ====================================================
        # 17. FINAL RESPONSE
        # ====================================================

        return ChatResponse(

            query=payload.query,

            response=response,

            created_files=
                created_files,

            file_directory=
                file_directory,

            output_directory=
                output_directory,

            tools_used=
                tools_used,

            model_role=
                result.get(
                    "model_role"
                ),

            model_name=
                result.get(
                    "model_name"
                ),

            verified=
                result.get(
                    "verified"
                ),

            verification_reason=
                result.get(
                    "verification_reason"
                ),

            thread_id=
                thread_id,

            agent_state=
                agent_state,
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=(
                "Agent workflow error: "
                f"{exc}"
            )
        )