import pytest

from pm.evm import load

pytest_plugins = ["results_plugin"]


@pytest.fixture(scope="session")
def plan():
    return load("plan.json")


@pytest.fixture(scope="session")
def raid():
    return load("raid.json")
