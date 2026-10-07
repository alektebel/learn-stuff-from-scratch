import pytest
from retrying import retry


def flaky(n_failures, exc=ConnectionError):
    state = {"calls": 0}

    def fn():
        """doc"""
        state["calls"] += 1
        if state["calls"] <= n_failures:
            raise exc(f"fail {state['calls']}")
        return "ok"
    return fn, state


def test_succeeds_after_retries_with_backoff():
    sleeps = []
    fn, state = flaky(2)
    wrapped = retry(attempts=3, base_delay=0.5, factor=2.0, retry_on=(ConnectionError,), sleep=sleeps.append)(fn)
    assert wrapped() == "ok"
    assert state["calls"] == 3 and sleeps == [0.5, 1.0]


def test_reraises_last_exception_without_final_sleep():
    sleeps = []
    fn, state = flaky(10)
    wrapped = retry(attempts=3, base_delay=1, factor=3, retry_on=(ConnectionError,), sleep=sleeps.append)(fn)
    with pytest.raises(ConnectionError, match="fail 3"):
        wrapped()
    assert state["calls"] == 3 and sleeps == [1, 3]


def test_non_retryable_propagates_immediately():
    sleeps = []
    fn, state = flaky(1, exc=KeyError)
    wrapped = retry(attempts=5, retry_on=(ConnectionError,), sleep=sleeps.append)(fn)
    with pytest.raises(KeyError):
        wrapped()
    assert state["calls"] == 1 and sleeps == []


def test_metadata_and_args():
    @retry(attempts=1, sleep=lambda s: None)
    def add(a, b=0):
        """adds"""
        return a + b
    assert add(1, b=2) == 3
    assert add.__name__ == "add" and add.__doc__ == "adds"


def test_invalid_attempts():
    with pytest.raises(ValueError):
        retry(attempts=0)
