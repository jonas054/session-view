import json

import session_view as sv


def test_build_overview_tracks_metrics_and_excludes_report_intent_from_tools_used(rich_events):
    overview = sv.build_overview(rich_events)

    assert overview["session_id"] == "rich-session"
    assert overview["copilot_version"] == "1.0.48"
    assert overview["duration_ms"] == 10000
    assert overview["tools_used"] == {"bash": 1}
    assert overview["intents"] == ["Rendering session view"]
    assert overview["lines_added"] == 12
    assert overview["lines_removed"] == 3
    assert overview["total_premium_requests"] == 2


def test_build_overview_excludes_empty_and_skill_context_user_messages():
    events = [
        {"type": "user.message", "data": {"content": "Keep this message"}},
        {"type": "user.message", "data": {"content": ""}},
        {"type": "user.message", "data": {"content": " \n\t "}},
        {
            "type": "user.message",
            "data": {"content": '\n<skill-context name="example">\ninternal context\n</skill-context>'},
        },
        {
            "type": "user.message",
            "data": {"content": "<system_reminder>\ninternal reminder\n</system_reminder>"},
        },
        {"type": "user.message", "data": {"content": "Keep this one too"}},
    ]

    overview = sv.build_overview(events)
    html = sv.render_overview(overview)

    assert overview["user_messages"] == ["Keep this message", "Keep this one too"]
    assert html.count('class="user-msg-summary"') == 2
    assert "skill-context" not in html


def test_build_turns_treats_commentary_phase_as_reasoning():
    events = [
        {"id": "ev-1", "timestamp": "2026-01-01T10:00:00Z", "type": "user.message",
         "data": {"content": "Do something", "interactionId": "int-1"}},
        {"id": "ev-2", "timestamp": "2026-01-01T10:00:01Z", "type": "assistant.message",
         "data": {"phase": "commentary", "content": "I'll read the file first.", "toolRequests": [],
                  "encryptedContent": "abc123", "model": "gpt-5.4"}},
        {"id": "ev-3", "timestamp": "2026-01-01T10:00:02Z", "type": "assistant.message",
         "data": {"phase": "final_answer", "content": "Done!", "toolRequests": [],
                  "encryptedContent": "def456", "model": "gpt-5.4"}},
    ]

    turns = sv.build_turns(events)

    assert len(turns) == 1
    kinds = [step["kind"] for step in turns[0]["steps"]]
    assert kinds == ["reasoning", "text"]
    assert turns[0]["steps"][0]["content"] == "I'll read the file first."
    assert turns[0]["steps"][1]["content"] == "Done!"


def test_render_turns_hides_empty_user_messages():
    events = [
        {"id": "ev-1", "timestamp": "2026-01-01T10:00:00Z", "type": "user.message",
         "data": {"content": "Hello", "interactionId": "int-1"}},
        {"id": "ev-2", "timestamp": "2026-01-01T10:00:01Z", "type": "assistant.message",
         "data": {"content": "Hi there!", "toolRequests": [], "model": "claude-sonnet-4.6"}},
        {"id": "ev-3", "timestamp": "2026-01-01T10:00:02Z", "type": "user.message",
         "data": {"content": "", "interactionId": "int-2"}},
        {"id": "ev-4", "timestamp": "2026-01-01T10:00:03Z", "type": "assistant.message",
         "data": {"content": "Still here.", "toolRequests": [], "model": "claude-sonnet-4.6"}},
    ]
    turns = sv.build_turns(events)
    html = sv.render_turns(turns)

    assert "Hello" in html
    assert html.count("user-bubble") == 1
    assert "Still here" in html


def test_render_turns_hides_system_reminder_user_messages():
    events = [
        {"id": "ev-1", "timestamp": "2026-01-01T10:00:00Z", "type": "user.message",
         "data": {"content": "Hello", "interactionId": "int-1"}},
        {"id": "ev-2", "timestamp": "2026-01-01T10:00:01Z", "type": "assistant.message",
         "data": {"content": "Hi there!", "toolRequests": [], "model": "claude-sonnet-4.6"}},
        {"id": "ev-3", "timestamp": "2026-01-01T10:00:02Z", "type": "user.message",
         "data": {"content": "<system_reminder>\n<sql_tables>Available tables: todos</sql_tables>\n</system_reminder>",
                  "interactionId": "int-2"}},
        {"id": "ev-4", "timestamp": "2026-01-01T10:00:03Z", "type": "assistant.message",
         "data": {"content": "Follow-up reply.", "toolRequests": [], "model": "claude-sonnet-4.6"}},
    ]
    turns = sv.build_turns(events)
    html = sv.render_turns(turns)

    assert "Hello" in html
    assert "system_reminder" not in html
    assert "sql_tables" not in html
    assert "Follow-up reply" in html


