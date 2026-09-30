"""Context and code snippet panel for Sarthika Code workspace.

Provides explicit file selection, sensitive-file warnings, context budget gauge,
file content preview, and integration with the dedicated code editor.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.domain.context import ContextBudget, SelectedFileContext
from sarthika_code.domain.errors import SensitiveFileError
from sarthika_code.services.context_service import ProjectContextService
from sarthika_code.ui.editor.code_editor import DedicatedCodeEditor
from sarthika_code.utils.logging import get_logger

logger = get_logger("ContextPanel")


class FilePreviewDialog(QDialog):
    """Read-only preview dialog displaying an attached file's contents, lines, and metadata."""

    def __init__(self, file_ctx: SelectedFileContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.file_ctx = file_ctx
        self.setWindowTitle(f"Preview: {file_ctx.display_name}")
        self.resize(700, 500)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Metadata header
        meta_frame = QFrame()
        meta_frame.setStyleSheet("background-color: #0f172a; border-radius: 6px; padding: 8px;")
        meta_layout = QHBoxLayout(meta_frame)

        info_text = (
            f"<b>{self.file_ctx.display_name}</b> | "
            f"Language: <code>{self.file_ctx.language}</code> | "
            f"Lines: {self.file_ctx.line_count} | "
            f"Size: {self.file_ctx.byte_size:,} bytes | "
            f"Estimated Tokens: ~{self.file_ctx.estimated_tokens:,}"
        )
        lbl_info = QLabel(info_text)
        lbl_info.setStyleSheet("color: #f8fafc; font-size: 11px;")
        meta_layout.addWidget(lbl_info)
        layout.addWidget(meta_frame)

        # File content viewer
        self.txt_view = QPlainTextEdit()
        self.txt_view.setReadOnly(True)
        self.txt_view.setPlainText(self.file_ctx.content)
        self.txt_view.setFont(QFont("Monospace", 10))
        self.txt_view.setStyleSheet("background-color: #030712; color: #e2e8f0; border: 1px solid #1e293b; padding: 8px;")
        layout.addWidget(self.txt_view, stretch=1)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 6px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)


