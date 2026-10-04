"""Read-only MCP stdio server implementing protocol revision 2025-11-25."""
import argparse
import inspect
import json
import sys
from soccer import SoccerGraph, DATA

STR = {'type': 'string'}
INT = {'type': 'integer'}
FILTERS = {k: STR for k in ('team', 'opponent', 'competition', 'date_from', 'date_to', 'stage', 'source')}
FILTERS.update(season=INT, venue={'type': 'string', 'enum': ['home', 'away', 'either']})
PAGE = {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}, 'offset': {'type': 'integer', 'minimum': 0}}
SCHEMAS = {
    'search_matches': (dict(FILTERS, **PAGE), []),
    'team_statistics': (FILTERS, ['team']),
    'head_to_head': (FILTERS, ['team', 'opponent']),
    'search_players': (dict({k: STR for k in ('name','nationality','club','position')}, min_rating=INT, **PAGE), []),
    'standings': ({k: FILTERS[k] for k in ('competition','season','venue')}, ['competition','season']),
    'analysis': (FILTERS, []),
    'team_profile': ({'team': STR}, ['team']),
    'competition_bracket': ({'competition': STR, 'season': INT}, ['competition','season']),
    'derbies': (dict(season=INT, **PAGE), []),
    'graph_neighbors': (dict(node_id=STR, **PAGE), ['node_id']),
    'coverage': ({}, []),
}


def validate(name, arguments):
    if not isinstance(arguments, dict): raise ValueError('arguments must be an object')
    props, required = SCHEMAS[name]
    if set(arguments) - props.keys(): raise ValueError('Unknown arguments: '+', '.join(set(arguments)-props.keys()))
    if set(required) - arguments.keys(): raise ValueError('Missing required arguments: '+', '.join(set(required)-arguments.keys()))
    for key, value in arguments.items():
        spec = props[key]
        if spec['type'] == 'string' and (not isinstance(value, str) or not value.strip()): raise ValueError(key+' must be a nonempty string')
        if spec['type'] == 'integer' and type(value) is not int: raise ValueError(key+' must be an integer')
        if 'enum' in spec and value not in spec['enum']: raise ValueError('Invalid '+key)
        if 'minimum' in spec and value < spec['minimum']: raise ValueError(key+' below minimum')
        if 'maximum' in spec and value > spec['maximum']: raise ValueError(key+' above maximum')


class MCPServer:
    def __init__(self, graph):
        self.graph = graph
        self.initialized = False

    def handle(self, request):
        def error(code, message):
            return {'jsonrpc': '2.0', 'id': request.get('id') if isinstance(request, dict) else None,
                    'error': {'code': code, 'message': message}}
        if not isinstance(request, dict) or request.get('jsonrpc') != '2.0' or not isinstance(request.get('method'), str):
            return error(-32600, 'Invalid Request')
        if 'id' not in request:
            return None
        method, params = request['method'], request.get('params', {})
        if not isinstance(params, dict): return error(-32602, 'params must be an object')
        if method == 'initialize':
            version = params.get('protocolVersion')
            if not isinstance(version, str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                return error(-32602, 'initialize requires protocolVersion, capabilities and clientInfo')
            self.initialized = True
            result = dict(protocolVersion=version if version in ('2024-11-05','2025-03-26','2025-06-18','2025-11-25') else '2025-11-25',
                          capabilities={'tools': {'listChanged': False}}, serverInfo={'name': 'brazilian-soccer', 'version': '1.0.0'},
                          instructions='Use tools to answer natural-language soccer questions. Call coverage for dates and limitations. FIFA clubs are historical snapshots. Keep context in the LLM for follow-up questions. Never invent absent scores, player goal totals, cup winners or relegation decisions.')
        elif method == 'ping': result = {}
        elif not self.initialized: return error(-32000, 'Initialize first')
        elif method == 'tools/list':
            result = {'tools': [dict(name=name, description=inspect.getdoc(getattr(self.graph,name)),
                                    inputSchema=dict(type='object', properties=props, required=required, additionalProperties=False),
                                    annotations={'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False})
                                for name,(props,required) in SCHEMAS.items()]}
        elif method == 'tools/call':
            name = params.get('name')
            if not isinstance(name, str) or name not in SCHEMAS: return error(-32602, 'Unknown tool')
            try:
                args = params.get('arguments', {})
                validate(name, args)
                data = getattr(self.graph, name)(**args)
                result = dict(content=[{'type': 'text', 'text': json.dumps(data, ensure_ascii=False, allow_nan=False)}], isError=False)
            except (ValueError, TypeError) as exc:
                result = dict(content=[{'type': 'text', 'text': str(exc)}], isError=True)
        else: return error(-32601, 'Method not found')
        return dict(jsonrpc='2.0', id=request['id'], result=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=str(DATA))
    args = parser.parse_args()
    server = MCPServer(SoccerGraph(args.data_dir))
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except ValueError:
            response = dict(jsonrpc='2.0', id=None, error={'code': -32700, 'message': 'Parse error'})
        else:
            response = server.handle(request)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
