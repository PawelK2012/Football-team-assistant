import asyncio
import logging
import os
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import AsyncClient
from starlette.exceptions import HTTPException

from football_team_assistant.football_agent import FootballAgent
from football_team_assistant.mcp_client import to_ollama_tool
from football_team_assistant.web_chat.conversations import ChatError, Conversations

HOST = "127.0.0.1:8001"
ORIGIN = f"http://{HOST}"
STATIC = Path(__file__).resolve().parent / "static"
logger = logging.getLogger(__name__)

ERRORS = {
    "invalid_request": (400, "Enter a valid message and try again."),
    "access_denied": (403, "Open the chat on the computer running the agent."),
    "conversation_missing": (404, "The previous fixture context was lost. Start fresh to resend."),
    "turn_pending": (409, "A reply is still pending. Try again once it finishes."),
    "unsupported_content_type": (415, "Send the message as JSON."),
    "agent_unavailable": (503, "The football agent is unavailable. Try again."),
    "runtime_unavailable": (
        503,
        "The football agent could not connect to its tools. "
        "Check the setup and restart the chat service.",
    ),
    "turn_timeout": (504, "The football agent took too long to reply. Try again."),
}

AgentFactory = Callable[[], FootballAgent]
Runtime = Callable[[], AbstractAsyncContextManager[AgentFactory | None]]


def error_response(code: str) -> JSONResponse:
    status, message = ERRORS[code]
    public_code = "agent_unavailable" if code == "runtime_unavailable" else code
    return JSONResponse({"error": {"code": public_code, "message": message}}, status_code=status)


@asynccontextmanager
async def open_runtime(timeout: float) -> AsyncIterator[AgentFactory | None]:
    async with AsyncExitStack() as stack:
        try:
            ollama = await stack.enter_async_context(AsyncClient())
            env = (
                {"DATABASE_URL": os.environ["DATABASE_URL"]}
                if "DATABASE_URL" in os.environ
                else None
            )
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "football_team_assistant.mcp_server.server"],
                env=env,
            )
            stderr = stack.enter_context(open(os.devnull, "w"))
            read, write = await stack.enter_async_context(stdio_client(parameters, errlog=stderr))
            session = await stack.enter_async_context(ClientSession(read, write))
            async with asyncio.timeout(timeout):
                await session.initialize()
                discovered = await session.list_tools()
            tools = [to_ollama_tool(tool) for tool in discovered.tools]
        except Exception:
            # Keep the UI up after startup failures and avoid logging upstream details.
            logger.warning("Football chat could not initialize its agent runtime.")
            await stack.aclose()
            yield None
            return

        def make_agent() -> FootballAgent:
            return FootballAgent(ollama=ollama, mcp_session=session, tools=tools)

        yield make_agent


async def read_turn(request: Request) -> tuple[str, str]:
    content_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
    if content_type != "application/json":
        raise ChatError("unsupported_content_type")
    try:
        data = await request.json()
        if not isinstance(data, dict) or set(data) != {"request_id", "message"}:
            raise ValueError
        request_id = data["request_id"]
        message = data["message"]
        if not isinstance(request_id, str) or not isinstance(message, str):
            raise ValueError
        request_id = str(UUID(request_id))
        if not (message := message.strip()):
            raise ValueError
    except ValueError:
        raise ChatError("invalid_request") from None
    return request_id, message


def create_app(
    *,
    runtime: Runtime | None = None,
    startup_timeout: float = 10.0,
    turn_timeout: float = 90.0,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with runtime() if runtime is not None else open_runtime(startup_timeout) as factory:
            conversations = Conversations(factory, turn_timeout)
            app.state.conversations = conversations
            try:
                yield
            finally:
                await conversations.close()

    app = FastAPI(
        title="Football Agent Web Chat",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )

    @app.middleware("http")
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if (
            request.client is None
            or request.client.host != "127.0.0.1"
            or request.headers.getlist("host") != [HOST]
            or (
                request.method in {"POST", "DELETE"}
                and request.headers.getlist("origin") != [ORIGIN]
            )
        ):
            response = error_response("access_denied")
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ChatError)
    async def handle_chat_error(request: Request, error: ChatError) -> JSONResponse:
        return error_response(error.code)

    @app.exception_handler(HTTPException)
    async def handle_route_error(request: Request, error: HTTPException) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": "invalid_request", "message": "This chat request is unavailable."}},
            status_code=error.status_code,
        )

    @app.get("/chat")
    async def page() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/chat/static/chat.css")
    async def stylesheet() -> FileResponse:
        return FileResponse(STATIC / "chat.css", media_type="text/css")

    @app.get("/chat/static/chat.js")
    async def javascript() -> FileResponse:
        return FileResponse(STATIC / "chat.js", media_type="text/javascript")

    @app.post("/chat/conversations", status_code=201)
    async def create_conversation(request: Request) -> dict[str, str]:
        if await request.body():
            raise ChatError("invalid_request")
        return {"conversation_id": request.app.state.conversations.create()}

    @app.post("/chat/conversations/{conversation_id}/turns")
    async def send_turn(request: Request, conversation_id: str) -> dict[str, str]:
        request_id, message = await read_turn(request)
        reply = await request.app.state.conversations.turn(conversation_id, request_id, message)
        return {"request_id": request_id, "reply": reply}

    @app.delete("/chat/conversations/{conversation_id}", status_code=204)
    async def release(request: Request, conversation_id: str) -> Response:
        if await request.body():
            raise ChatError("invalid_request")
        await request.app.state.conversations.release(conversation_id)
        return Response(status_code=204)

    return app


app = create_app()
