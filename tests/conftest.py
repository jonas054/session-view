import json
import sqlite3
from pathlib import Path

import pytest

import session_view


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _read_jsonl_fixture(name: str) -> list[dict]:
    path = FIXTURES_DIR / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture
def read_jsonl_fixture():
    return _read_jsonl_fixture


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def isolated_home(monkeypatch, tmp_path) -> Path:
    home = tmp_path / "home"
    (home / ".copilot" / "session-state").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(session_view, "_home_dir", lambda: home)
    return home


@pytest.fixture
def write_session_fixture(isolated_home):
    def _write(name: str, session_id: str | None = None) -> Path:
        session_dir = isolated_home / ".copilot" / "session-state" / (session_id or Path(name).stem)
        session_dir.mkdir(parents=True, exist_ok=True)
        session_dir.joinpath("events.jsonl").write_text(
            (FIXTURES_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return session_dir

    return _write


@pytest.fixture
def rich_events(read_jsonl_fixture):
    return read_jsonl_fixture("rich-session.jsonl")


@pytest.fixture
def rich_session_dir(write_session_fixture) -> Path:
    return write_session_fixture("rich-session.jsonl", session_id="rich-session")


@pytest.fixture
def ask_user_session_dir(write_session_fixture) -> Path:
    return write_session_fixture("ask-user-session.jsonl", session_id="ask-user-session")


@pytest.fixture
def create_session_store_db(isolated_home):
    def _create(rows: dict[str, str]) -> Path:
        db_path = isolated_home / ".copilot" / "session-store.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, summary TEXT)")
            conn.executemany(
                "INSERT INTO sessions (id, summary) VALUES (?, ?)",
                list(rows.items()),
            )
            conn.commit()
        finally:
            conn.close()
        return db_path

    return _create
