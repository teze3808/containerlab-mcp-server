from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Sequence

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="containerlab-mcp-client",
        description="Lightweight stdio client for containerlab-mcp-server.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete MCP response as JSON.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show diagnostic output from the MCP server process.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    tools_parser = subparsers.add_parser("tools", help="List available tools.")
    tools_parser.add_argument(
        "--schemas",
        action="store_true",
        help="Include each tool's input schema.",
    )

    call_parser = subparsers.add_parser("call", help="Call one MCP tool.")
    call_parser.add_argument("tool", help="MCP tool name.")
    call_parser.add_argument(
        "--arguments",
        default="{}",
        metavar="JSON",
        help="Tool arguments as a JSON object.",
    )
    return parser


def parse_tool_arguments(raw: str) -> dict[str, Any]:
    try:
        arguments = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON arguments: {exc.msg}") from exc
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be a JSON object")
    return arguments


def _dump_json(value: Any) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", by_alias=True, exclude_none=True)
    print(json.dumps(value, indent=2, sort_keys=True))


async def run_client(args: argparse.Namespace) -> int:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "containerlab_mcp.server"],
        env=dict(os.environ),
    )
    errlog = sys.stderr if args.verbose else open(os.devnull, "w")
    try:
        async with stdio_client(server, errlog=errlog) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                if args.action == "tools":
                    result = await session.list_tools()
                    if args.json:
                        _dump_json(result)
                    else:
                        for tool in sorted(
                            result.tools,
                            key=lambda item: item.name,
                        ):
                            print(tool.name)
                            if tool.description:
                                print(f"  {tool.description}")
                            if args.schemas:
                                schema = json.dumps(
                                    tool.inputSchema,
                                    sort_keys=True,
                                )
                                print(f"  schema: {schema}")
                    return 0

                arguments = parse_tool_arguments(args.arguments)
                result = await session.call_tool(args.tool, arguments=arguments)
                if args.json or result.structuredContent is None:
                    _dump_json(result)
                else:
                    _dump_json(result.structuredContent)
                return 1 if result.isError else 0
    finally:
        if errlog is not sys.stderr:
            errlog.close()


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code = asyncio.run(run_client(args))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
