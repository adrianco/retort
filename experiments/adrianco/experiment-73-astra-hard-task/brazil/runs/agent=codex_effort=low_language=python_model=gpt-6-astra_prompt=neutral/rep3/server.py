"""Read-only MCP JSON-RPC stdio server. Run: python server.py [--data-dir PATH]."""
import argparse
import json
import sys
from soccer import SoccerGraph

FILTERS = {'team': 'string', 'opponent': 'string', 'venue': 'string', 'competition': 'string',
           'season': 'integer', 'start_date': 'string', 'end_date': 'string', 'stage': 'string',
           'source': 'string', 'derbies': 'boolean'}
TOOLS = {
    'search_matches': ('Find matches by team, opponent, venue, date range, competition, season, stage or source. Newest first.', FILTERS | {'limit':'integer','offset':'integer'}, []),
    'search_players': ('Search historical FIFA players, ratings and attributes. Position accepts forward, midfielder, defender, goalkeeper or FIFA code.',
                       {k:'string' for k in ('name','nationality','club','position')} | {k:'integer' for k in ('min_rating','limit','offset')}, []),
    'team_statistics': ('Calculate wins, draws, losses, goals and win rate from played matches.', FILTERS, ['team']),
    'head_to_head': ('Compare two teams in either direction.', FILTERS, ['team','opponent']),
    'standings': ('Calculate a league table. Not official championship or relegation evidence.', {'competition':'string','season':'integer','venue':'string'}, ['competition','season']),
    'analysis': ('Average goals, home win rate and biggest victories.', FILTERS | {'limit':'integer'}, []),
    'team_profile': ('Join team match statistics, competitions and FIFA roster.', {'team':'string'}, ['team']),
    'trends': ('Compare performance across seasons.', {'team':'string','competition':'string'}, []),
    'competition_results': ('Fixtures grouped by recorded stage/round, including knockout results.', {'competition':'string','season':'integer'}, ['competition','season']),
    'top_scorers': ('Explain why individual top scorers cannot be inferred.', {}, []),
    'coverage': ('Dataset counts, dates, rejected rows and conflicts.', {}, []),
    'neighbors': ('Explore team, player, competition and match graph relationships.', {'entity':'string','kind':'string','limit':'integer','offset':'integer'}, ['entity']),
}


class MCPServer:
    def __init__(self, graph):
        self.graph = graph
        self.initialized = False
        self.ready = False

    def handle(self, request):
        rid = request.get('id') if isinstance(request, dict) else None
        def error(code, message):
            return {'jsonrpc':'2.0','id':rid,'error':{'code':code,'message':message}}
        if not isinstance(request, dict) or request.get('jsonrpc') != '2.0' or not isinstance(request.get('method'), str):
            return error(-32600, 'Invalid Request')
        method, params = request['method'], request.get('params', {})
        if not isinstance(params, dict): return error(-32602, 'params must be an object')
        if 'id' not in request:
            if method == 'notifications/initialized' and self.initialized: self.ready = True
            return None
        if method == 'initialize':
            version = params.get('protocolVersion')
            if not isinstance(version, str): return error(-32602, 'protocolVersion required')
            self.initialized = True
            result = {'protocolVersion': version if version in ('2024-11-05','2025-03-26','2025-06-18','2025-11-25') else '2025-11-25',
                      'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name':'brazilian-soccer','version':'1.0.0'},
                      'instructions':'Use tools to answer natural-language soccer questions. All facts are dataset snapshots. Use coverage first when dates matter. Never infer individual scorers, official titles or relegation from incomplete records. For follow-ups reuse prior tool results or filters; server stores no conversation.'}
        elif method == 'ping': result = {}
        elif not self.ready: return error(-32000, 'Initialize and send notifications/initialized first')
        elif method == 'tools/list':
            result = {'tools': [{'name': name, 'description': desc, 'inputSchema': {'type':'object',
                      'properties': {k:{'type':v} for k,v in fields.items()}, 'required': required, 'additionalProperties':False},
                      'annotations': {'readOnlyHint':True, 'destructiveHint':False, 'idempotentHint':True, 'openWorldHint':False}}
                     for name,(desc,fields,required) in TOOLS.items()]}
        elif method == 'tools/call':
            name, args = params.get('name'), params.get('arguments', {})
            if not isinstance(name, str) or name not in TOOLS: return error(-32602, 'Unknown tool')
            _, fields, required = TOOLS[name]
            types = {'string':str, 'integer':int, 'boolean':bool}
            if not isinstance(args, dict) or any(k not in fields or type(v) is not types[fields[k]] for k,v in args.items()) or any(k not in args for k in required):
                return error(-32602, 'Invalid tool arguments')
            try:
                data = getattr(self.graph, name)(**args)
                result = {'content':[{'type':'text','text':json.dumps(data, ensure_ascii=False)}], 'isError':False}
            except (ValueError, TypeError) as exc:
                result = {'content':[{'type':'text','text':str(exc)}], 'isError':True}
        else: return error(-32601, 'Method not found')
        return {'jsonrpc':'2.0','id':rid,'result':result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir')
    args = parser.parse_args()
    server = MCPServer(SoccerGraph(args.data_dir))
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = {'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        else:
            response = server.handle(request)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
