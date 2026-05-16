import json
import sys

import pytest

import session_view as sv


def test_load_events_skips_malformed_lines(tmp_path, capsys):
    path = tmp_path / "events.jsonl"
    path.write_text(
        '{"type":"user.message","data":{"content":"ok"}}\n'
        'not json\n'
        '{"type":"assistant.message","data":{"content":"done"}}\n',
        encoding="utf-8",
    )

    events = sv.load_events(str(path))

    assert len(events) == 2
    assert events[0]["type"] == "user.message"
    assert "Warning: skipping malformed line 2" in capsys.readouterr().err


def test_build_overview_html_embeds_search_payload_and_filters_internal_story_sessions():
    html = sv.build_overview_html(
        [
            {
                "id": "rich-session",
                "events_html": "/tmp/rich/events.html",
                "start_time": "2026-05-16T10:00:00Z",
                "cwd": "/tmp/example/project",
                "first_prompt": "Render the session nicely",
                "search_text": "reasoning text and assistant reply",
                "model": "gpt-5.4",
                "user_prompt_count": 1,
                "intent_count": 1,
                "has_story": True,
                "total_premium_requests": 2,
                "model_metrics": {},
                "summary": "Merged summary",
            },
            {
                "id": "internal-story",
                "events_html": "/tmp/internal/events.html",
                "start_time": "2026-05-16T10:00:00Z",
                "cwd": "/tmp/example/project",
                "first_prompt": "Read the Copilot session below and write a text in English",
                "search_text": "internal story prompt",
                "model": "gpt-5.4",
                "user_prompt_count": 1,
                "intent_count": 0,
                "has_story": False,
                "total_premium_requests": 0,
                "model_metrics": {},
                "summary": "",
            },
        ]
    )

    assert "reasoning text and assistant reply" in html
    assert "Render the session nicely" in html
    assert "Read the Copilot session below" not in html
    assert "url.searchParams.set('q', value);" in html


def test_main_resolves_bare_session_id_and_writes_html(rich_session_dir, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["session_view.py", "rich-session"])

    sv.main()

    html = (rich_session_dir / "events.html").read_text(encoding="utf-8")
    assert "Render the session nicely" in html
    assert "Rendering session view" in html
    assert "The explore agent inspected the rendering path." in html


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["-l", "Swedish", "INPUT"], "-l/--language"),
        (["--force", "INPUT"], "-f/--force"),
        (["--story"], "--story is not valid in batch mode."),
    ],
)
def test_main_rejects_invalid_flag_combinations(rich_session_dir, monkeypatch, capsys, argv, expected):
    resolved = [
        str(rich_session_dir / "events.jsonl") if value == "INPUT" else value
        for value in argv
    ]
    monkeypatch.setattr(sys, "argv", ["session_view.py", *resolved])

    with pytest.raises(SystemExit) as exc:
        sv.main()

    assert exc.value.code == 1
    assert expected in capsys.readouterr().err


def test_main_batch_mode_skips_up_to_date_outputs(write_session_fixture, monkeypatch, capsys):
    session_dir = write_session_fixture("rich-session.jsonl", session_id="rich-session")
    input_path = session_dir / "events.jsonl"
    output_path = session_dir / "events.html"
    output_path.write_text("already rendered", encoding="utf-8")

    input_mtime = input_path.stat().st_mtime
    output_mtime = input_mtime + 100
    monkeypatch.setattr(sv, "_effective_source_mtime", lambda: 0)
    monkeypatch.setattr(sys, "argv", ["session_view.py"])

    output_path.touch()
    import os

    os.utime(output_path, (output_mtime, output_mtime))

    sv.main()

    captured = capsys.readouterr()
    assert "Done: 0 written, 1 skipped." in captured.out
    assert not sv._overview_output_path().exists()


def test_main_batch_mode_generates_overview_and_filters_internal_story_sessions(
    write_session_fixture,
    monkeypatch,
):
    rich_session_dir = write_session_fixture("rich-session.jsonl", session_id="rich-session")
    write_session_fixture("internal-story-session.jsonl", session_id="internal-story-session")
    monkeypatch.setattr(sys, "argv", ["session_view.py"])

    sv.main()

    assert (rich_session_dir / "events.html").exists()
    overview_html = sv._overview_output_path().read_text(encoding="utf-8")
    assert "Render the session nicely" in overview_html
    assert "Read the Copilot session below" not in overview_html


def test_generate_overview_merges_json_and_db_summaries(
    rich_session_dir,
    isolated_home,
    create_session_store_db,
):
    (rich_session_dir / "events.html").write_text("<html></html>", encoding="utf-8")
    summaries_path = isolated_home / ".copilot" / "session-summaries.json"
    summaries_path.write_text(json.dumps({"rich-session": "Saved summary"}), encoding="utf-8")
    create_session_store_db({"rich-session": "DB summary", "other-session": "Extra summary"})

    sv.generate_overview()

    overview_html = sv._overview_output_path().read_text(encoding="utf-8")
    persisted = json.loads(summaries_path.read_text(encoding="utf-8"))

    assert "DB summary" in overview_html
    assert "Saved summary" not in overview_html
    assert persisted["rich-session"] == "DB summary"
    assert persisted["other-session"] == "Extra summary"