def test_build_turns_reconstructs_reasoning_intent_tool_and_subagent_steps(rich_events):
    turns = sv.build_turns(rich_events)

    assert len(turns) == 1
    assert turns[0]["user_message"]["content"] == "Render the session nicely"
    assert [step["kind"] for step in turns[0]["steps"]] == [
        "reasoning",
        "text",
        "intent",
        "tool",
        "text",
        "subagent",
    ]
    assert turns[0]["steps"][2]["content"] == "Rendering session view"
    assert turns[0]["steps"][3]["name"] == "bash"
    assert turns[0]["steps"][3]["result"]["content"].startswith("diff --git")
    assert turns[0]["steps"][5]["name"] == "Explore Agent"
    assert "Session rendering path" in turns[0]["steps"][5]["result"]["content"]


def test_read_session_collects_search_text_and_intent_count(rich_session_dir):
    (rich_session_dir / "story.txt").write_text("Story generated by test\n\nChapter 1", encoding="utf-8")

    info = sv.read_session(rich_session_dir)

    assert info["has_story"] is True
    assert info["model"] == "gpt-5.4"
    assert info["user_prompt_count"] == 1
    assert info["intent_count"] == 1
    assert info["first_prompt"] == "Render the session nicely"
    assert "**Plan**: inspect rendered output." in info["search_text"]
    assert "Rendering session view" in info["search_text"]
    assert info["search_fields"]["prompts"] == "Render the session nicely"
    assert "**Plan**: inspect rendered output." in info["search_fields"]["reasoning"]
    assert "The explore agent inspected the rendering path." in info["search_fields"]["replies"]
    assert "Rendering session view" in info["search_fields"]["intents"]
    assert "git --no-pager status" in info["search_fields"]["tools"]
    assert "Explore Agent" in info["search_fields"]["tools"]
    assert "report_intent" not in info["search_fields"]["tools"]
    assert info["search_fields"]["directory"] == "/tmp/example/project"
    assert info["search_fields"]["model"] == "gpt-5.4"
    assert "Story generated by test" in info["search_fields"]["story"]


def test_read_session_indexes_ask_user_questions_choices_and_answers(ask_user_session_dir):
    info = sv.read_session(ask_user_session_dir)

    assert "Which view should I show?" in info["search_text"]
    assert "Show recent git commits" in info["search_text"]
    assert "Show file diffs (Recommended)" in info["search_text"]
    assert "Which view should I show?" in info["search_fields"]["prompts"]
    assert "Show file diffs (Recommended)" in info["search_fields"]["prompts"]


def test_search_text_caps_large_tool_payloads():
    text = "head " + ("x" * 9000) + " tail"

    capped = sv._cap_search_text(text)

    assert len(capped) <= sv.SEARCH_TEXT_LIMIT
    assert capped.startswith("head ")
    assert capped.endswith(" tail")
    assert "[truncated]" in capped


def test_read_session_keeps_full_prompt_and_response_search_text(write_session_fixture):
    session_dir = write_session_fixture("rich-session.jsonl", session_id="search-full-text")
    tail_prompt = "Tail prompt " + " ".join(["user"] * 180)
    tail_response = "Tail response " + " ".join(["copilot"] * 180)

    with (session_dir / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "id": "ev-13",
                    "timestamp": "2026-05-16T10:00:11Z",
                    "type": "user.message",
                    "data": {"content": tail_prompt, "interactionId": "int-2"},
                }
            )
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "id": "ev-14",
                    "timestamp": "2026-05-16T10:00:12Z",
                    "type": "assistant.message",
                    "data": {"content": tail_response},
                }
            )
            + "\n"
        )

    info = sv.read_session(session_dir)

    assert tail_prompt in info["search_text"]
    assert tail_response in info["search_text"]


def test_process_file_renders_story_tab_a11y_and_query_hooks(rich_session_dir, tmp_path):
    (rich_session_dir / "story.txt").write_text(
        "Story generated by test\n\nFirst chapter\n\nSecond chapter",
        encoding="utf-8",
    )
    output_path = tmp_path / "events.html"

    sv.process_file(
        str(rich_session_dir / "events.jsonl"),
        str(output_path),
        a11y=True,
        story=False,
    )

    html = output_path.read_text(encoding="utf-8")

    assert "📖 Story" in html
    assert '<p class="md-h5">Story generated by test</p>' in html
    assert '<p class="story-p">First chapter</p>' in html
    assert ".story-body .story-p {" in sv.CSS
    assert sv.CSS_A11Y.strip() in html
    assert 'class="back-link"' in html
    assert "url.searchParams.set('q', query);" in html


def test_process_file_marks_searchable_session_fields(rich_session_dir, tmp_path):
    (rich_session_dir / "story.txt").write_text("Story generated by test", encoding="utf-8")
    output_path = tmp_path / "events.html"

    sv.process_file(
        str(rich_session_dir / "events.jsonl"),
        str(output_path),
        story=False,
    )

    html = output_path.read_text(encoding="utf-8")

    assert 'data-search-field="prompts"' in html
    assert 'data-search-field="replies"' in html
    assert 'data-search-field="reasoning"' in html
    assert 'data-search-field="intents"' in html
    assert 'data-search-field="tools"' in html
    assert 'data-search-field="directory"' in html
    assert 'data-search-field="model"' in html
    assert 'data-search-field="story"' in html


