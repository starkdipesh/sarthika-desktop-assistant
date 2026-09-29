"""Unit tests for ServerState enum, transitions, and ServerStatus."""

from __future__ import annotations

import pytest

from sarthika_code.domain.server import (
    InvalidStateTransitionError,
    ServerState,
    ServerStatus,
    validate_state_transition,
)


def test_all_eight_states_defined() -> None:
    """Verify that exactly the required 8 states are defined."""
    expected_states = {
        "STOPPED",
        "STARTING",
        "READY",
        "GENERATING",
        "STOPPING",
        "START_FAILED",
        "CRASHED",
        "UNAVAILABLE",
    }
    actual_states = {s.value for s in ServerState}
    assert actual_states == expected_states


def test_valid_lifecycle_transitions() -> None:
    """Verify permitted nominal state transitions."""
    # STOPPED -> STARTING
    validate_state_transition(ServerState.STOPPED, ServerState.STARTING)
    # STARTING -> READY
    validate_state_transition(ServerState.STARTING, ServerState.READY)
    # READY -> GENERATING
    validate_state_transition(ServerState.READY, ServerState.GENERATING)
    # GENERATING -> READY
    validate_state_transition(ServerState.GENERATING, ServerState.READY)
    # READY -> STOPPING
    validate_state_transition(ServerState.READY, ServerState.STOPPING)
    # STOPPING -> STOPPED
    validate_state_transition(ServerState.STOPPING, ServerState.STOPPED)


def test_failure_and_recovery_transitions() -> None:
    """Verify transitions for startup failure, crashes, and unavailability."""
    # STARTING -> START_FAILED -> STOPPED / STARTING
    validate_state_transition(ServerState.STARTING, ServerState.START_FAILED)
    validate_state_transition(ServerState.START_FAILED, ServerState.STOPPED)
    validate_state_transition(ServerState.START_FAILED, ServerState.STARTING)

    # READY -> CRASHED -> STOPPED / STARTING
    validate_state_transition(ServerState.READY, ServerState.CRASHED)
    validate_state_transition(ServerState.CRASHED, ServerState.STOPPED)
    validate_state_transition(ServerState.CRASHED, ServerState.STARTING)

    # READY -> UNAVAILABLE -> STOPPED
    validate_state_transition(ServerState.READY, ServerState.UNAVAILABLE)
    validate_state_transition(ServerState.UNAVAILABLE, ServerState.STOPPED)


def test_invalid_transitions_raise_error() -> None:
    """Verify illegal transitions raise InvalidStateTransitionError."""
    # Cannot jump from STOPPED directly to GENERATING or STOPPING
    with pytest.raises(InvalidStateTransitionError):
        validate_state_transition(ServerState.STOPPED, ServerState.GENERATING)

    with pytest.raises(InvalidStateTransitionError):
        validate_state_transition(ServerState.STOPPED, ServerState.STOPPING)

    with pytest.raises(InvalidStateTransitionError):
        validate_state_transition(ServerState.STOPPED, ServerState.CRASHED)

    # Cannot jump from STARTING to GENERATING
    with pytest.raises(InvalidStateTransitionError):
        validate_state_transition(ServerState.STARTING, ServerState.GENERATING)

    # Cannot jump from STOPPING back to READY
    with pytest.raises(InvalidStateTransitionError):
        validate_state_transition(ServerState.STOPPING, ServerState.READY)


def test_server_status_defaults() -> None:
    """Verify default attributes of ServerStatus."""
    status = ServerStatus()
    assert status.state == ServerState.STOPPED
    assert status.pid is None
    assert status.url is None
    assert status.is_managed is True
    assert status.last_error is None
