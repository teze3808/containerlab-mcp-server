import pytest

from containerlab_mcp.client_cli import build_parser, parse_tool_arguments


def test_parse_tool_arguments() -> None:
    assert parse_tool_arguments('{"name":"lab1","deploy":false}') == {
        "name": "lab1",
        "deploy": False,
    }


@pytest.mark.parametrize("raw", ["[]", '"value"', "not-json"])
def test_parse_tool_arguments_requires_json_object(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_tool_arguments(raw)


def test_cli_parser_supports_tools_and_call() -> None:
    parser = build_parser()

    tools = parser.parse_args(["tools", "--schemas"])
    call = parser.parse_args(
        ["--json", "call", "health", "--arguments", "{}"]
    )

    assert tools.action == "tools"
    assert tools.schemas is True
    assert call.action == "call"
    assert call.tool == "health"
    assert call.json is True
    assert call.verbose is False
