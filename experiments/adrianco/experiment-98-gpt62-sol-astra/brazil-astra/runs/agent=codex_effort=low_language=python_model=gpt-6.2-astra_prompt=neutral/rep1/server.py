"""Brazilian soccer MCP server over newline-delimited JSON-RPC on stdio."""
import json
import sys

from soccer import Graph, FILES

FILTERS = dict(team="Club in either dataset, including aliases", opponent="Second club for head-to-head",
               competition_name="Brasileirão (Serie A), Copa do Brasil, Libertadores, Serie B or Serie C",
               season="Season year", venue="either, home or away", start="Inclusive first date",
               end="Inclusive last date", stage="Exact stage, e.g. final, semifinals, or round number",
               source="Filter by CSV basename: " + ", ".join(FILES), derby="Traditional rivalry matches")
PAGING = dict(limit="Page size (1–200)", offset="Rows to skip")
TOOLS = {
    "find_matches": ("Fixtures and scores, newest first. Use stage for brackets and limit=1 for latest.",
                     {**FILTERS, **PAGING, "biggest_wins": "Sort decisive results by goal difference"}),
    "find_players": ("FIFA snapshot ranked by overall rating. Join to matches with the team argument.",
                     dict(name="Partial player name", nationality="Country", team="Club",
                          position="FIFA position or forwards", details="Include all attributes", **PAGING)),
    "statistics": ("Calculated standings, team records, competitions played, win rates and goals per match. "
                   "Compare seasons by calling once per year. Points use 3 for wins and 1 for draws.",
                   {**FILTERS, **PAGING, "rank_by": "points, wins, win_rate or goals_for"}),
}
TYPES = dict(season=int, limit=int, offset=int, derby=bool, biggest_wins=bool, details=bool)
JSON_TYPES = {int: "integer", bool: "boolean", str: "string"}
VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")


def catalog():
    result = []
    for name, (description, fields) in TOOLS.items():
        props = {k: dict(type=JSON_TYPES[TYPES.get(k, str)], description=v) for k,v in fields.items()}
        result.append(dict(name=name, description=description,
                           inputSchema=dict(type="object", properties=props, additionalProperties=False)))
    return result


def error(code, message):
    return {"error": {"code": code, "message": message}}


def dispatch(graph, request):
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
        return dict(jsonrpc="2.0", id=None, **error(-32600, "Invalid Request"))
    if "id" not in request:
        return None
    method = request["method"]
    params = request.get("params", {})
    if not isinstance(params, dict):
        reply = error(-32602, "Expected object parameters")
    elif method == "initialize":
        version = params.get("protocolVersion")
        reply = dict(result=dict(protocolVersion=version if version in VERSIONS else VERSIONS[0],
                     capabilities={"tools": {}}, serverInfo=dict(name="brazilian-soccer", version="1.0"),
                     instructions="Answer from supplied data. Individual match scorers are unavailable. "
                     "Use multiple calls for trends, head-to-head summaries or player and match questions."))
    elif method == "tools/list":
        reply = dict(result={"tools": catalog()})
    elif method == "ping":
        reply = dict(result={})
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if not isinstance(name, str) or name not in TOOLS:
            reply = error(-32602, "Unknown tool")
        else:
            try:
                if not isinstance(args, dict) or any(k not in TOOLS[name][1] or
                        type(v) is not TYPES.get(k, str) for k,v in args.items()):
                    raise ValueError("Arguments do not match tool schema")
                value = getattr(graph, name)(**args)
                reply = dict(result={"content": [{"type":"text", "text":json.dumps(value, ensure_ascii=False)}]})
            except (TypeError, ValueError) as exc:
                reply = dict(result={"isError": True, "content": [{"type":"text", "text":str(exc)}]})
    else:
        reply = error(-32601, "Method not found")
    return dict(jsonrpc="2.0", id=request["id"], **reply)


def main():
    graph = Graph()
    for line in sys.stdin.buffer:
        try:
            response = dispatch(graph, json.loads(line))
        except (ValueError, UnicodeError):
            response = dict(jsonrpc="2.0", id=None, **error(-32700, "Parse error"))
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
