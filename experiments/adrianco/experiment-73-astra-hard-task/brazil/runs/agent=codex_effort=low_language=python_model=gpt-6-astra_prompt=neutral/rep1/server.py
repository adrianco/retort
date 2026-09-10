"""Dependency-free MCP stdio server. Run: python server.py [--data-dir PATH]."""
from __future__ import annotations

import argparse
import inspect
import json
import sys
from soccer import DATA_DIR, SoccerGraph

PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05')
TOOL_NAMES = ('search_matches', 'get_match', 'team_statistics', 'head_to_head',
              'search_players', 'standings', 'competition_bracket', 'statistics',
              'season_trends', 'derbies', 'competitions', 'graph_neighbors', 'data_status')
INSTRUCTIONS = '''Answer natural-language soccer questions by calling these read-only tools.
Use data_status for coverage, search_matches for scores/latest meetings, team_statistics
for records, head_to_head for comparisons, search_players for the historical FIFA snapshot,
standings for calculated league positions, competition_bracket for observed cup ties,
statistics for goals and home/away rankings, season_trends for comparisons and derbies
for curated rivalries. Follow pagination when the user asks for all records. For score
follow-ups reuse the match_id from this conversation with get_match. Never fabricate
unavailable players, individual scorers, current rosters, shootouts or official titles.
State dataset scope and incomplete coverage. No SQL, shell commands or network access
are exposed by these tools.'''


def tool_definition(name):
    method = getattr(SoccerGraph, name)
    props, required = {}, []
    for key, param in inspect.signature(method).parameters.items():
        if key == 'self':
            continue
        kind = 'integer' if key in ('season', 'limit', 'offset', 'min_overall') else 'array' if key == 'seasons' else 'string'
        schema = {'type': kind}
        if kind == 'array':
            schema.update(items={'type': 'integer'}, minItems=1, maxItems=30)
        if key == 'venue':
            schema['enum'] = ['home', 'away', 'either']
        if key == 'limit':
            schema.update(minimum=1, maximum=500)
        if key == 'offset':
            schema['minimum'] = 0
        if key == 'min_overall':
            schema.update(minimum=0, maximum=100)
        if param.default is inspect.Parameter.empty:
            required.append(key)
        elif param.default is not None:
            schema['default'] = param.default
        props[key] = schema
    return {'name': name, 'description': inspect.getdoc(method),
            'inputSchema': {'type': 'object', 'properties': props, 'required': required, 'additionalProperties': False},
            'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}}


TOOLS = {name: tool_definition(name) for name in TOOL_NAMES}


def validate_arguments(name, args):
    if not isinstance(args, dict):
        raise ValueError('arguments must be an object')
    schema = TOOLS[name]['inputSchema']
    if set(args) - set(schema['properties']):
        raise ValueError('Unknown argument(s): ' + ', '.join(sorted(set(args) - set(schema['properties']))))
    for key in schema['required']:
        if key not in args:
            raise ValueError('Missing required argument: ' + key)
    for key, value in args.items():
        prop = schema['properties'][key]
        expected = {'string': str, 'integer': int, 'array': list}[prop['type']]
        if type(value) is not expected:
            raise ValueError(f'{key} must be {prop["type"]}')
        if expected is str and not value.strip():
            raise ValueError(f'{key} must not be empty')
        if 'enum' in prop and value not in prop['enum']:
            raise ValueError(f'{key} must be one of {prop["enum"]}')
        if expected is int and (value < prop.get('minimum', -10**9) or value > prop.get('maximum', 10**9)):
            raise ValueError(f'{key} out of range')
        if expected is list and (not 1 <= len(value) <= 30 or any(type(x) is not int for x in value)):
            raise ValueError(f'{key} must contain 1 to 30 integer years')


def format_result(name, data):
    """Readable summary followed by complete machine-readable data in structuredContent."""
    if name in ('search_matches', 'derbies'):
        lines = [f"{data['total']} matches in dataset (offset {data['offset']})."]
        for m in data['items']:
            score = f"{m['home_goal']}-{m['away_goal']}" if m['home_goal'] is not None and m['away_goal'] is not None else 'score unavailable'
            lines.append(f"- {m['date'] or 'Date unknown'}: {m['home_team']} {score} {m['away_team']} ({m['competition']}, {m['stage'] or 'Round ' + str(m['round'] or '?')}) [{m['id']}]")
        if data['next_offset'] is not None:
            lines.append(f"More results: request offset={data['next_offset']}.")
        return '\n'.join(lines)
    if name == 'team_statistics':
        return (f"{data['team']} ({data['season'] or 'all seasons'}, {data['venue']}): "
                f"{data['played']} played; {data['wins']}W, {data['draws']}D, {data['losses']}L; "
                f"goals {data['goals_for']}-{data['goals_against']}; win rate {data['win_rate']}%.\n{data['note']}")
    if name == 'search_players':
        return '\n'.join([f"{data['total']} players in FIFA snapshot."] +
                         [f"- {p['name']} — Overall: {p['overall']}, Position: {p['position']}, Club: {p['club'] or 'unknown'}" for p in data['items']] + [data['note']])
    if name == 'standings':
        return '\n'.join([f"{data['season']} {data['competition']} — calculated standings:"] +
                         [f"{r['rank']}. {r['team']} — {r['points']} pts ({r['wins']}W, {r['draws']}D, {r['losses']}L), GD {r['goal_difference']}" for r in data['table']] + [data['note']])
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)


