"""Brazilian Soccer MCP server (JSON-RPC 2.0 over stdio, MCP protocol)."""
import json
import sys

from soccer_tools import REQUIRED, TOOLS, data

PROTOCOL_VERSION = "2024-11-05"


def tool_list():
    return [{"name": n, "description": desc,
             "inputSchema": {"type": "object", "properties": props, "required": REQUIRED.get(n, [])}}
            for n, (_, desc, props) in TOOLS.items()]


def handle(msg):
    method, params = msg.get("method"), msg.get("params") or {}
    if method == "initialize":
        return {"protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": tool_list()}
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            raise LookupError(f"Unknown tool: {name}")
        try:
            text = TOOLS[name][0](**(params.get("arguments") or {}))
            return {"content": [{"type": "text", "text": text}], "isError": False}
        except Exception as e:  # report tool failures to the client, MCP-style
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
    raise LookupError(f"Method not found: {method}")


def main():
    data()  # load datasets once at startup
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        if "id" not in msg:
            continue  # notification
        try:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
        except LookupError as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": str(e)}}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    main()
