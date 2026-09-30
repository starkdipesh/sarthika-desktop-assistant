"""UI unit tests for Milestone 5 workflow components, cards, and debug dialogs."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from sarthika_code.app.paths import get_app_paths
from sarthika_code.prompts.registry import WorkflowRegistry
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.services.workflow_service import WorkflowService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.ui.chat.chat_workspace import ChatWorkspace
from sarthika_code.ui.chat.workflow_selection_widget import WorkflowCard, WorkflowSelectionWidget
from sarthika_code.ui.dialogs.prompt_review_dialog import PromptReviewDialog
from sarthika_code.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure single persistent QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


def test_workflow_card_click(qapp: QApplication) -> None:
    """Verify that WorkflowCard emits clicked signal with its workflow ID."""
    wf = WorkflowRegistry.get_workflow("debug_code")
    assert wf is not None

    card = WorkflowCard(wf)
    received: list[str] = []
    card.clicked.connect(received.append)

    # Simulate click
    card.clicked.emit(wf.id)
    assert received == ["debug_code"]


def test_workflow_selection_widget(qapp: QApplication) -> None:
    """Verify that WorkflowSelectionWidget renders all 11 cards and propagates selection."""
    widget = WorkflowSelectionWidget()
    received: list[str] = []
    widget.workflow_selected.connect(received.append)

    cards = widget.findChildren(WorkflowCard)
    assert len(cards) == 11

    # Simulate card click
    cards[0].clicked.emit(cards[0].workflow.id)
    assert len(received) == 1
    assert received[0] == cards[0].workflow.id


def test_prompt_review_dialog(qapp: QApplication) -> None:
    """Verify PromptReviewDialog initializes and displays debug prompt data."""
    service = WorkflowService()
    debug_bundle = service.inspect_debug_prompt(
        workflow_id="explain_code",
        user_request="Explain binary search",
        code_context="def bsearch(): pass",
    )

    dialog = PromptReviewDialog(debug_bundle)
    assert "Workflow: Explain Code" in dialog.windowTitle() or "Developer Debug Mode" in dialog.windowTitle()
    dialog.close()


def test_chat_workspace_workflow_sync(qapp: QApplication, tmp_path: Path) -> None:
    """Verify ChatWorkspace synchronizes workflow combo box with active chat."""
    db_file = tmp_path / "test_workspace_wf.db"
    db_mgr = DatabaseManager(db_file)
    db_mgr.init_db()

    chat_service = ChatService(db_mgr)
    settings_service = SettingsService(db_mgr)

    chat = chat_service.create_chat(title="Test Chat", workflow="database_schema_draft")

    workspace = ChatWorkspace(chat_service=chat_service, settings_service=settings_service)
    workspace.load_chat(chat.id)

    # Verify combo box has selected workflow
    assert workspace.combo_workflow.currentData() == "database_schema_draft"

    # Switch combo box to python_component_draft
    idx = workspace.combo_workflow.findData("python_component_draft")
    assert idx >= 0
    workspace.combo_workflow.setCurrentIndex(idx)

    # Verify active chat updated
    assert workspace.active_chat is not None
    assert workspace.active_chat.workflow == "python_component_draft"

    # Verify database was updated
    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    assert reloaded.workflow == "python_component_draft"


def test_main_window_debug_mode_toggle(qapp: QApplication, tmp_path: Path) -> None:
    """Verify MainWindow toggling Developer Debug Mode updates workspace inspect button visibility."""
    paths = get_app_paths(base_override=tmp_path)
    paths.ensure_directories()

    db_mgr = DatabaseManager(paths.database_file)
    db_mgr.init_db()

    settings_service = SettingsService(db_mgr)
    chat_service = ChatService(db_mgr)

    window = MainWindow(
        paths=paths,
        settings_service=settings_service,
        chat_service=chat_service,
    )

    # Initially debug mode is False, inspect button is hidden
    assert not window.settings.debug_mode
    assert window.workspace.btn_inspect_prompt.isHidden()
    assert not window.inspect_prompt_action.isVisible()

    # Toggle debug mode on
    window._toggle_debug_mode()
    assert window.settings.debug_mode is True
    assert not window.workspace.btn_inspect_prompt.isHidden()
    assert window.inspect_prompt_action.isVisible()

    # Toggle debug mode off
    window._toggle_debug_mode()
    assert window.settings.debug_mode is False
    assert window.workspace.btn_inspect_prompt.isHidden()
    assert not window.inspect_prompt_action.isVisible()

    window.close()
