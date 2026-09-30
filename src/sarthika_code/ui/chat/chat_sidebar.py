"""Chat history sidebar for Sarthika Code.

Provides a list of past local conversations, new chat initiation, renaming,
cascading deletion with confirmation, export shortcuts, and bottom user profile card.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
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

    settings_requested = Signal()
    privacy_requested = Signal()
    help_requested = Signal()
    toggle_collapse_requested = Signal()
    lock_vault_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(230)
        self.setMaximumWidth(320)
        self._chats: list[Chat] = []
        self._user_name = "Dipesh Mahakali"

        self._init_ui()

    def set_user_profile(self, name: str) -> None:
        """Update the displayed user profile name."""
        self._user_name = name
        initial = name[0].upper() if name else "D"
        self.lbl_avatar.setText(initial)
        self.lbl_user_name.setText(name)

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            ChatSidebar {
                background-color: #080b13;
                border-right: 1px solid #151c28;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Top Brand Row + Collapse Toggle
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(2, 0, 2, 0)

        self.lbl_brand = QLabel("✦ Sarthika Code")
        brand_font = QFont()
        brand_font.setBold(True)
        brand_font.setPointSize(12)
        self.lbl_brand.setFont(brand_font)
        self.lbl_brand.setStyleSheet("color: #38bdf8; letter-spacing: 0.3px;")
        brand_layout.addWidget(self.lbl_brand)

        brand_layout.addStretch()

        self.btn_collapse = QPushButton("◀")
        self.btn_collapse.setToolTip("Collapse Sidebar")
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #162032;
                color: #f1f5f9;
                border-color: #1e2d4a;
            }
        """)
        self.btn_collapse.clicked.connect(self.toggle_collapse_requested.emit)
        brand_layout.addWidget(self.btn_collapse)

        layout.addLayout(brand_layout)

        # 2. Prominent "+ New Chat" Button
        self.btn_new_chat = QPushButton("+ New Chat")
        self.btn_new_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_chat.setStyleSheet("""
            QPushButton {
                background-color: #0c182c;
                color: #f8fafc;
                font-size: 12px;
                font-weight: 600;
                padding: 9px 14px;
                border: 1px solid #1e3a63;
                border-radius: 8px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #122442;
                border-color: #0284c7;
                color: #38bdf8;
            }
            QPushButton:pressed {
                background-color: #0c182c;
            }
        """)
        self.btn_new_chat.clicked.connect(self._on_new_chat_clicked)
        layout.addWidget(self.btn_new_chat)

        # 3. Search Filter Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search conversations...")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #0c121e;
                color: #f1f5f9;
                border: 1px solid #151c28;
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #0284c7;
                background-color: #0e1626;
            }
        """)
        self.txt_search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.txt_search)

        # 4. Conversations List Section Header
        lbl_section = QLabel("RECENT CONVERSATIONS")
        lbl_section.setStyleSheet(
            "color: #475569; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; margin-top: 4px;"
        )
        layout.addWidget(lbl_section)

        # 5. Chat List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: #cbd5e1;
                border: none;
                padding: 2px 0px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 8px;
                margin-bottom: 3px;
                border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #0e1422;
                color: #f8fafc;
                border: 1px solid #151c28;
            }
            QListWidget::item:selected {
                background-color: #121b2d;
                color: #38bdf8;
                border: 1px solid #1a2d4b;
                font-weight: 600;
            }
        """)
        self.list_widget.itemSelectionChanged.connect(self._on_item_selection_changed)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, stretch=1)

        # 6. Quick Icon-based Management (Rename / Delete) Row
        mgmt_layout = QHBoxLayout()
        mgmt_layout.setSpacing(6)

        self.btn_rename = QPushButton("✏ Rename")
        self.btn_rename.setToolTip("Rename selected conversation")
        self.btn_rename.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rename.setStyleSheet("""
            QPushButton {
                background-color: #0d1526;
                color: #94a3b8;
                border: 1px solid #1a273f;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #132038;
                color: #f1f5f9;
                border-color: #0284c7;
            }
        """)
        self.btn_rename.clicked.connect(self._on_rename_clicked)
        mgmt_layout.addWidget(self.btn_rename, stretch=1)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setToolTip("Delete selected conversation")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #1c0e12;
                color: #f87171;
                border: 1px solid #3b1419;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2b1217;
                color: #fca5a5;
                border-color: #ef4444;
            }
        """)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        mgmt_layout.addWidget(self.btn_delete, stretch=1)

        layout.addLayout(mgmt_layout)

        # 7. Navigation Row: Privacy / Help Links (compact)
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(4)

        self.btn_privacy_nav = QPushButton("🔒 Privacy")
        self.btn_privacy_nav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_privacy_nav.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: none;
                font-size: 11px;
                font-weight: 500;
                padding: 4px 6px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0e1627;
                color: #cbd5e1;
            }
        """)
        self.btn_privacy_nav.clicked.connect(self.privacy_requested.emit)
        nav_layout.addWidget(self.btn_privacy_nav)

        self.btn_help_nav = QPushButton("❓ Help")
        self.btn_help_nav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help_nav.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: none;
                font-size: 11px;
                font-weight: 500;
                padding: 4px 6px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0e1627;
                color: #cbd5e1;
            }
        """)
        self.btn_help_nav.clicked.connect(self.help_requested.emit)
        nav_layout.addWidget(self.btn_help_nav)

        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        # 8. User Profile Card at Very Bottom (Matching Image 5)
        self.profile_card = QFrame()
        self.profile_card.setObjectName("UserProfileCard")
        self.profile_card.setStyleSheet("""
            QFrame#UserProfileCard {
                background-color: #0c121e;
                border: 1px solid #151c28;
                border-radius: 12px;
                padding: 6px 10px;
            }
            QFrame#UserProfileCard:hover {
                border-color: #1a283e;
                background-color: #0e1626;
            }
        """)
        profile_layout = QHBoxLayout(self.profile_card)
        profile_layout.setContentsMargins(6, 6, 6, 6)
        profile_layout.setSpacing(10)

        # Avatar circle
        self.lbl_avatar = QLabel("D")
        self.lbl_avatar.setFixedSize(32, 32)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font_av = QFont()
        font_av.setPointSize(12)
        font_av.setBold(True)
        self.lbl_avatar.setFont(font_av)
        self.lbl_avatar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0284c7, stop:1 #38bdf8);
            color: #ffffff;
            border-radius: 16px;
            font-weight: bold;
        """)
        profile_layout.addWidget(self.lbl_avatar)

        # User details column
        user_vbox = QVBoxLayout()
        user_vbox.setContentsMargins(0, 0, 0, 0)
        user_vbox.setSpacing(2)

        self.lbl_user_name = QLabel(self._user_name)
        font_name = QFont()
        font_name.setPointSize(11)
        font_name.setBold(True)
        self.lbl_user_name.setFont(font_name)
        self.lbl_user_name.setStyleSheet("color: #f1f5f9;")
        user_vbox.addWidget(self.lbl_user_name)

        lbl_vault_sub = QLabel("🔒 Local Vault • Private")
        lbl_vault_sub.setStyleSheet("color: #64748b; font-size: 10px;")
        user_vbox.addWidget(lbl_vault_sub)

        profile_layout.addLayout(user_vbox, stretch=1)

        # Action icon button: Lock Vault
        self.btn_lock_nav = QPushButton("🔒")
        self.btn_lock_nav.setToolTip("Lock Private Vault (Ctrl+L)")
        self.btn_lock_nav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lock_nav.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid #1e2d4a;
                border-radius: 6px;
                font-size: 12px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #38bdf8;
                border-color: #0284c7;
            }
        """)
        self.btn_lock_nav.clicked.connect(self.lock_vault_requested.emit)
        profile_layout.addWidget(self.btn_lock_nav)

        # Action icon button: Settings
        self.btn_settings_nav = QPushButton("⚙")
        self.btn_settings_nav.setToolTip("Open Settings")
        self.btn_settings_nav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings_nav.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid #1e2d4a;
                border-radius: 6px;
                font-size: 12px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #38bdf8;
                border-color: #0284c7;
            }
        """)
        self.btn_settings_nav.clicked.connect(self.settings_requested.emit)
        profile_layout.addWidget(self.btn_settings_nav)

        layout.addWidget(self.profile_card)

    def _on_search_changed(self, text: str) -> None:
        """Filter visible conversation items matching query text."""
        query = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item is not None:
                title = item.text().lower()
                item.setHidden(bool(query and query not in title))

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

        action_rename = QAction("✏ Rename", self)
        action_rename.triggered.connect(self._on_rename_clicked)
        menu.addAction(action_rename)

        action_export_md = QAction("⤓ Export to Markdown (.md)...", self)
        action_export_md.triggered.connect(lambda: self.export_chat_requested.emit(chat_id, "markdown"))
        menu.addAction(action_export_md)

        action_export_txt = QAction("⤓ Export to Plain Text (.txt)...", self)
        action_export_txt.triggered.connect(lambda: self.export_chat_requested.emit(chat_id, "txt"))
        menu.addAction(action_export_txt)

        menu.addSeparator()

        action_delete = QAction("🗑 Delete", self)
        action_delete.triggered.connect(self._on_delete_clicked)
        menu.addAction(action_delete)

        menu.exec(self.list_widget.mapToGlobal(position))
