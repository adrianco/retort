package org.brazilsoccer.mcp;

import java.io.*;import java.nio.file.*;import java.util.*;

/** MCP stdio server. Start with: java -jar target/brazilian-soccer-mcp-1.0.0.jar [data-directory]. */
public final class BrazilianSoccerMcpServer {
 public static void main(String[] args) throws Exception {Path d=Path.of(args.length>0?args[0]:"data/kaggle"); SoccerService service=new SoccerService(SoccerRepository.load(d));try(BufferedReader in=new BufferedReader(new InputStreamReader(System.in));PrintWriter out=new PrintWriter(System.out,true)){for(String line;(line=in.readLine())!=null;){if(line.isBlank())continue;String reply=handle(line,service);if(reply!=null)out.println(reply);}}}
 /** Handles one JSON-RPC message. A null return is a notification, for which MCP requires no response. */
 static String handle(String line,SoccerService service){
   Object parsed;
   try { parsed=Json.parse(line); } catch(Exception e) { return Json.write(error(null,-32700,"Parse error")); }
   if(!(parsed instanceof Map<?,?> raw)) return Json.write(error(null,-32600,"Invalid Request"));
   Map<String,Object> request=map(raw); boolean notification=!request.containsKey("id"); Object id=request.get("id");
   try { return notification ? notification(request,service) : Json.write(response(request,service)); }
   catch(RpcException e) { return notification?null:Json.write(error(id,e.code,e.getMessage())); }
   catch(Exception e) { return notification?null:Json.write(error(id,-32603,"Internal error: "+message(e))); }
 }
 static String notification(Map<String,Object> request,SoccerService service) {
   // MCP clients send notifications/initialized after initialize.  It is deliberately ignored.
   if("notifications/initialized".equals(request.get("method"))) return null;
   // Unknown notifications are ignored per JSON-RPC; never let a client notification kill stdio.
   return null;
 }
 static Map<String,Object> response(Map<String,Object> request,SoccerService s){
   if(!"2.0".equals(request.get("jsonrpc")))throw new RpcException(-32600,"Invalid Request");
   Object id=request.get("id"); Object methodValue=request.get("method");
   if(!(methodValue instanceof String method)||method.isBlank())throw new RpcException(-32600,"Invalid Request");
   Map<String,Object> p=map(request.get("params"));Object result=switch(method){case "initialize"->Map.of("protocolVersion","2024-11-05","capabilities",Map.of("tools",Map.of("listChanged",false)),"serverInfo",Map.of("name","brazilian-soccer","version","1.0.0"));case "tools/list"->Map.of("tools",tools());case "tools/call"->call(str(p,"name"),map(p.get("arguments")),s);default->throw new RpcException(-32601,"Method not found: "+method);};return envelope(id,"result",result);}
 static Map<String,Object> envelope(Object id,String key,Object value){Map<String,Object> result=new LinkedHashMap<>();result.put("jsonrpc","2.0");result.put("id",id);result.put(key,value);return result;}
 static Map<String,Object> error(Object id,int code,String message){return envelope(id,"error",Map.of("code",code,"message",message));}
 static String message(Exception e){return e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();}
 static final class RpcException extends RuntimeException { final int code; RpcException(int code,String message){super(message);this.code=code;} }
 static Object call(String name,Map<String,Object> p,SoccerService s){Object data=switch(name){case "search_matches"->s.matches(str(p,"team"),str(p,"opponent"),str(p,"competition"),integer(p,"season"),str(p,"from"),str(p,"to"),number(p,"limit",50));case "team_statistics"->s.teamStatistics(required(p,"team"),str(p,"competition"),integer(p,"season"),bool(p,"home_only"));case "head_to_head"->s.headToHead(required(p,"team"),required(p,"opponent"),str(p,"competition"),integer(p,"season"));case "search_players"->s.repository.findPlayers(str(p,"name"),str(p,"nationality"),str(p,"club"),str(p,"position"),number(p,"limit",50));case "standings"->s.standings(str(p,"competition"),requiredInteger(p,"season"));case "competition_statistics"->s.competitionStatistics(str(p,"competition"),integer(p,"season"));default->throw new RpcException(-32602,"Unknown tool: "+name);};return Map.of("content",List.of(Map.of("type","text","text",Json.write(data))),"structuredContent",Map.of("data",data));}
 static List<Map<String,Object>> tools(){return List.of(tool("search_matches","Search matches across all supplied match datasets.","team","opponent","competition","season","from","to","limit"),tool("team_statistics","Calculate a team's record, goals and win rate.","team","competition","season","home_only"),tool("head_to_head","Compare two teams' head-to-head record.","team","opponent","competition","season"),tool("search_players","Search the FIFA player database.","name","nationality","club","position","limit"),tool("standings","Calculate a season table from match results.","competition","season"),tool("competition_statistics","Aggregate goal and outcome statistics.","competition","season"));}
 static Map<String,Object> tool(String n,String d,String... props){Map<String,Object> x=new LinkedHashMap<>();for(String p:props)x.put(p,Map.of("type",p.equals("season")||p.equals("limit")?"integer":p.equals("home_only")?"boolean":"string"));return Map.of("name",n,"description",d,"inputSchema",Map.of("type","object","properties",x));}
 @SuppressWarnings("unchecked") static Map<String,Object> map(Object x){return x instanceof Map<?,?> m?(Map<String,Object>)m:Map.of();}static String str(Map<String,Object>p,String k){Object x=p.get(k);return x==null?null:String.valueOf(x);}static String required(Map<String,Object>p,String k){String s=str(p,k);if(s==null||s.isBlank())throw new RpcException(-32602,"Missing required argument: "+k);return s;}static Integer integer(Map<String,Object>p,String k){Object x=p.get(k);try{return x instanceof Number n?n.intValue():x==null?null:Integer.valueOf(x.toString());}catch(NumberFormatException e){throw new RpcException(-32602,"Invalid integer argument: "+k);}}static int requiredInteger(Map<String,Object>p,String k){Integer value=integer(p,k);if(value==null)throw new RpcException(-32602,"Missing required argument: "+k);return value;}static int number(Map<String,Object>p,String k,int d){Integer i=integer(p,k);return i==null?d:i;}static boolean bool(Map<String,Object>p,String k){return Boolean.parseBoolean(str(p,k));}
}
