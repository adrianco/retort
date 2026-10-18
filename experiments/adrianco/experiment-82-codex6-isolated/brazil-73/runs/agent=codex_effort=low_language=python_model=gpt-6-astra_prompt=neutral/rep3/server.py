"""Dependency-free, newline-delimited MCP stdio server."""
import argparse
import inspect
import json
import sys
from soccer import SoccerGraph

FILTERS = {
    'team': ('string', 'Team name; accents and known aliases accepted.'),
    'opponent': ('string', 'Other team, in either orientation; requires team.'),
    'venue': ('string', 'either, home or away relative to team.'),
    'competition': ('string', 'Brasileirão, Serie A/B/C, Copa do Brasil or Libertadores.'),
    'season': ('integer', 'Season year, not necessarily calendar year.'),
    'start_date': ('string', 'Inclusive date YYYY-MM-DD or DD/MM/YYYY.'),
    'end_date': ('string', 'Inclusive date YYYY-MM-DD or DD/MM/YYYY.'),
    'stage': ('string', 'Exact stage label or numeric round; final excludes semifinals.'),
    'derbies': ('boolean', 'Only curated traditional rivalries.'),
    'source': ('string', 'Exact CSV filename to select provenance.'),
}
EXTRAS = {
    'limit': ('integer', 'Page size 1..500.'), 'offset': ('integer', 'Zero-based pagination offset.'),
    'name': ('string', 'Player name substring, accent insensitive.'),
    'nationality': ('string', 'Exact nationality, e.g. Brazil.'),
    'club': ('string', 'Normalized club name.'), 'position': ('string', 'FIFA position code or forward.'),
    'min_rating': ('integer', 'Minimum FIFA overall rating.'),
    'entity_id': ('string', 'Graph ID: team:flamengo, player:158023, match:1, competition:Libertadores.'),
}
METHODS = ('search_matches', 'team_stats', 'head_to_head', 'search_players', 'standings',
           'competition_results', 'analysis', 'graph_neighbors', 'coverage')


def tool_definitions(graph):
    definitions = []
    for name in METHODS:
        method = getattr(graph, name)
        properties, required = {}, []
        for param in inspect.signature(method).parameters.values():
            if param.kind == param.VAR_KEYWORD:
                for key, (typ, description) in FILTERS.items():
                    if key not in inspect.signature(method).parameters:
                        properties[key] = {'type': typ, 'description': description}
                continue
            typ, description = {**FILTERS, **EXTRAS}[param.name]
            properties[param.name] = {'type': typ, 'description': description}
            if param.default is param.empty:
                required.append(param.name)
        definitions.append({'name': name, 'description': method.__doc__,
                            'inputSchema': {'type': 'object', 'properties': properties,
                                            'required': required, 'additionalProperties': False},
                            'annotations': {'readOnlyHint': True, 'destructiveHint': False}})
    return definitions


class MCPServer:
    def __init__(self, graph):
        self.graph = graph
        self.tools = tool_definitions(graph)

    def handle(self, request):
        if not isinstance(request, dict) or request.get('jsonrpc') != '2.0' or not isinstance(request.get('method'), str):
            return self.error(None, -32600, 'Invalid Request')
        if 'id' not in request:
            return None  # initialized/cancelled notifications never receive a response
        rid, method = request['id'], request['method']
        params = request.get('params', {})
        if not isinstance(params, dict):
            return self.error(rid, -32602, 'params must be an object')
        if method == 'initialize':
            versions = ('2024-11-05', '2025-03-26', '2025-06-18')
            version = params.get('protocolVersion')
            result = {'protocolVersion': version if version in versions else versions[-1],
                      'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': 'brazilian-soccer', 'version': '1.0.0'},
                      'instructions': 'Answer natural-language questions by composing these read-only tools. '
                                      'Call coverage first for season availability. Use pagination for all results. '
                                      'Always describe results as dataset-based and distinguish historical rosters. '
                                      'Resolve follow-up questions using conversation context and match IDs. '
                                      'Do not infer individual scorers, official relegations or cup advancement.'}
        elif method == 'ping':
            result = {}
        elif method == 'tools/list':
            result = {'tools': self.tools}
        elif method == 'tools/call':
            definition = next((t for t in self.tools if t['name'] == params.get('name')), None)
            if definition is None:
                return self.error(rid, -32602, 'Unknown tool')
            try:
                arguments = params.get('arguments', {})
                self.validate(arguments, definition['inputSchema'])
                data = getattr(self.graph, definition['name'])(**arguments)
                result = {'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}],
                          'structuredContent': data, 'isError': False}
            except (ValueError, TypeError, KeyError) as exc:
                result = {'content': [{'type': 'text', 'text': str(exc)}], 'isError': True}
        else:
            return self.error(rid, -32601, 'Method not found')
        return {'jsonrpc': '2.0', 'id': rid, 'result': result}

    @staticmethod
    def validate(arguments, schema):
        if not isinstance(arguments, dict):
            raise ValueError('arguments must be an object')
        for key in schema['required']:
            if key not in arguments:
                raise ValueError(f'Missing required argument: {key}')
        for key, value in arguments.items():
            if key not in schema['properties']:
                raise ValueError(f'Unknown argument: {key}')
            typ = {'string': str, 'integer': int, 'boolean': bool}[schema['properties'][key]['type']]
            if type(value) is not typ:
                raise ValueError(f'{key} must be {typ.__name__}')

    @staticmethod
    def error(rid, code, message):
        return {'jsonrpc': '2.0', 'id': rid, 'error': {'code': code, 'message': message}}

    def serve(self, stream, output):
        for line in stream:
            try:
                request = json.loads(line)
                response = self.handle(request)
            except json.JSONDecodeError:
                response = self.error(None, -32700, 'Parse error')
            if response is not None:
                output.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + '\n')
                output.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', help='Directory containing all six CSV files')
    args = parser.parse_args()
    try:
        graph = SoccerGraph(args.data_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Dataset load failed: {exc}\n')
    MCPServer(graph).serve(sys.stdin, sys.stdout)


if __name__ == '__main__':
    main()
