import pytest

from retry import retry


def test_succeeds_after_transient_failures():
    calls = []

    @retry(attempts=3, sleep=lambda _: None)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("reset by peer")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 3


def test_gives_up_and_reraises():
    @retry(attempts=2, sleep=lambda _: None)
    def always_down():
        raise TimeoutError("upstream timeout")

    with pytest.raises(TimeoutError):
        always_down()


def test_does_not_retry_bugs():
    calls = []

    @retry(attempts=5, sleep=lambda _: None)
    def buggy():
        calls.append(1)
        raise ValueError("bad input")

    with pytest.raises(ValueError):
        buggy()
    assert len(calls) == 1
