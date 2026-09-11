"""MCP stdio entry point. An attached LLM maps natural language to these tools."""
import argparse
import json
import sys
from soccer import SoccerGraph

FILTERS = {k:{'type':'string'} for k in ('team','opponent','competition','date_from','date_to','stage','source')}
FILTERS.update(season={'type':'integer'},venue={'type':'string','enum':['home','away','either']},derbies={'type':'boolean'})
PAGE = {'limit':{'type':'integer','minimum':1,'maximum':500},'offset':{'type':'integer','minimum':0}}
S = {'type':'string'}
DEFINITIONS = {
 'search_matches': ('Search fixtures/results across all five match files. Dates ISO or DD/MM/YYYY; stage=final supported. latest=true returns newest first.', dict(FILTERS,**PAGE,latest={'type':'boolean'}), []),
 'search_players': ('Search historical FIFA players, sorted by rating; position=forwards includes attacking positions. Full raw attributes returned.',dict({k:S for k in ('name','nationality','club','position')},**PAGE),[]),
 'standings': ('Calculate points and records; filter venue for home/away rankings. Sort returned goals_for for highest-scoring teams. Not official champions or relegation.',FILTERS,[]),
 'team_info': ('Team records, competitions and historical FIFA roster; cross-file query.',FILTERS,['team']),
 'head_to_head': ('Compare two teams with wins/draws/losses and fixtures.',FILTERS,['team','opponent']),
 'statistics': ('Average goals, home win percentage and biggest victories.',FILTERS,[]),
 'trends': ('Compare season aggregates for a team or competition.',{'team':S,'competition':S},[]),
 'bracket': ('Recorded cup fixtures grouped by stage; no invented advancement.',{'competition':S,'season':{'type':'integer'}},['competition','season']),
 'top_scorers': ('Explain why individual scorer statistics are unavailable.',{},[]),
 'graph': ('Bounded knowledge graph of teams, players, matches and competitions with typed edges.',{'team':S,'limit':PAGE['limit']},['team']),
 'coverage': ('Source row counts, dates, ingestion diagnostics and deduplication policy.',{},[]),
}


def tool_list():
    return [dict(name=name,description=desc,inputSchema=dict(type='object',properties=props,required=required,additionalProperties=False)) for name,(desc,props,required) in DEFINITIONS.items()]


def validate(name,args):
    if name not in DEFINITIONS: raise ValueError('Unknown tool: '+str(name))
    if not isinstance(args,dict): raise ValueError('arguments must be an object')
    _,props,required=DEFINITIONS[name]
    for key in required:
        if key not in args: raise ValueError('Missing argument: '+key)
    for key,value in args.items():
        if key not in props: raise ValueError('Unknown argument: '+key)
        schema=props[key]; kind=schema['type']
        if (kind=='string' and not isinstance(value,str)) or (kind=='integer' and type(value)!=int) or (kind=='boolean' and type(value)!=bool): raise ValueError('Invalid type for '+key)
        if 'enum' in schema and value not in schema['enum']: raise ValueError('Invalid value for '+key)
        if kind=='integer' and (value<schema.get('minimum',-999999) or value>schema.get('maximum',999999)): raise ValueError('Out of range: '+key)


class Server:
    def __init__(self,graph): self.graph=graph

    def handle(self,request):
        rid=request.get('id') if isinstance(request,dict) else None
        def error(code,message): return dict(jsonrpc='2.0',id=rid,error=dict(code=code,message=message))
        if not isinstance(request,dict) or request.get('jsonrpc')!='2.0' or not isinstance(request.get('method'),str): return error(-32600,'Invalid Request')
        if 'id' not in request: return None
        method=request['method']; params=request.get('params',{})
        if not isinstance(params,dict): return error(-32602,'params must be an object')
        if method=='initialize':
            supported=('2024-11-05','2025-03-26','2025-06-18')
            version=params.get('protocolVersion')
            result=dict(protocolVersion=version if version in supported else supported[-1],capabilities={'tools':{'listChanged':False}},serverInfo={'name':'brazilian-soccer','version':'1.0.0'},instructions='Use tools to answer natural-language questions. Use previous conversation results for follow-up scores. Data is historical; state coverage and avoid inventing scorers, champions or relegation. Paginate lists.')
        elif method=='ping': result={}
        elif method=='tools/list': result={'tools':tool_list()}
        elif method=='tools/call':
            try:
                name=params.get('name'); args=params.get('arguments',{})
                validate(name,args)
                output=getattr(self.graph,name)(**args)
                result=dict(content=[dict(type='text',text=json.dumps(output,ensure_ascii=False))],isError=False)
            except (ValueError,TypeError) as exc:
                result=dict(content=[dict(type='text',text=str(exc))],isError=True)
        else: return error(-32601,'Method not found')
        return dict(jsonrpc='2.0',id=rid,result=result)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--data-dir'); args=parser.parse_args()
    server=Server(SoccerGraph(args.data_dir))
    for line in sys.stdin:
        try: response=server.handle(json.loads(line))
        except json.JSONDecodeError: response=dict(jsonrpc='2.0',id=None,error=dict(code=-32700,message='Parse error'))
        if response is not None: print(json.dumps(response,ensure_ascii=False),flush=True)

if __name__=='__main__': main()
