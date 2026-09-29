"""Unit tests for Milestone 4 Chat UI components (Sidebar, MessageWidget, InputBar, Workspace)."""

from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QLabel

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.chat import Chat, Message
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.ui.chat.chat_input_bar import ChatInputBar
from sarthika_code.ui.chat.chat_sidebar import ChatSidebar
from sarthika_code.ui.chat.chat_workspace import ChatWorkspace
from sarthika_code.ui.chat.message_widget import MessageWidget, extract_code_blocks
from sarthika_code.ui.main_window import MainWindow


def test_extract_code_blocks() -> None:
    """Verify regex extraction of fenced code blocks."""
    text = (
        "Here is the code:\n\n"
        "```python\n"
        "def add(a, b):\n"
        "    return a + b\n"
        "```\n\n"
        "And another:\n"
        "```bash\n"
        "ls -la\n"
        "```"
    )
    blocks = extract_code_blocks(text)
    assert len(blocks) == 2
    assert "def add(a, b):" in blocks[0]
    assert "ls -la" in blocks[1]


def test_chat_sidebar_ui(qapp: QApplication) -> None:
    """Verify ChatSidebar population, selection, and signal emission."""
    sidebar = ChatSidebar()

    chats = [
        Chat(id="c1", title="Conversation One"),
        Chat(id="c2", title="Conversation Two"),
    ]
    sidebar.set_chats(chats, active_chat_id="c1")

    assert sidebar.list_widget.count() == 2
    assert sidebar.get_selected_chat_id() == "c1"

    # Select second item
    sidebar.list_widget.setCurrentRow(1)
    assert sidebar.get_selected_chat_id() == "c2"

    # Test new chat signal
    new_chat_called = False

    def on_new() -> None:
        nonlocal new_chat_called
        new_chat_called = True

    sidebar.new_chat_requested.connect(on_new)
    sidebar.btn_new_chat.click()
    assert new_chat_called is True

    sidebar.close()


def test_message_widget_user_and_assistant(qapp: QApplication) -> None:
    """Verify MessageWidget distinguishes user from assistant and detects code blocks."""
    # User message
    user_msg = Message(id="m1", chat_id="c1", role="user", content="Explain loops")
    w_user = MessageWidget(user_msg)
    labels = [lbl.text() for lbl in w_user.findChildren(QLabel)]
    assert any("You" in lbl_text for lbl_text in labels)
    assert not hasattr(w_user, "btn_retry") or w_user.message.role == "user"
    w_user.close()

    # Assistant message with code
    asst_msg = Message(
        id="m2",
        chat_id="c1",
        role="assistant",
        content="Here is a loop:\n```python\nfor i in range(5): print(i)\n```",
    )
    w_asst = MessageWidget(asst_msg)
    asst_labels = [lbl.text() for lbl in w_asst.findChildren(QLabel)]
    assert any("Sarthika Code" in lbl_text for lbl_text in asst_labels)
    assert hasattr(w_asst, "btn_copy_code")
    assert w_asst.btn_copy_code is not None
    assert hasattr(w_asst, "btn_retry")
    w_asst.close()


def test_chat_input_bar_controls(qapp: QApplication) -> None:
    """Verify ChatInputBar toggles generating state, emits submit, and handles retry."""
    input_bar = ChatInputBar()

    submitted_text = ""

    def on_submit(text: str) -> None:
        nonlocal submitted_text
        submitted_text = text

    input_bar.submit_requested.connect(on_submit)

    # Submitting empty does nothing
    input_bar.set_prompt_text("")
    input_bar._on_submit_clicked()
    assert submitted_text == ""

    # Submitting prompt text
    input_bar.set_prompt_text("Hello Sarthika")
    input_bar._on_submit_clicked()
    assert submitted_text == "Hello Sarthika"
    assert input_bar.get_prompt_text() == ""

    # Toggle generating state
    input_bar.set_generating(True)
    assert input_bar.btn_send.isEnabled() is False
    assert not input_bar.btn_cancel.isHidden()

    input_bar.set_generating(False)
    assert input_bar.btn_send.isEnabled() is True
    assert input_bar.btn_cancel.isHidden()

    input_bar.close()


def test_chat_workspace_load_chat(
    qapp: QApplication,
    db_manager: DatabaseManager,
    settings_service: SettingsService,
) -> None:
    """Verify ChatWorkspace loads conversation history cleanly."""
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Test Workspace Chat")
    chat_service.add_user_message(chat.id, "User query 1")
    asst = chat_service.create_assistant_placeholder(chat.id)
    chat_service.update_assistant_message(asst.id, "Assistant reply 1")

    workspace = ChatWorkspace(
        chat_service=chat_service,
        settings_service=settings_service,
        model_service=None,
    )

    workspace.load_chat(chat.id)
    assert workspace.lbl_chat_title.text() == "Test Workspace Chat"
    assert workspace.btn_export.isEnabled() is True
    # Count of message widgets inside layout (plus stretch)
    assert workspace.message_layout.count() >= 3

    workspace.close()


def test_main_window_full_workspace_integration(
    qapp: QApplication,
    temp_paths: AppPaths,
    db_manager: DatabaseManager,
    settings_service: SettingsService,
) -> None:
    """Verify MainWindow integrates sidebar and workspace with chat lifecycle."""
    # Enable mock mode for testing
    settings = settings_service.load_settings()
    settings.mock_mode = True
    settings_service.save_settings(settings)

    chat_service = ChatService(db_manager)

    window = MainWindow(
        paths=temp_paths,
        settings_service=settings_service,
        chat_service=chat_service,
        model_service=None,
        diagnostics_service=None,
    )

    try:
        assert window.sidebar is not None
        assert window.workspace is not None

        # Verify initial chat is loaded
        assert window.sidebar.list_widget.count() >= 1
        active_id = window.sidebar.get_selected_chat_id()
        assert active_id is not None

        # Test New Chat
        window._on_new_chat()
        assert window.sidebar.list_widget.count() >= 2

        # Test Rename Chat
        new_active = window.sidebar.get_selected_chat_id()
        assert new_active is not None
        window._on_rename_chat(new_active, "My Custom Project Chat")
        assert window.workspace.lbl_chat_title.text() == "My Custom Project Chat"

        # Test Export Dialog trigger
        with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName") as mock_save:
            test_export_path = temp_paths.exports_dir / "test_export.md"
            mock_save.return_value = (str(test_export_path), "Markdown Document (*.md)")
            with patch("PySide6.QtWidgets.QMessageBox.information"):
                window._on_export_chat(new_active, default_format="markdown")
                assert test_export_path.exists()
                content = test_export_path.read_text(encoding="utf-8")
                assert "# My Custom Project Chat" in content

    finally:
        window.close()
