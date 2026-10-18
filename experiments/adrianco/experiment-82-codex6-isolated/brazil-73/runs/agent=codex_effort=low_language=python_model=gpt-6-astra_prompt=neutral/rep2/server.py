"""Newline-delimited JSON-RPC MCP stdio server, protocol 2025-06-18.

Natural language is interpreted by the connected LLM, which calls typed tools.
Run: python server.py [--data-dir data/kaggle]
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
from soccer import DATA_DIR, SoccerGraph

TOOL_NAMES = ('search_matches', 'team_statistics', 'head_to_head', 'search_players',
              'standings', 'bracket', 'analysis', 'season_comparison',
              'graph_neighbors', 'dataset_info')
INTS = {'season', 'min_rating', 'limit', 'offset'}
ENUMS = {'venue': ['home', 'away', 'either'], 'entity_type': ['team', 'player', 'competition']}


def tool_schema(name):
    method = getattr(SoccerGraph, name)
    properties, required = {}, []
    for key, param in inspect.signature(method).parameters.items():
        if key == 'self':
            continue
        schema = {'type': 'integer' if key in INTS else 'boolean' if key == 'derbies' else
                  'array' if key == 'seasons' else 'string'}
        if key == 'seasons':
            schema.update(items={'type': 'integer'}, minItems=1, maxItems=30)
        if key in ENUMS:
            schema['enum'] = ENUMS[key]
        if key in {'limit', 'offset'}:
            schema['minimum'] = 1 if key == 'limit' else 0
            if key == 'limit':
                schema['maximum'] = 500
        if param.default is inspect.Parameter.empty:
            required.append(key)
        elif param.default is not None:
            schema['default'] = param.default
        properties[key] = schema
    return {'name': name, 'description': inspect.getdoc(method),
            'inputSchema': {'type': 'object', 'properties': properties,
                            'required': required, 'additionalProperties': False},
            'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False}}


SCHEMAS = {name: tool_schema(name) for name in TOOL_NAMES}


def validate(name, arguments):
    if name not in SCHEMAS:
        raise ValueError(f'Unknown tool: {name}')
    if not isinstance(arguments, dict):
        raise ValueError('arguments must be an object')
    schema = SCHEMAS[name]['inputSchema']
    for required in schema['required']:
        if required not in arguments:
            raise ValueError(f'Missing argument: {required}')
    for key, value in arguments.items():
        if key not in schema['properties']:
            raise ValueError(f'Unknown argument: {key}')
        prop = schema['properties'][key]
        expected = {'string': str, 'integer': int, 'boolean': bool, 'array': list}[prop['type']]
        if type(value) is not expected:
            raise ValueError(f'{key} must be {prop["type"]}')
        if 'enum' in prop and value not in prop['enum']:
            raise ValueError(f'{key} must be one of {prop["enum"]}')
        if expected is int and (value < prop.get('minimum', value) or value > prop.get('maximum', value)):
            raise ValueError(f'{key} outside supported range')
        if expected is list and (not 1 <= len(value) <= 30 or any(type(v) is not int for v in value)):
            raise ValueError('seasons must contain 1 to 30 integers')


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
            return self.error(request.get('id') if isinstance(request, dict) else None, -32600, 'Invalid Request')
        request_id = request.get('id')
        if 'id' in request and (type(request_id) not in (str, int) and request_id is not None):
            return self.error(None, -32600, 'Invalid request id')
        method = request['method']
        if 'id' not in request:
            if method == 'notifications/initialized' and self.initialized:
                self.ready = True
            return None
        params = request.get('params', {})
        if not isinstance(params, dict):
            return self.error(request_id, -32602, 'params must be an object')
        if method == 'initialize':
            if not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                return self.error(request_id, -32602, 'initialize requires protocolVersion, capabilities and clientInfo')
            self.initialized = True
            result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': 'brazilian-soccer', 'version': '1.0.0'},
                      'instructions': 'Answer natural-language soccer questions using these tools. Inspect dataset_info for coverage. Paginate results. Explain snapshot limitations and computed standings; never invent scorers or unavailable fixtures. Conversation context belongs to the host LLM.'}
        elif method == 'ping':
            result = {}
        elif not self.ready:
            return self.error(request_id, -32002, 'Initialize and send notifications/initialized first')
        elif method == 'tools/list':
            result = {'tools': list(SCHEMAS.values())}
        elif method == 'tools/call':
            name, arguments = params.get('name'), params.get('arguments', {})
            if not isinstance(name, str) or name not in SCHEMAS:
                return self.error(request_id, -32602, 'Unknown tool')
            try:
                validate(name, arguments)
                data = getattr(self.graph, name)(**arguments)
                result = {'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False, indent=2)}],
                          'structuredContent': data, 'isError': False}
            except (ValueError, TypeError) as exc:
                result = {'content': [{'type': 'text', 'text': str(exc)}], 'isError': True}
        else:
            return self.error(request_id, -32601, 'Method not found')
        return {'jsonrpc': '2.0', 'id': request_id, 'result': result}

    def serve(self, reader, writer):
        for line in reader:
            try:
                request = json.loads(line)
            except (json.JSONDecodeError, UnicodeError):
                response = self.error(None, -32700, 'Parse error')
            else:
                try:
                    response = self.handle(request)
                except Exception as exc:
                    print(f'Internal error: {exc}', file=sys.stderr)
                    response = self.error(request.get('id') if isinstance(request, dict) else None, -32603, 'Internal error')
            if response is not None:
                writer.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + '\n')
                writer.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=str(DATA_DIR))
    args = parser.parse_args()
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        graph = SoccerGraph(args.data_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Unable to load soccer data: {exc}\n')
    MCPServer(graph).serve(sys.stdin, sys.stdout)


if __name__ == '__main__':
    main()
