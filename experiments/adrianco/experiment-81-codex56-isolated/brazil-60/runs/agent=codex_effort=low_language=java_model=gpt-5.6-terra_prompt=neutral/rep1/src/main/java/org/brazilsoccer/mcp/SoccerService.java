package org.brazilsoccer.mcp;

import java.time.LocalDate;
import java.util.*;

/** Query and aggregation operations exposed by the MCP transport. */
public final class SoccerService {
  final SoccerRepository repository;
  public SoccerService(SoccerRepository repository){this.repository=repository;}
  public List<Match> matches(String team,String opponent,String competition,Integer season,String from,String to,int limit){return repository.findMatches(team,opponent,competition,season,parseDate(from),parseDate(to),limit);}
  public Map<String,Object> teamStatistics(String team,String competition,Integer season,boolean homeOnly){
    int won=0,drawn=0,lost=0,goalsFor=0,goalsAgainst=0;
    for(Match m:distinct(matches(team,null,competition,season,null,null,10000))){ boolean home=Names.same(m.home(),team); if(homeOnly&&!home)continue; int f=home?m.homeGoals():m.awayGoals(), a=home?m.awayGoals():m.homeGoals(); goalsFor+=f;goalsAgainst+=a;if(f>a)won++;else if(f==a)drawn++;else lost++; }
    int played=won+drawn+lost; Map<String,Object> r=new LinkedHashMap<>();r.put("team",team);r.put("matches",played);r.put("wins",won);r.put("draws",drawn);r.put("losses",lost);r.put("goalsFor",goalsFor);r.put("goalsAgainst",goalsAgainst);r.put("points",won*3+drawn);r.put("winRate",played==0?0:round(100.0*won/played));return r;
  }
  public Map<String,Object> headToHead(String first,String second,String competition,Integer season){
    int fw=0,sw=0,d=0; List<Match> games=distinct(matches(first,second,competition,season,null,null,10000));
    for(Match m:games){int fg=Names.same(m.home(),first)?m.homeGoals():m.awayGoals();int sg=Names.same(m.home(),second)?m.homeGoals():m.awayGoals();if(fg>sg)fw++;else if(fg<sg)sw++;else d++;}
    Map<String,Object> r=new LinkedHashMap<>();r.put("team",first);r.put("opponent",second);r.put("matches",games.size());r.put("teamWins",fw);r.put("opponentWins",sw);r.put("draws",d);r.put("recentMatches",games);return r;
  }
  public List<Map<String,Object>> standings(String competition,int season){
    Map<String,int[]> table=new HashMap<>(); for(Match m:distinct(matches(null,null,competition,season,null,null,10000))){ if(m.season()==null||m.season()!=season)continue; apply(table,m.home(),m.homeGoals(),m.awayGoals());apply(table,m.away(),m.awayGoals(),m.homeGoals()); }
    List<Map<String,Object>> result=new ArrayList<>();table.entrySet().stream().sorted((a,b)->{int[]x=a.getValue(),y=b.getValue();int c=Integer.compare(y[0],x[0]);return c!=0?c:Integer.compare(y[4]-y[5],x[4]-x[5]);}).forEach(e->{int[]v=e.getValue();Map<String,Object> x=new LinkedHashMap<>();x.put("team",e.getKey());x.put("points",v[0]);x.put("played",v[1]);x.put("wins",v[2]);x.put("draws",v[3]);x.put("goalsFor",v[4]);x.put("goalsAgainst",v[5]);result.add(x);});return result;
  }
  private static void apply(Map<String,int[]> t,String team,int goals,int against){int[]v=t.computeIfAbsent(team,k->new int[6]);v[1]++;v[4]+=goals;v[5]+=against;if(goals>against){v[0]+=3;v[2]++;}else if(goals==against){v[0]++;v[3]++;}}
  public Map<String,Object> competitionStatistics(String competition,Integer season){List<Match> games=distinct(matches(null,null,competition,season,null,null,10000));int hw=0,d=0,g=0;for(Match m:games){g+=m.homeGoals()+m.awayGoals();if(m.homeGoals()>m.awayGoals())hw++;if(m.homeGoals()==m.awayGoals())d++;}return Map.of("competition",competition==null?"all":competition,"matches",games.size(),"goals",g,"averageGoals",games.isEmpty()?0:round((double)g/games.size()),"homeWinRate",games.isEmpty()?0:round(100.0*hw/games.size()),"drawRate",games.isEmpty()?0:round(100.0*d/games.size()));}
  /** The historical Brasileirão source overlaps the newer source; count a fixture once in aggregates. */
  private static List<Match> distinct(List<Match> matches){Map<String,Match> unique=new LinkedHashMap<>();for(Match m:matches){String key=Names.normalize(m.competition())+"|"+m.date()+"|"+Names.normalize(m.home())+"|"+Names.normalize(m.away())+"|"+m.homeGoals()+"|"+m.awayGoals();unique.putIfAbsent(key,m);}return List.copyOf(unique.values());}
  private static LocalDate parseDate(String s){return SoccerRepository.date(s);} private static double round(double n){return Math.round(n*100.0)/100.0;}
}
