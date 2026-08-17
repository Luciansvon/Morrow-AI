"""Control grammar must distinguish direct commands from quoted/project text."""

from src.core.types import MessageIntent
from src.routing.intent import intent_detector


def test_control_command_is_not_triggered_by_mid_sentence_text():
    text = "Manager, catat sebagai keputusan: jangan lanjut fitur X sampai audit selesai"
    assert intent_detector.detect_control_command(text) is None
    assert intent_detector.detect_intent(text) == MessageIntent.WORK_REQUEST


def test_control_command_accepts_role_and_thanks_prefixes():
    assert intent_detector.detect_control_command("Manager, stop yang tadi") == "cancel"
    assert intent_detector.detect_control_command("makasih, batal aja semua task") == "cancel"