def test_render_args_and_results_handle_sql_apply_patch_line_numbers_and_diff():
    sql_html = sv.render_args(
        {"description": "Query sessions", "query": "SELECT 'x' FROM SESSIONS"},
        "sql",
    )
    patch_html = sv.render_args(
        "*** Begin Patch\n*** Add File: demo.txt\n+hello\n*** End Patch\n",
        "apply_patch",
    )
    numbered_html = sv.render_tool_result({"content": "1. alpha\n2. beta\n"}, "view")
    diff_html = sv.render_tool_result(
        {"content": "diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-old\n+new\n"},
        "bash",
    )

    assert "sql-block" in sql_html
    assert "sql-kw" in sql_html
    assert 'class="diff-meta"' in patch_html
    assert 'class="line-num"' in numbered_html
    assert 'class="diff-add"' in diff_html
    assert 'class="diff-del"' in diff_html


def test_render_args_formats_bulk_insert_sql_as_table():
    html = sv.render_args(
        {
            "description": "Insert todo rows",
            "query": (
                "INSERT OR REPLACE INTO todos (id, title, description, status) VALUES\n"
                "  ('testing-harness', 'Add test harness', 'Add minimal pytest-based test configuration and shared test helpers/fixtures for session_view.', 'in_progress'),\n"
                "  ('testing-seams', 'Refactor test seams', 'Add surgical filesystem and subprocess seams so tests can run in temp directories and mock story generation.', 'pending'),\n"
                "  ('testing-coverage', 'Add behavior tests', 'Add behavior-first tests for CLI modes, ingest/turn reconstruction, rendering, overview generation, search, story flows, a11y, and summary merge behavior.', 'pending');"
            ),
        },
        "sql",
    )

    assert "sql-block" in html
    assert 'class="md-table"' in html
    assert ">id<" in html
    assert ">title<" in html
    assert ">description<" in html
    assert ">status<" in html
    assert ">testing-harness<" in html
    assert ">Add test harness<" in html
    assert ">in_progress<" in html
    assert html.index("sql-block") < html.index('class="md-table"')


def test_render_turns_renders_ask_user_panel_and_selected_choice(read_jsonl_fixture):
    turns = sv.build_turns(read_jsonl_fixture("ask-user-session.jsonl"))
    html = sv.render_turns(turns)

    assert "Which view should I show?" in html
    assert "Show file diffs (Recommended)" in html
    assert "Show recent git commits" in html
    assert 'class="ask-user-choice ask-user-choice-selected"' in html
    assert "✓ Selected" in html
    assert 'class="ask-user-summary-answer"' in html
    assert ">Arguments<" not in html
    assert ">Result<" not in html


def test_render_steps_shows_custom_ask_user_answer_without_guessing_choice():
    html = sv.render_steps(
        [{
            "kind": "tool",
            "name": "ask_user",
            "arguments": {
                "question": "What should I show next?",
                "choices": ["Show file diffs", "Show recent git commits"],
                "allow_freeform": True,
            },
            "result": {"content": "User selected: Just the short summary"},
            "success": True,
            "ts_start": "2026-05-16T10:00:00Z",
            "ts_end": "2026-05-16T10:00:01Z",
        }],
        0,
    )

    assert "What should I show next?" in html
    assert "Show file diffs" in html
    assert "Show recent git commits" in html
    assert "Just the short summary" in html
    assert "Custom answer allowed" in html
    assert "ask-user-choice-selected" not in html


def test_markdown_to_html_renders_lists_tables_and_inline_markup():
    html = sv.markdown_to_html(
        "**Bold** and `code`\n\n"
        "1. first\n"
        "2. second\n\n"
        "| Name | Value |\n"
        "| --- | --- |\n"
        "| foo | bar |\n"
    )

    assert "<strong>Bold</strong>" in html
    assert '<code class="md-code">code</code>' in html
    assert '<ol class="md-ol">' in html
    assert "<table" in html


def test_markdown_to_html_preserves_indented_list_continuations():
    html = sv.markdown_to_html(
        "- [ ] 🔴 **Cross-customer message risk** — `secure-message.ts:88-100`  \n"
        "  The dialog is non-modal and retains the original `partId`/`conversationId`.\n\n"
        "- 🟡 **Template variables are not substituted** — `follow-up-message.ts:76-80`  \n"
        "  `MarkdownTemplate.body` is used verbatim, so `{{firstName}}` can be sent literally.\n"
    )

    assert "The dialog is non-modal and retains the original" in html
    assert "MarkdownTemplate.body" in html
    assert '<ul class="md-ul"></ul>' not in html


def test_markdown_to_html_keeps_nested_lists():
    html = sv.markdown_to_html("- parent\n  - child\n")

    assert '<ul class="md-ul"><li class=\'md-li\'>parent<ul class="md-ul">' in html
    assert "child" in html
