"""Database engine and session management for Sarthika Code.

Provides SQLite initialization, foreign key pragma enforcement, WAL journal mode,
and session context managers using SQLAlchemy 2.0.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from sarthika_code.domain.errors import PersistenceError
from sarthika_code.storage.models import Base


def _set_sqlite_pragmas(dbapi_connection: object, connection_record: object) -> None:
    """Enforce SQLite foreign key constraints and fast WAL journaling."""
    cursor = getattr(dbapi_connection, "cursor", None)
    if cursor is not None:
        c = cursor()
        c.execute("PRAGMA foreign_keys = ON;")
        c.execute("PRAGMA journal_mode = WAL;")
        c.close()


class DatabaseManager:
    """Manages SQLite engine lifecycle and SQLAlchemy 2.0 sessions."""

    def __init__(self, db_path: Path | str) -> None:
        if str(db_path) == ":memory:":
            self.database_url = "sqlite:///:memory:"
        else:
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.database_url = f"sqlite:///{path.resolve()}"

        self.engine: Engine = create_engine(
            self.database_url,
            echo=False,
            future=True,
        )

        # Enforce foreign key constraints in SQLite
        event.listen(self.engine, "connect", _set_sqlite_pragmas)

        self._session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            class_=Session,
        )

    def init_db(self) -> None:
        """Create all tables defined in Base metadata if they do not exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            raise PersistenceError(
                message=f"Failed to initialize database schema: {e}",
                user_guidance="Check that the database directory is writable and not locked by another process.",
                details=str(e),
            ) from e

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional session scope for database operations."""
        sess: Session = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception as e:
            sess.rollback()
            if isinstance(e, PersistenceError):
                raise
            raise PersistenceError(
                message=f"Database transaction failed: {e}",
                user_guidance="Ensure database integrity and permissions are intact.",
                details=str(e),
            ) from e
        finally:
            sess.close()

    def close(self) -> None:
        """Dispose of the database engine connections."""
        self.engine.dispose()
