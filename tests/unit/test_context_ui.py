"""Unit tests for Milestone 6 UI components: DedicatedCodeEditor, ContextPanel, and FilePreviewDialog."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from sarthika_code.domain.context import SelectedFileContext
from sarthika_code.services.context_service import ProjectContextService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.storage.repositories import ChatRepository
from sarthika_code.ui.chat.context_panel import ContextPanel, FilePreviewDialog
from sarthika_code.ui.editor.code_editor import DedicatedCodeEditor


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


class TestDedicatedCodeEditor:
    """Tests for the code editor widget, stats, and actions."""

    def test_editor_initialization_and_text_stats(self, qapp: QApplication) -> None:
        editor = DedicatedCodeEditor(initial_language="python")
        editor.set_code("print('hello')\nx = 10\n")

        assert "print('hello')" in editor.get_code()
        assert editor.language == "python"

        # Check stats label
        stats_text = editor.lbl_stats.text()
        assert "Lines: 2" in stats_text
        assert "Chars: 22" in stats_text
        assert "Est. Tokens:" in stats_text

    def test_editor_language_switch(self, qapp: QApplication) -> None:
        editor = DedicatedCodeEditor(initial_language="python")
        editor.set_language("javascript")
        assert editor.language == "javascript"

    def test_editor_clear(self, qapp: QApplication) -> None:
        editor = DedicatedCodeEditor()
        editor.set_code("def foo(): pass")
        assert len(editor.get_code()) > 0
        editor.clear()
        assert editor.get_code() == ""


class TestContextPanel:
    """Tests for the context panel managing files and budget."""

    @pytest.fixture
    def service(self, tmp_path: Path) -> ProjectContextService:
        db_path = tmp_path / "test_ui.db"
        db = DatabaseManager(db_path)
        db.init_db()

        with db.session() as session:
            ChatRepository().create(session, chat_id="c1", title="Test")

        return ProjectContextService(db)

    def test_panel_load_and_budget(self, qapp: QApplication, service: ProjectContextService, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("a = 10\nb = 20\n", encoding="utf-8")
        service.add_file("c1", f)

        panel = ContextPanel(context_service=service)
        panel.set_chat("c1", context_limit=4096)

        assert panel.table_files.rowCount() == 1
        item_name = panel.table_files.item(0, 0)
        assert item_name is not None
        assert item_name.text() == "test.py"

        # Budget bar text
        assert "tokens" in panel.lbl_budget.text()
        assert "Budget:" in panel.lbl_budget.text()

    def test_file_preview_dialog(self, qapp: QApplication) -> None:
        file_ctx = SelectedFileContext(
            id="ctx-1",
            chat_id="c1",
            file_path="/app/test.py",
            display_name="test.py",
            byte_size=100,
            line_count=1,
            estimated_tokens=12,
            language="python",
            content="print('hello')",
        )
        dialog = FilePreviewDialog(file_ctx)
        assert dialog.windowTitle() == "Preview: test.py"
        assert "print('hello')" in dialog.txt_view.toPlainText()
