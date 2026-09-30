"""Security scanner and sensitive file filter for Sarthika Code.

Blocks dangerous, credential-bearing, binary, and archive files by default.
Ensures zero-cloud, local-first safety invariants before any file content enters prompt context.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

# Blocked filename patterns (case-insensitive)
BLOCKED_FILENAME_PATTERNS = [
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.rar",
    "*.7z",
    "*.bz2",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.bin",
    "id_rsa",
    "id_rsa.*",
    "id_dsa",
    "id_dsa.*",
    "id_ecdsa",
    "id_ecdsa.*",
    "id_ed25519",
    "id_ed25519.*",
]

# Blocked exact base names or substrings (case-insensitive)
BLOCKED_NAME_KEYWORDS = [
    "credential",
    "credentials",
    "secret",
    "secrets",
    "token",
    "tokens",
]

# Blocked path directory segments (case-insensitive)
BLOCKED_PATH_SEGMENTS = {
    "node_modules",
    "vendor",
    ".git",
    ".ssh",
    "__pycache__",
    ".svn",
    ".hg",
}

# Maximum allowed file size for read-only context (500 KB limit to prevent OOM/context exhaustion)
MAX_FILE_SIZE_BYTES = 512 * 1024


@dataclass(frozen=True)
class FileFilterResult:
    """Outcome of sensitive file evaluation."""

    is_safe: bool
    reason: str | None = None
    category: str = "safe"


class SensitiveFileFilter:
    """Enforces strict, non-bypassable security checks on user-selected files."""

    @staticmethod
    def detect_language(path: Path) -> str:
        """Detect language identifier from file extension, falling back to 'text'."""
        return detect_language(path)

    @classmethod
    def evaluate_file(cls, path: Path) -> FileFilterResult:
        """Scan file path and contents against security blacklist.

        Args:
            path: Target file path to inspect.

        Returns:
            FileFilterResult indicating whether file is safe or reason for rejection.
        """
        # 1. Existence and type verification
        if not path.exists():
            return FileFilterResult(
                is_safe=False,
                reason=f"File does not exist: {path.name}",
                category="not_found",
            )

        if not path.is_file():
            return FileFilterResult(
                is_safe=False,
                reason=f"Path is not a regular file: {path.name}",
                category="not_a_file",
            )

        filename_lower = path.name.lower()

        # 2. Check blocked filename patterns
        for pattern in BLOCKED_FILENAME_PATTERNS:
            if fnmatch.fnmatch(filename_lower, pattern.lower()):
                return FileFilterResult(
                    is_safe=False,
                    reason=f"Matches restricted file pattern '{pattern}': sensitive file",
                    category="restricted_pattern",
                )

        # 3. Check blocked keywords in filename stem
        stem_lower = path.stem.lower()
        parts = stem_lower.replace("-", "_").replace(".", "_").split("_")
        for kw in BLOCKED_NAME_KEYWORDS:
            if kw in parts or filename_lower == kw:
                return FileFilterResult(
                    is_safe=False,
                    reason=f"Filename contains sensitive keyword '{kw}' (possible secret or credential)",
                    category="sensitive_keyword",
                )

        # 4. Check forbidden directory path segments
        resolved_parts = [p.lower() for p in path.resolve().parts]
        for seg in BLOCKED_PATH_SEGMENTS:
            if seg in resolved_parts:
                return FileFilterResult(
                    is_safe=False,
                    reason=f"File resides inside restricted directory '{seg}'",
                    category="restricted_directory",
                )

        # 5. Check file size threshold
        try:
            size = path.stat().st_size
            if size > MAX_FILE_SIZE_BYTES:
                return FileFilterResult(
                    is_safe=False,
                    reason=f"File size ({size // 1024} KB) exceeds the maximum safe limit ({MAX_FILE_SIZE_BYTES // 1024} KB)",
                    category="file_too_large",
                )
        except OSError as e:
            return FileFilterResult(
                is_safe=False,
                reason=f"Failed to access file attributes: {e}",
                category="io_error",
            )

        # 6. Binary content detection
        if cls.is_binary_file(path):
            return FileFilterResult(
                is_safe=False,
                reason="File appears to be binary or contains non-text/null bytes",
                category="binary_file",
            )

        return FileFilterResult(is_safe=True)

    @classmethod
    def is_binary_file(cls, path: Path) -> bool:
        """Inspect the initial chunk of the file for null bytes and non-text characters."""
        try:
            with open(path, "rb") as f:
                chunk = f.read(4096)
                if not chunk:
                    return False  # Empty file is treated as text
                # Null byte is a definitive binary indicator
                if b"\x00" in chunk:
                    return True
                # Attempt decoding as UTF-8
                try:
                    text = chunk.decode("utf-8")
                except UnicodeDecodeError:
                    return True
                # Check ratio of non-printable control characters (excluding newline, tab, carriage return)
                non_printable = sum(1 for ch in text if ord(ch) < 32 and ch not in ("\n", "\r", "\t"))
                return len(text) > 0 and (non_printable / len(text)) > 0.2
        except Exception:
            return True


# Supported programming languages mapped from extensions
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".php": "php",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".json": "json",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".md": "markdown",
    ".txt": "text",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".xml": "xml",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
}


def detect_language(path: Path) -> str:
    """Detect language identifier from file extension, falling back to 'text'."""
    ext = path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "text")
