"""Локальный прогресс: галочки, звёзды, статусы книг, метки."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuthorProgress:
    acquainted: bool = False
    stars: int = 0
    note: str = ""


@dataclass
class BookProgress:
    status: str = "planned"
    note: str = ""


@dataclass
class Marker:
    id: int
    x: float
    y: float
    icon: str
    label: str


class ProgressDB:
    def __init__(self, path: Path) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS author_progress (
                author_id TEXT PRIMARY KEY,
                acquainted INTEGER NOT NULL DEFAULT 0,
                stars INTEGER NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS book_progress (
                book_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'planned',
                note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS markers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                x REAL NOT NULL,
                y REAL NOT NULL,
                icon TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT ''
            );
            """
        )
        self.conn.commit()

    def author(self, author_id: str) -> AuthorProgress:
        row = self.conn.execute(
            "SELECT acquainted, stars, note FROM author_progress WHERE author_id = ?",
            (author_id,),
        ).fetchone()
        if row is None:
            return AuthorProgress()
        return AuthorProgress(bool(row["acquainted"]), int(row["stars"]), row["note"])

    def set_author(
        self,
        author_id: str,
        acquainted: bool | None = None,
        stars: int | None = None,
        note: str | None = None,
    ) -> AuthorProgress:
        current = self.author(author_id)
        if acquainted is not None:
            current.acquainted = acquainted
        if stars is not None:
            current.stars = max(0, min(3, int(stars)))
        if note is not None:
            current.note = note
        self.conn.execute(
            """
            INSERT INTO author_progress (author_id, acquainted, stars, note)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(author_id) DO UPDATE SET
                acquainted = excluded.acquainted,
                stars = excluded.stars,
                note = excluded.note
            """,
            (author_id, int(current.acquainted), current.stars, current.note),
        )
        self.conn.commit()
        return current

    def book(self, book_id: str) -> BookProgress:
        row = self.conn.execute(
            "SELECT status, note FROM book_progress WHERE book_id = ?",
            (book_id,),
        ).fetchone()
        if row is None:
            return BookProgress()
        return BookProgress(row["status"], row["note"])

    def set_book(self, book_id: str, status: str | None = None, note: str | None = None) -> BookProgress:
        current = self.book(book_id)
        if status is not None:
            if status not in ("planned", "reading", "done"):
                status = "planned"
            current.status = status
        if note is not None:
            current.note = note
        self.conn.execute(
            """
            INSERT INTO book_progress (book_id, status, note)
            VALUES (?, ?, ?)
            ON CONFLICT(book_id) DO UPDATE SET
                status = excluded.status,
                note = excluded.note
            """,
            (book_id, current.status, current.note),
        )
        self.conn.commit()
        return current

    def done_count(self, book_ids: list[str]) -> int:
        if not book_ids:
            return 0
        marks = ",".join("?" for _ in book_ids)
        row = self.conn.execute(
            f"SELECT COUNT(*) AS n FROM book_progress WHERE status = 'done' AND book_id IN ({marks})",
            book_ids,
        ).fetchone()
        return int(row["n"])

    def acquainted_count(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM author_progress WHERE acquainted = 1"
        ).fetchone()
        return int(row["n"])

    def done_books_total(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM book_progress WHERE status = 'done'"
        ).fetchone()
        return int(row["n"])

    def markers(self) -> list[Marker]:
        rows = self.conn.execute(
            "SELECT id, x, y, icon, label FROM markers ORDER BY id"
        ).fetchall()
        return [Marker(int(r["id"]), r["x"], r["y"], r["icon"], r["label"]) for r in rows]

    def add_marker(self, x: float, y: float, icon: str, label: str = "") -> Marker:
        cur = self.conn.execute(
            "INSERT INTO markers (x, y, icon, label) VALUES (?, ?, ?, ?)",
            (x, y, icon, label),
        )
        self.conn.commit()
        return Marker(int(cur.lastrowid), x, y, icon, label)

    def delete_marker(self, marker_id: int) -> None:
        self.conn.execute("DELETE FROM markers WHERE id = ?", (marker_id,))
        self.conn.commit()
