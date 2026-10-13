import os

import pytest

from algolens.sandbox.client import SandboxClient, SandboxUnavailable

SOCKET = os.environ.get("ALGOLENS_TEST_SANDBOX_SOCKET")


def test_unreachable_sandbox_is_unavailable_not_a_verdict(tmp_path):
    client = SandboxClient(str(tmp_path / "missing.sock"), timeout_s=2)
    assert client.is_healthy() is False
    with pytest.raises(SandboxUnavailable):
        client.run_batch({"language": "python", "source": "", "entry": "f", "tests": []})


@pytest.fixture
def sandbox():
    if not SOCKET:
        pytest.skip("ALGOLENS_TEST_SANDBOX_SOCKET not set")
    client = SandboxClient(SOCKET)
    if not client.is_healthy():
        pytest.skip(f"sandbox not healthy at {SOCKET}")
    yield client
    client.close()


def test_python_batch_end_to_end(sandbox):
    resp = sandbox.run_batch(
        {
            "language": "python",
            "source": "def two_sum(nums, target):\n"
            "    seen = {}\n"
            "    for i, x in enumerate(nums):\n"
            "        if target - x in seen:\n"
            "            return [seen[target - x], i]\n"
            "        seen[x] = i\n",
            "entry": "two_sum",
            "tests": [
                {"id": "ex1", "input": {"args": [[2, 7, 11, 15], 9]}},
                {"id": "ex2", "input": {"args": [[3, 2, 4], 6]}},
            ],
        }
    )
    assert resp["status"] == "ok"
    assert [r["value"] for r in resp["results"]] == [[0, 1], [1, 2]]


def test_cpp_batch_end_to_end(sandbox):
    source = (
        "#include <algolens.h>\n#include <nlohmann/json.hpp>\n"
        "int main() {\n"
        "  auto in = nlohmann::json::parse(algolens::read_input());\n"
        '  auto v = in["args"][0].get<std::vector<int>>();\n'
        "  long s = 0; for (int x : v) s += x;\n"
        "  algolens::emit(nlohmann::json(s).dump());\n"
        "}\n"
    )
    resp = sandbox.run_batch(
        {
            "language": "cpp",
            "source": source,
            "tests": [{"id": "a", "input": {"args": [[1, 2, 3]]}}],
        }  # fmt: skip
    )
    assert resp["status"] == "ok", resp
    assert resp["results"][0]["value"] == 6


def test_compile_error_end_to_end(sandbox):
    resp = sandbox.run_batch(
        {"language": "cpp", "source": "int main( {", "tests": [{"id": "a", "input": {}}]}
    )
    assert resp["status"] == "compile_error"
