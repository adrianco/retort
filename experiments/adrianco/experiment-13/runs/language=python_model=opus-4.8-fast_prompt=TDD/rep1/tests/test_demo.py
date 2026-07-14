"""Smoke test for the demo question runner."""
from brazilian_soccer import demo
from brazilian_soccer.server import SoccerService


def test_sample_questions_count():
    # The spec requires at least 20 answerable sample questions.
    assert len(demo.SAMPLE_QUESTIONS) >= 20


def test_run_question_returns_text(fixture_dir):
    svc = SoccerService.from_data_dir(fixture_dir)
    q, answer = demo.SAMPLE_QUESTIONS[0]
    text = demo.run_question(svc, demo.SAMPLE_QUESTIONS[0])
    assert q in text
    assert answer.__name__  # callable bound


def test_run_all_does_not_crash(fixture_dir):
    svc = SoccerService.from_data_dir(fixture_dir)
    out = demo.run_all(svc)
    assert len(out.splitlines()) > 20
