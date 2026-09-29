"""Domain entities and state machine for local llama-server.

Defines the exact 8-state machine, transitions, and status models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sarthika_code.domain.errors import ServerError


class ServerState(StrEnum):
    """Explicit lifecycle states for local llama-server."""

    STOPPED = "STOPPED"
    STARTING = "STARTING"
    READY = "READY"
    GENERATING = "GENERATING"
    STOPPING = "STOPPING"
    START_FAILED = "START_FAILED"
    CRASHED = "CRASHED"
    UNAVAILABLE = "UNAVAILABLE"


# Permitted state transitions according to architecture specification
ALLOWED_TRANSITIONS: dict[ServerState, set[ServerState]] = {
    ServerState.STOPPED: {ServerState.STARTING, ServerState.READY, ServerState.UNAVAILABLE},
    ServerState.STARTING: {ServerState.READY, ServerState.START_FAILED, ServerState.STOPPING},
    ServerState.READY: {
        ServerState.GENERATING,
        ServerState.STOPPING,
        ServerState.CRASHED,
        ServerState.UNAVAILABLE,
    },
    ServerState.GENERATING: {
        ServerState.READY,
        ServerState.STOPPING,
        ServerState.CRASHED,
        ServerState.UNAVAILABLE,
    },
    ServerState.STOPPING: {ServerState.STOPPED, ServerState.CRASHED},
    ServerState.START_FAILED: {ServerState.STOPPED, ServerState.STARTING},
    ServerState.CRASHED: {ServerState.STOPPED, ServerState.STARTING},
    ServerState.UNAVAILABLE: {ServerState.STOPPED, ServerState.STARTING},
}


class InvalidStateTransitionError(ServerError):
    """Raised when an illegal transition is attempted on ServerState."""

    def __init__(self, from_state: ServerState, to_state: ServerState) -> None:
        super().__init__(
            message=f"Illegal server state transition from {from_state.value} to {to_state.value}.",
            user_guidance="The server state machine prevented an invalid transition. Check Diagnostics for details.",
        )
        self.from_state = from_state
        self.to_state = to_state


def validate_state_transition(current_state: ServerState, new_state: ServerState) -> None:
    """Validate whether transitioning from current_state to new_state is permissible."""
    if current_state == new_state:
        return
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    if new_state not in allowed:
        raise InvalidStateTransitionError(current_state, new_state)


@dataclass(frozen=True)
class ServerStatus:
    """Immutable snapshot of llama-server runtime status."""

    state: ServerState = ServerState.STOPPED
    message: str = "Server is stopped."
    url: str | None = None
    pid: int | None = None
    started_at: datetime | None = None
    last_error: str | None = None
    is_managed: bool = True  # True if spawned by Sarthika Code; False if connected to external local server
