"""Chat history sidebar for Sarthika Code.

Provides a list of past local conversations, new chat initiation, renaming,
cascading deletion with confirmation, and export shortcuts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.domain.chat import Chat

if TYPE_CHECKING:
    pass


class ChatSidebar(QWidget):
    """Left sidebar widget displaying conversation history and management actions."""

    chat_selected = Signal(str)  # chat_id
    new_chat_requested = Signal()
    rename_chat_requested = Signal(str, str)  # chat_id, new_title
    delete_chat_requested = Signal(str)  # chat_id
    export_chat_requested = Signal(str, str)  # chat_id, format ("markdown" or "txt")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(360)
        self._chats: list[Chat] = []

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)

        # Header with "+ New Chat" button
        header_layout = QHBoxLayout()

        title_label = QLabel("Conversations")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #94a3b8;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.btn_new_chat = QPushButton("+ New Chat")
        self.btn_new_chat.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_new_chat.clicked.connect(self._on_new_chat_clicked)
        header_layout.addWidget(self.btn_new_chat)

        layout.addLayout(header_layout)

        # Chat List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget {"
            "  background-color: #0f172a;"
            "  color: #f1f5f9;"
            "  border: 1px solid #334155;"
            "  border-radius: 6px;"
            "  padding: 4px;"
            "}"
            "QListWidget::item {"
            "  padding: 8px 10px;"
            "  border-radius: 4px;"
            "  margin-bottom: 2px;"
            "}"
            "QListWidget::item:hover {"
            "  background-color: #1e293b;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: #3b82f6;"
            "  color: white;"
            "  font-weight: bold;"
            "}"
        )
        self.list_widget.itemSelectionChanged.connect(self._on_item_selection_changed)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget)

        # Footer Actions
        footer_layout = QHBoxLayout()
        self.btn_rename = QPushButton("Rename")
        self.btn_rename.setStyleSheet("background-color: #334155; color: #f1f5f9; padding: 4px 8px; border-radius: 4px;")
        self.btn_rename.clicked.connect(self._on_rename_clicked)
        footer_layout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("background-color: #450a0a; color: #f87171; padding: 4px 8px; border-radius: 4px;")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        footer_layout.addWidget(self.btn_delete)

        layout.addLayout(footer_layout)

    def set_chats(self, chats: list[Chat], active_chat_id: str | None = None) -> None:
        """Populate the sidebar with chats, restoring selection."""
        self._chats = chats
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        selected_row = -1
        for i, chat in enumerate(chats):
            item = QListWidgetItem(chat.title)
            item.setData(Qt.ItemDataRole.UserRole, chat.id)
            time_str = chat.updated_at.strftime("%b %d, %H:%M") if chat.updated_at else ""
            item.setToolTip(f"{chat.title}\nLast active: {time_str}")
            self.list_widget.addItem(item)

            if active_chat_id and chat.id == active_chat_id:
                selected_row = i

        if selected_row >= 0:
            self.list_widget.setCurrentRow(selected_row)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        self.list_widget.blockSignals(False)

    def get_selected_chat_id(self) -> str | None:
        """Return the ID of the currently selected chat, or None."""
        current_item = self.list_widget.currentItem()
        if current_item is not None:
            return str(current_item.data(Qt.ItemDataRole.UserRole))
        return None

    def _on_item_selection_changed(self) -> None:
        chat_id = self.get_selected_chat_id()
        if chat_id:
            self.chat_selected.emit(chat_id)

    def _on_new_chat_clicked(self) -> None:
        self.new_chat_requested.emit()

    def _on_rename_clicked(self) -> None:
        chat_id = self.get_selected_chat_id()
        if not chat_id:
            return

        current_item = self.list_widget.currentItem()
        current_title = current_item.text() if current_item else "New Chat"

        new_title, ok = QInputDialog.getText(
            self,
            "Rename Conversation",
            "Enter new conversation title:",
            text=current_title,
        )
        if ok and new_title.strip():
            self.rename_chat_requested.emit(chat_id, new_title.strip())

    def _on_delete_clicked(self) -> None:
        chat_id = self.get_selected_chat_id()
        if not chat_id:
            return

        current_item = self.list_widget.currentItem()
        current_title = current_item.text() if current_item else "this conversation"

        reply = QMessageBox.question(
            self,
            "Delete Conversation",
            f"Are you sure you want to permanently delete '{current_title}'?\n\n"
            "This action cannot be undone. All messages will be erased locally.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_chat_requested.emit(chat_id)

    def _show_context_menu(self, position: QPoint) -> None:
        item = self.list_widget.itemAt(position)
        if item is None:
            return

        chat_id = str(item.data(Qt.ItemDataRole.UserRole))
        menu = QMenu(self)

        action_rename = QAction("Rename", self)
        action_rename.triggered.connect(self._on_rename_clicked)
        menu.addAction(action_rename)

        action_export_md = QAction("Export to Markdown (.md)...", self)
        action_export_md.triggered.connect(lambda: self.export_chat_requested.emit(chat_id, "markdown"))
        menu.addAction(action_export_md)

        action_export_txt = QAction("Export to Plain Text (.txt)...", self)
        action_export_txt.triggered.connect(lambda: self.export_chat_requested.emit(chat_id, "txt"))
        menu.addAction(action_export_txt)

        menu.addSeparator()

        action_delete = QAction("Delete", self)
        action_delete.triggered.connect(self._on_delete_clicked)
        menu.addAction(action_delete)

        menu.exec(self.list_widget.mapToGlobal(position))
