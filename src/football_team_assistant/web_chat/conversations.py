import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from secrets import token_urlsafe

from anyio import BrokenResourceError, ClosedResourceError
from mcp import MCPError
from mcp.types import CONNECTION_CLOSED

from football_team_assistant.football_agent import FootballAgent

AMBIGUOUS_FIXTURE = "Multiple fixtures match. Please specify a fixture ID: "


class ChatError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass
class CompletedTurn:
    request_id: str
    message: str
    reply: str


@dataclass
class Conversation:
    agent: FootballAgent
    pending: asyncio.Task[str] | None = None
    last_turn: CompletedTurn | None = None


class Conversations:
    def __init__(self, agent_factory: Callable[[], FootballAgent] | None, timeout: float) -> None:
        self._agent_factory = agent_factory
        self._timeout = timeout
        self._conversations: dict[str, Conversation] = {}

    def create(self) -> str:
        if self._agent_factory is None:
            raise ChatError("runtime_unavailable")
        identifier = token_urlsafe(32)
        self._conversations[identifier] = Conversation(self._agent_factory())
        return identifier

    async def turn(self, identifier: str, request_id: str, message: str) -> str:
        conversation = self._conversations.get(identifier)
        if conversation is None:
            raise ChatError("conversation_missing")
        if conversation.pending is not None:
            raise ChatError("turn_pending")
        previous = conversation.last_turn
        if previous is not None and previous.request_id == request_id:
            if message != previous.message:
                raise ChatError("invalid_request")
            return previous.reply

        task = asyncio.create_task(self._complete_turn(conversation, request_id, message))
        conversation.pending = task
        try:
            reply = await task
            if identifier not in self._conversations:
                raise ChatError("conversation_missing")
            return reply
        except asyncio.CancelledError:
            if identifier not in self._conversations:
                raise ChatError("conversation_missing") from None
            raise
        finally:
            conversation.pending = None

    async def _complete_turn(
        self, conversation: Conversation, request_id: str, message: str
    ) -> str:
        reply = await self._ask(conversation.agent, message)
        # Save the replay before the requesting task can resume or be cancelled.
        conversation.last_turn = CompletedTurn(request_id, message, reply)
        return reply

    async def _ask(self, agent: FootballAgent, message: str) -> str:
        history_length = len(agent.messages)
        fixture_id = agent.current_fixture_id
        completed = False
        try:
            async with asyncio.timeout(self._timeout):
                reply = await agent.ask(message)
            if not isinstance(reply, str) or not reply.strip():
                raise ChatError("agent_unavailable")
            completed = True
            return reply
        except TimeoutError:
            raise ChatError("turn_timeout") from None
        except (BrokenResourceError, ClosedResourceError):
            raise ChatError("runtime_unavailable") from None
        except MCPError as error:
            code = (
                "runtime_unavailable"
                if error.error.code == CONNECTION_CLOSED
                else "agent_unavailable"
            )
            raise ChatError(code) from None
        except ChatError:
            raise
        except ValueError as error:
            if str(error).startswith(AMBIGUOUS_FIXTURE):
                return str(error)
            raise ChatError("agent_unavailable") from None
        except Exception:
            # Third-party errors may include prompt, tool, or connection details.
            raise ChatError("agent_unavailable") from None
        finally:
            if not completed:
                del agent.messages[history_length:]
                agent.current_fixture_id = fixture_id

    async def release(self, identifier: str) -> None:
        conversation = self._conversations.pop(identifier, None)
        if conversation is not None and conversation.pending is not None:
            conversation.pending.cancel()
            await asyncio.gather(conversation.pending, return_exceptions=True)

    async def close(self) -> None:
        pending = [
            conversation.pending
            for conversation in self._conversations.values()
            if conversation.pending is not None
        ]
        self._conversations.clear()
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