class ContextPanel(QWidget):
    """Panel managing attached project files and dedicated snippet editor."""

    context_changed = Signal()  # Emitted whenever files are added or removed
    snippet_inserted = Signal(str, str)  # code, language

    def __init__(
        self,
        context_service: ProjectContextService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.context_service = context_service
        self.current_chat_id: str | None = None
        self.context_limit: int = 4096
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        self.setStyleSheet("""
            QWidget {
                background-color: #080b13;
                color: #e2e8f0;
            }
        """)

        # Tab widget for Attached Files vs Code Snippet Editor
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #182236; background-color: #0c121e; border-radius: 8px; }
            QTabBar::tab { background-color: #0c121e; color: #94a3b8; padding: 5px 12px; margin-right: 2px; font-size: 11px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background-color: #121b2d; color: #38bdf8; font-weight: bold; border-bottom: 2px solid #0284c7; }
        """)

        # ----------------------------------------------------------------------
        # Tab 1: Project Files Context
        # ----------------------------------------------------------------------
        tab_files = QWidget()
        files_layout = QVBoxLayout(tab_files)
        files_layout.setContentsMargins(8, 8, 8, 8)
        files_layout.setSpacing(6)

        # Controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.chk_include = QCheckBox("Include attached context in next request")
        self.chk_include.setChecked(True)
        self.chk_include.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 11px;")
        ctrl_row.addWidget(self.chk_include)

        ctrl_row.addStretch()

        self.btn_add_file = QPushButton("+ Add File...")
        self.btn_add_file.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; border: none; padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_add_file.clicked.connect(self._on_add_file_clicked)
        ctrl_row.addWidget(self.btn_add_file)

        self.btn_clear_files = QPushButton("Clear Files")
        self.btn_clear_files.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 4px 10px; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background-color: #334155; color: #f8fafc; }
        """)
        self.btn_clear_files.clicked.connect(self._on_clear_files_clicked)
        ctrl_row.addWidget(self.btn_clear_files)

        files_layout.addLayout(ctrl_row)

        # Context Budget gauge bar
        budget_row = QHBoxLayout()
        budget_row.setSpacing(8)

        self.lbl_budget = QLabel("Budget: 0 files | 0 tokens (0%)")
        self.lbl_budget.setStyleSheet("color: #94a3b8; font-size: 11px;")
        budget_row.addWidget(self.lbl_budget)

        self.progress_budget = QProgressBar()
        self.progress_budget.setMaximum(100)
        self.progress_budget.setValue(0)
        self.progress_budget.setFixedHeight(6)
        self.progress_budget.setTextVisible(False)
        self.progress_budget.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 3px; }
            QProgressBar::chunk { background-color: #10b981; border-radius: 3px; }
        """)
        budget_row.addWidget(self.progress_budget, stretch=1)

        files_layout.addLayout(budget_row)

        # Table of attached files
        self.table_files = QTableWidget()
        self.table_files.setColumnCount(5)
        self.table_files.setHorizontalHeaderLabels(["File Name", "Language", "Lines", "Est. Tokens", "Actions"])
        self.table_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_files.setStyleSheet("""
            QTableWidget {
                background-color: #030712;
                border: 1px solid #1e293b;
                gridline-color: #1e293b;
                color: #e2e8f0;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #1e293b;
                padding: 4px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.table_files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_files.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        files_layout.addWidget(self.table_files, stretch=1)

        self.tabs.addTab(tab_files, "Attached Project Files (0)")

        # ----------------------------------------------------------------------
        # Tab 2: Dedicated Code Snippet Editor
        # ----------------------------------------------------------------------
        self.code_editor = DedicatedCodeEditor()
        self.code_editor.snippet_submitted.connect(self._on_snippet_submitted)
        self.tabs.addTab(self.code_editor, "Code Snippet Editor")

        main_layout.addWidget(self.tabs)

    def set_chat(self, chat_id: str, context_limit: int = 4096) -> None:
        """Set the active chat session and refresh attached files and budget."""
        self.current_chat_id = chat_id
        self.context_limit = context_limit
        self.refresh_files()

    def should_include_context(self) -> bool:
        """Return True if user enabled context inclusion and files exist."""
        if not self.chk_include.isChecked():
            return False
        if not self.current_chat_id:
            return False
        files = self.context_service.list_files(self.current_chat_id)
        return len(files) > 0

    def get_attached_files(self) -> list[SelectedFileContext]:
        """Return list of all attached files for current chat."""
        if not self.current_chat_id:
            return []
        return self.context_service.list_files(self.current_chat_id)

    def refresh_files(self) -> None:
        """Reload file list from database, populate table, and update budget gauge."""
        if not self.current_chat_id:
            self.table_files.setRowCount(0)
            self.tabs.setTabText(0, "Attached Project Files (0)")
            self._update_budget_gauge(ContextBudget(0, 0, 0, self.context_limit, 0.0, "safe"))
            return

        files = self.context_service.list_files(self.current_chat_id)
        self.tabs.setTabText(0, f"Attached Project Files ({len(files)})")
        self.table_files.setRowCount(len(files))

        for row, f in enumerate(files):
            # File name
            item_name = QTableWidgetItem(f.display_name)
            item_name.setToolTip(f.file_path)
            self.table_files.setItem(row, 0, item_name)

            # Language
            item_lang = QTableWidgetItem(f.language)
            item_lang.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_files.setItem(row, 1, item_lang)

            # Lines
            item_lines = QTableWidgetItem(str(f.line_count))
            item_lines.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_files.setItem(row, 2, item_lines)

            # Tokens
            item_tokens = QTableWidgetItem(f"~{f.estimated_tokens:,}")
            item_tokens.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_files.setItem(row, 3, item_tokens)

            # Action buttons cell (Preview & Remove)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            btn_prev = QPushButton("Preview")
            btn_prev.setStyleSheet("""
                QPushButton { background-color: #1e293b; color: #38bdf8; border: 1px solid #0284c7; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
                QPushButton:hover { background-color: #0284c7; color: white; }
            """)
            btn_prev.clicked.connect(lambda _, ctx=f: self._on_preview_file(ctx))
            action_layout.addWidget(btn_prev)

            btn_del = QPushButton("✕")
            btn_del.setStyleSheet("""
                QPushButton { background-color: #1e293b; color: #f87171; border: 1px solid #ef4444; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background-color: #ef4444; color: white; }
            """)
            btn_del.clicked.connect(lambda _, ctx_id=f.id: self._on_remove_file(ctx_id))
            action_layout.addWidget(btn_del)

            self.table_files.setCellWidget(row, 4, action_widget)

        budget = self.context_service.get_budget(self.current_chat_id, context_limit=self.context_limit)
        self._update_budget_gauge(budget)

    def _update_budget_gauge(self, budget: ContextBudget) -> None:
        val = min(100, int(budget.usage_percentage))
        self.progress_budget.setValue(val)

        # Color coding
        if budget.status == "exceeded":
            bar_color = "#ef4444"  # red
            status_text = "<b style='color: #ef4444;'>Exceeded</b>"
        elif budget.status == "critical":
            bar_color = "#f97316"  # orange
            status_text = "<b style='color: #f97316;'>Critical</b>"
        elif budget.status == "warning":
            bar_color = "#eab308"  # yellow
            status_text = "<b style='color: #eab308;'>Warning</b>"
        else:
            bar_color = "#10b981"  # green
            status_text = "<span style='color: #4ade80;'>Safe</span>"

        self.progress_budget.setStyleSheet(f"""
            QProgressBar {{ background-color: #1e293b; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}
        """)

        self.lbl_budget.setText(
            f"Budget: {budget.total_files} files | {budget.total_characters:,} chars | "
            f"~{budget.total_tokens:,} / {budget.context_limit:,} tokens ({budget.usage_percentage}%) [{status_text}]"
        )

    def _on_add_file_clicked(self) -> None:
        """Prompt user for explicit file selection and validate security policies."""
        if not self.current_chat_id:
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Project Files as Read-Only Context",
            "",
            "Source Files (*.py *.php *.js *.ts *.sql *.html *.css *.json *.sh *.md *.txt);;All Files (*)",
        )

        if not file_paths:
            return

        added_count = 0
        blocked_messages: list[str] = []

        for p_str in file_paths:
            p = Path(p_str)
            try:
                self.context_service.add_file(self.current_chat_id, p)
                added_count += 1
            except SensitiveFileError as e:
                blocked_messages.append(f"• {p.name}: {e.message}")
            except Exception as e:
                blocked_messages.append(f"• {p.name}: {e}")

        self.refresh_files()
        self.context_changed.emit()

        if blocked_messages:
            msg = "The following file(s) were blocked by security policies:\n\n" + "\n".join(blocked_messages)
            QMessageBox.warning(self, "Security Filter: File(s) Blocked", msg)

    def _on_preview_file(self, file_ctx: SelectedFileContext) -> None:
        dlg = FilePreviewDialog(file_ctx, self)
        dlg.exec()

    def _on_remove_file(self, context_id: str) -> None:
        self.context_service.remove_file(context_id)
        self.refresh_files()
        self.context_changed.emit()

    def _on_clear_files_clicked(self) -> None:
        if not self.current_chat_id:
            return
        self.context_service.clear_files(self.current_chat_id)
        self.refresh_files()
        self.context_changed.emit()

    def _on_snippet_submitted(self, code: str, language: str) -> None:
        self.snippet_inserted.emit(code, language)
