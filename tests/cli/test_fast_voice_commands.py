from unittest.mock import MagicMock, patch

from samantha.cli._fast_voice_commands import handle_fast_voice_command


def _result(*, success=True, content=""):
    return MagicMock(success=success, content=content)


def test_add_priority_is_fast_and_local():
    with patch("samantha.cli._fast_voice_commands.UserProfileManageTool") as tool_cls:
        tool_cls.return_value.execute.return_value = _result(success=True)

        response = handle_fast_voice_command(
            "Samantha, remember finish the proposal as a priority"
        )

    assert response == "Priority saved: finish the proposal, Sir."
    tool_cls.return_value.execute.assert_called_once_with(
        action="add", entry="Priority: finish the proposal"
    )


def test_list_priorities_reads_only_tagged_profile_entries():
    with patch("samantha.cli._fast_voice_commands.UserProfileManageTool") as tool_cls:
        tool_cls.return_value.execute.return_value = _result(
            content="- Name: Mir\n- Priority: Finish proposal\n- Priority: Call team\n"
        )

        response = handle_fast_voice_command("Samantha, list my priorities")

    assert response == "Your priorities are: Finish proposal; Call team."


def test_list_priorities_accepts_common_samantha_transcription_error():
    with patch("samantha.cli._fast_voice_commands.UserProfileManageTool") as tool_cls:
        tool_cls.return_value.execute.return_value = _result(content="(empty)")

        response = handle_fast_voice_command("samanta list my priorities")

    assert response == "You have no saved priorities, Sir."


def test_fast_command_ignores_spoken_filler():
    with patch("samantha.cli._fast_voice_commands.UserProfileManageTool") as tool_cls:
        tool_cls.return_value.execute.return_value = _result(content="(empty)")

        response = handle_fast_voice_command("Okay, list my priorities")

    assert response == "You have no saved priorities, Sir."


def test_open_excel_accepts_common_whisper_mispronunciation():
    with patch("samantha.cli._fast_voice_commands.MacOSControlTool") as tool_cls:
        tool_cls.return_value.execute.return_value = _result(success=True)

        response = handle_fast_voice_command("open extel")

    assert response == "Opened Microsoft Excel, Sir."
    tool_cls.return_value.execute.assert_called_once_with(
        action="open_app", app="Microsoft Excel"
    )


def test_complete_priority_removes_matching_entry():
    with patch("samantha.cli._fast_voice_commands.UserProfileManageTool") as tool_cls:
        tool_cls.return_value.execute.return_value = _result(success=True)

        response = handle_fast_voice_command(
            "Samantha, complete priority finish the proposal"
        )

    assert response == "Priority completed: finish the proposal, Sir."
    tool_cls.return_value.execute.assert_called_once_with(
        action="remove", entry="finish the proposal"
    )
