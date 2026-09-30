"""Unit tests for Milestone 5 curated developer workflow architecture.

Validates domain models, registry, prompt builder, safety invariants,
database persistence, debug prompt review, and mock mode streaming.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sarthika_code.domain.config import GenerationSettings
from sarthika_code.domain.workflow import Workflow
from sarthika_code.llm.base import StreamCompletedEvent, StreamTokenEvent
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.prompts.builder import (
    DELIMITER_END,
    DELIMITER_START,
    INJECTION_DEFENSE_HEADER,
    PromptBuilder,
)
from sarthika_code.prompts.registry import WorkflowRegistry
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.workflow_service import WorkflowService
from sarthika_code.storage.database import DatabaseManager

REQUIRED_WORKFLOW_IDS = {
    "explain_code",
    "debug_code",
    "refactor_code",
    "generate_unit_tests",
    "laravel_component_draft",
    "python_component_draft",
    "explain_sql_query",
    "requirement_to_implementation_plan",
    "review_git_diff",
    "api_design_draft",
    "database_schema_draft",
}


def test_all_required_workflow_ids_exist() -> None:
    """Verify that all 11 curated Version 0.1 workflows exist in the registry with valid attributes."""
    workflows = WorkflowRegistry.list_workflows()
    registered_ids = {w.id for w in workflows}

    assert registered_ids == REQUIRED_WORKFLOW_IDS
    assert len(workflows) == 11

    for wf in workflows:
        assert isinstance(wf, Workflow)
        assert wf.name.strip()
        assert wf.description.strip()
        assert wf.system_prompt.strip()
        assert len(wf.input_requirements) > 0
        assert wf.output_format.strip()
        assert wf.safety_disclaimer.strip()
        assert isinstance(wf.recommended_language, list)


def test_prompts_contain_required_safety_instructions() -> None:
    """Verify that every workflow system prompt contains all required safety directives."""
    required_phrases = [
        "State Assumptions",
        "Identify Uncertainty",
        "Never Claim Code Execution",
        "Never Claim Tests Passed",
        "Reviewable Output",
        "Prefer Minimal Changes",
        "Explain Risky Changes",
        "Recommend Local Validation",
        "No Application Commands",
        "No Direct File Access",
        "Untrusted Input Handling",
    ]

    for wf in WorkflowRegistry.list_workflows():
        prompt = wf.system_prompt
        for phrase in required_phrases:
            assert phrase.lower() in prompt.lower(), (
                f"Workflow '{wf.id}' prompt is missing required safety directive: '{phrase}'"
            )


def test_prompt_construction_is_deterministic() -> None:
    """Verify that prompt builder output is 100% deterministic and byte-for-byte reproducible."""
    wf = WorkflowRegistry.get_workflow("explain_code")
    assert wf is not None

    user_req = "Explain how quicksort partitions elements in place."
    code = "def partition(arr, low, high):\n    pivot = arr[high]\n    ..."
    lang = "python"

    out1 = PromptBuilder.build_full_prompt(wf, user_req, code_context=code, language=lang)
    out2 = PromptBuilder.build_full_prompt(wf, user_req, code_context=code, language=lang)
    out3 = PromptBuilder.build_full_prompt(wf, user_req, code_context=code, language=lang)

    assert out1 == out2 == out3
    assert out1[0] == wf.system_prompt


def test_user_code_is_clearly_delimited() -> None:
    """Verify that untrusted user input is wrapped with explicit delimiters and injection defense headers."""
    user_req = "Debug this crash"
    code = "raise RuntimeError('db down')"

    user_msg = PromptBuilder.build_user_message(user_req, code_context=code, language="python")

    assert DELIMITER_START in user_msg
    assert DELIMITER_END in user_msg
    assert INJECTION_DEFENSE_HEADER in user_msg
    assert "[User Request]\nDebug this crash" in user_msg
    assert "```python\nraise RuntimeError('db down')\n```" in user_msg

    # Verify order: Header -> DELIMITER_START -> Request -> Code -> DELIMITER_END
    idx_header = user_msg.index(INJECTION_DEFENSE_HEADER)
    idx_start = user_msg.index(DELIMITER_START)
    idx_req = user_msg.index(user_req)
    idx_code = user_msg.index(code)
    idx_end = user_msg.index(DELIMITER_END)

    assert idx_header < idx_start < idx_req < idx_code < idx_end


def test_missing_required_input_is_handled_cleanly() -> None:
    """Verify that empty or whitespace-only user input raises a clean ValueError."""
    with pytest.raises(ValueError, match="cannot both be empty"):
        PromptBuilder.build_user_message("", None)

    with pytest.raises(ValueError, match="cannot both be empty"):
        PromptBuilder.build_user_message("   \n\t  ", "   ")


def test_workflow_selection_persists_in_chat(tmp_path: Path) -> None:
    """Verify that workflow selection persists in the SQLite database across loads."""
    db_file = tmp_path / "test_workflow.db"
    db_mgr = DatabaseManager(db_file)
    db_mgr.init_db()

    chat_service = ChatService(db_mgr)

    # Create chat with specific workflow
    created = chat_service.create_chat(
        title="Refactoring Task",
        workflow="refactor_code",
    )
    assert created.workflow == "refactor_code"

    # Reload from fresh query
    loaded = chat_service.get_chat(created.id)
    assert loaded is not None
    assert loaded.workflow == "refactor_code"

    # Update workflow to generate_unit_tests
    success = chat_service.update_chat_workflow(created.id, "generate_unit_tests")
    assert success is True

    # Reload again and verify update
    reloaded = chat_service.get_chat(created.id)
    assert reloaded is not None
    assert reloaded.workflow == "generate_unit_tests"


@pytest.mark.asyncio
async def test_mock_mode_workflow_chat_behavior(tmp_path: Path) -> None:
    """Verify end-to-end streaming generation turn using a workflow system prompt with MockProvider."""
    db_file = tmp_path / "test_mock_workflow.db"
    db_mgr = DatabaseManager(db_file)
    db_mgr.init_db()

    chat_service = ChatService(db_mgr)
    chat = chat_service.create_chat(title="SQL Breakdown", workflow="explain_sql_query")

    user_msg = chat_service.add_user_message(
        chat.id,
        "SELECT u.id, count(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id",
    )
    assert user_msg.role == "user"

    asst_placeholder = chat_service.create_assistant_placeholder(chat.id)

    mock_provider = MockLLMProvider(token_delay=0.0)
    events = []

    async for event in chat_service.stream_chat_turn(
        chat_id=chat.id,
        assistant_message_id=asst_placeholder.id,
        provider=mock_provider,
        settings=GenerationSettings(),
    ):
        events.append(event)

    tokens = [e.delta for e in events if isinstance(e, StreamTokenEvent)]
    completions = [e for e in events if isinstance(e, StreamCompletedEvent)]

    assert len(tokens) > 0
    assert len(completions) == 1

    # Verify persisted message in database
    reloaded_chat = chat_service.get_chat(chat.id)
    assert reloaded_chat is not None
    assert len(reloaded_chat.messages) == 2
    assert reloaded_chat.messages[1].role == "assistant"
    assert len(reloaded_chat.messages[1].content) > 0


def test_workflow_service_inspect_debug_prompt() -> None:
    """Verify that WorkflowService provides complete debug prompt inspection."""
    service = WorkflowService()
    debug_bundle = service.inspect_debug_prompt(
        workflow_id="api_design_draft",
        user_request="Design a payments webhook API",
        code_context='{"event": "payment.succeeded"}',
        language="json",
    )

    assert debug_bundle["workflow_id"] == "api_design_draft"
    assert debug_bundle["workflow_name"] == "API Design Draft"
    assert "payments webhook API" in debug_bundle["user_message"]
    assert '{"event": "payment.succeeded"}' in debug_bundle["user_message"]
    assert "Core Operational Rules and Safety Directives" in debug_bundle["system_prompt"]
    assert "### SYSTEM PROMPT" in debug_bundle["full_debug_view"]


def test_workflow_service_fallbacks() -> None:
    """Verify that WorkflowService gracefully falls back to default workflow for unknown IDs."""
    service = WorkflowService()
    fallback = service.get_workflow("non_existent_custom_id")
    assert fallback.id == "explain_code"

    default_wf = service.get_default_workflow()
    assert default_wf.id == "explain_code"