class MCPServer:
    def __init__(self, graph):
        self.graph = graph
        self.initialized = False
        self.ready = False

    @staticmethod
    def error(request_id, code, message):
        return {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': code, 'message': message}}

    def handle(self, request):
        if not isinstance(request, dict) or request.get('jsonrpc') != '2.0' or not isinstance(request.get('method'), str):
            return self.error(None, -32600, 'Invalid Request')
        rid = request.get('id')
        if 'id' in request and (type(rid) not in (str, int)):
            return self.error(None, -32600, 'Request id must be a string or integer')
        method, params = request['method'], request.get('params', {})
        if 'id' not in request:
            if method == 'notifications/initialized' and self.initialized:
                self.ready = True
            return None
        if not isinstance(params, dict):
            return self.error(rid, -32602, 'params must be an object')
        if method == 'initialize':
            if not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                return self.error(rid, -32602, 'initialize requires protocolVersion, capabilities and clientInfo')
            version = params['protocolVersion']
            self.initialized = True
            result = {'protocolVersion': version if version in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                      'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': 'brazilian-soccer', 'version': '1.0.0'}, 'instructions': INSTRUCTIONS}
        elif method == 'ping':
            result = {}
        elif not self.ready:
            return self.error(rid, -32002, 'Initialize the session and send notifications/initialized first')
        elif method == 'tools/list':
            if params.get('cursor'):
                return self.error(rid, -32602, 'Invalid cursor')
            result = {'tools': list(TOOLS.values())}
        elif method == 'tools/call':
            name = params.get('name')
            if not isinstance(name, str) or name not in TOOLS:
                return self.error(rid, -32602, 'Unknown tool')
            args = params.get('arguments', {})
            try:
                validate_arguments(name, args)
                data = getattr(self.graph, name)(**args)
                result = {'content': [{'type': 'text', 'text': format_result(name, data)},
                                      {'type': 'text', 'text': json.dumps(data, ensure_ascii=False, allow_nan=False)}],
                          'structuredContent': data, 'isError': False}
            except (ValueError, TypeError) as exc:
                result = {'content': [{'type': 'text', 'text': str(exc)}], 'isError': True}
            except Exception:
                print('Unexpected error executing ' + name, file=sys.stderr)
                return self.error(rid, -32603, 'Internal error')
        else:
            return self.error(rid, -32601, 'Method not found')
        return {'jsonrpc': '2.0', 'id': rid, 'result': result}

    def serve(self, input_stream=sys.stdin, output_stream=sys.stdout):
        # MCP stdio uses one UTF-8 JSON-RPC message per line, never HTTP headers.
        for line in input_stream:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
            except (ValueError, UnicodeError):
                response = self.error(None, -32700, 'Parse error')
            else:
                response = self.handle(request)
            if response is not None:
                output_stream.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + '\n')
                output_stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=str(DATA_DIR))
    args = parser.parse_args()
    try:
        graph = SoccerGraph(args.data_dir)
    except (OSError, ValueError) as exc:
        print(f'Cannot load soccer datasets: {exc}', file=sys.stderr)
        return 1
    MCPServer(graph).serve()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
