"""Lightweight syntax highlighter for Sarthika Code's dedicated code editor.

Provides fast, regex-based highlighting for common programming languages using PySide6's
built-in QSyntaxHighlighter without any third-party IDE dependencies.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

# Common keywords by language
KEYWORDS: dict[str, list[str]] = {
    "python": [
        "and", "as", "assert", "async", "await", "break", "class", "continue",
        "def", "del", "elif", "else", "except", "finally", "for", "from",
        "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
        "or", "pass", "raise", "return", "try", "while", "with", "yield",
        "True", "False", "None",
    ],
    "php": [
        "abstract", "and", "array", "as", "break", "case", "catch", "class",
        "clone", "const", "continue", "declare", "default", "do", "else",
        "elseif", "endfor", "endforeach", "endif", "endswitch", "endwhile",
        "extends", "final", "finally", "fn", "for", "foreach", "function",
        "global", "if", "implements", "include", "include_once", "instanceof",
        "interface", "match", "namespace", "new", "or", "private", "protected",
        "public", "readonly", "require", "require_once", "return", "static",
        "switch", "throw", "trait", "try", "use", "var", "while", "yield",
    ],
    "javascript": [
        "async", "await", "break", "case", "catch", "class", "const", "continue",
        "debugger", "default", "delete", "do", "else", "export", "extends",
        "finally", "for", "function", "if", "import", "in", "instanceof",
        "let", "new", "return", "super", "switch", "this", "throw", "try",
        "typeof", "var", "void", "while", "with", "yield", "null", "undefined",
        "true", "false",
    ],
    "typescript": [
        "async", "await", "break", "case", "catch", "class", "const", "continue",
        "debugger", "default", "delete", "do", "else", "enum", "export", "extends",
        "finally", "for", "function", "if", "implements", "import", "in",
        "instanceof", "interface", "let", "new", "package", "private", "protected",
        "public", "return", "super", "switch", "this", "throw", "try", "type",
        "typeof", "var", "void", "while", "with", "yield", "null", "undefined",
        "true", "false", "any", "number", "string", "boolean", "never", "unknown",
    ],
    "sql": [
        "SELECT", "FROM", "WHERE", "INSERT", "INTO", "UPDATE", "DELETE",
        "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "ON", "GROUP",
        "BY", "HAVING", "ORDER", "ASC", "DESC", "LIMIT", "OFFSET", "UNION",
        "ALL", "CREATE", "TABLE", "DROP", "ALTER", "INDEX", "PRIMARY", "KEY",
        "FOREIGN", "REFERENCES", "NULL", "NOT", "AND", "OR", "IN", "LIKE",
        "BETWEEN", "IS", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END",
        "AS", "COUNT", "SUM", "AVG", "MIN", "MAX", "DISTINCT", "VALUES",
    ],
    "bash": [
        "if", "then", "else", "elif", "fi", "case", "esac", "for", "select",
        "while", "until", "do", "done", "in", "function", "time", "return",
        "exit", "echo", "export", "source", "alias", "local", "readonly",
    ],
    "json": [
        "true", "false", "null",
    ],
    "html": [
        "html", "head", "body", "div", "span", "p", "a", "button", "input",
        "form", "table", "tr", "td", "th", "ul", "ol", "li", "h1", "h2",
        "h3", "h4", "h5", "h6", "script", "style", "link", "meta", "title",
    ],
    "css": [
        "color", "background", "margin", "padding", "border", "font", "display",
        "flex", "grid", "position", "width", "height", "top", "left", "right",
        "bottom", "overflow", "cursor", "transition", "transform", "opacity",
    ],
}


class CodeSyntaxHighlighter(QSyntaxHighlighter):
    """Clean, lightweight regex-driven syntax highlighter."""

    def __init__(self, parent: QTextDocument, language: str = "python") -> None:
        super().__init__(parent)
        self.language = language.lower()
        self._highlighting_rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._init_formats()
        self._build_rules()

    def _init_formats(self) -> None:
        # Keyword format (blue/cyan)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#38bdf8"))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        # String format (green)
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#4ade80"))

        # Comment format (gray/italic)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#64748b"))
        self.comment_format.setFontItalic(True)

        # Number format (amber)
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#fbbf24"))

    def set_language(self, language: str) -> None:
        """Update active language and re-highlight document."""
        self.language = language.lower()
        self._build_rules()
        self.rehighlight()

    def _build_rules(self) -> None:
        self._highlighting_rules.clear()

        # 1. Keywords
        words = KEYWORDS.get(self.language, [])
        for word in words:
            pattern = QRegularExpression(rf"\b{re.escape(word)}\b")
            self._highlighting_rules.append((pattern, self.keyword_format))

        # 2. Numbers
        num_pattern = QRegularExpression(r"\b[0-9]+(\.[0-9]+)?\b")
        self._highlighting_rules.append((num_pattern, self.number_format))

        # 3. Double-quoted strings
        self._highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.string_format))

        # 4. Single-quoted strings
        self._highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), self.string_format))

        # 5. Comments
        if self.language in ("python", "bash"):
            self._highlighting_rules.append((QRegularExpression(r"#.*"), self.comment_format))
        elif self.language in ("javascript", "typescript", "php"):
            self._highlighting_rules.append((QRegularExpression(r"//.*"), self.comment_format))
        elif self.language == "sql":
            self._highlighting_rules.append((QRegularExpression(r"--.*"), self.comment_format))
        elif self.language in ("html", "css"):
            self._highlighting_rules.append((QRegularExpression(r"<!--.*-->"), self.comment_format))

    def highlightBlock(self, text: str) -> None:
        """Apply formatting to the text block."""
        for pattern, fmt in self._highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
