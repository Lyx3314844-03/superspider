import tempfile as tempfile_module

import pytest


class _BenchmarkStub:
    def __call__(self, func, *args, **kwargs):
        if callable(func):
            return func(*args, **kwargs)
        raise TypeError("benchmark expects a callable")

    def pedantic(self, func, iterations=1, rounds=1):
        result = None
        for _ in range(rounds):
            for _ in range(iterations):
                result = func()
        return result


@pytest.fixture
def benchmark():
    return _BenchmarkStub()


@pytest.fixture
def tempfile():
    return tempfile_module
