package org.brazilsoccer.mcp;

import java.io.IOException;
import java.nio.file.*;
import java.time.*;
import java.time.format.*;
import java.util.*;
import java.util.stream.*;

/** In-memory, read-only view of every supplied data file. */
public final class SoccerRepository {
  private final List<Match> matches; private final List<Map<String,String>> players;
  private SoccerRepository(List<Match> m,List<Map<String,String>> p){matches=List.copyOf(m);players=List.copyOf(p);}
  public static SoccerRepository load(Path data) throws IOException {
    List<Match> all=new ArrayList<>();
    add(all,Csv.read(data.resolve("Brasileirao_Matches.csv")),"Brasileirão", "datetime","home_team","away_team","home_goal","away_goal","season","round","stage");
    add(all,Csv.read(data.resolve("Brazilian_Cup_Matches.csv")),"Copa do Brasil", "datetime","home_team","away_team","home_goal","away_goal","season","round","stage");
    add(all,Csv.read(data.resolve("Libertadores_Matches.csv")),"Libertadores", "datetime","home_team","away_team","home_goal","away_goal","season","round","stage");
    add(all,Csv.read(data.resolve("BR-Football-Dataset.csv")),null, "date","home","away","home_goal","away_goal",null,null,null);
    add(all,Csv.read(data.resolve("novo_campeonato_brasileiro.csv")),"Brasileirão", "Data","Equipe_mandante","Equipe_visitante","Gols_mandante","Gols_visitante","Ano","Rodada",null);
    return new SoccerRepository(all,Csv.read(data.resolve("fifa_data.csv")));
  }
  private static void add(List<Match> out,List<Map<String,String>> rows,String fixed,String date,String home,String away,String hg,String ag,String season,String round,String stage){
    for(Map<String,String> r:rows) { Integer h=integer(r.get(hg)), a=integer(r.get(ag)); if(h==null||a==null) continue; LocalDate d=date(r.get(date)); String comp=fixed!=null?fixed:blank(r.get("tournament"),"Unknown"); out.add(new Match(comp,d,r.get(home),r.get(away),h,a, season==null?(d==null?null:d.getYear()):integer(r.get(season)), round==null?null:r.get(round),stage==null?null:r.get(stage))); }
  }
  private static String blank(String s,String fallback){return s==null||s.isBlank()?fallback:s;}
  static Integer integer(String s){try{return s==null||s.isBlank()?null:(int)Double.parseDouble(s.trim());}catch(NumberFormatException e){return null;}}
  static LocalDate date(String s){if(s==null||s.isBlank())return null; for(DateTimeFormatter f:List.of(DateTimeFormatter.ISO_LOCAL_DATE,DateTimeFormatter.ofPattern("d/M/uuuu"))){try{return LocalDate.parse(s.length()>=10?s.substring(0,10):s,f);}catch(DateTimeParseException ignored){}} return null;}
  public List<Match> matches(){return matches;}
  public List<Match> findMatches(String team,String opponent,String competition,Integer season,LocalDate from,LocalDate to,int limit){return matches.stream().filter(m->team==null||m.involves(team)).filter(m->opponent==null||(m.involves(opponent)&&((team==null)||((Names.same(m.home(),team)&&Names.same(m.away(),opponent))||(Names.same(m.away(),team)&&Names.same(m.home(),opponent)))))).filter(m->competition==null||Names.normalize(m.competition()).contains(Names.normalize(competition))).filter(m->m.season()==null||season==null||m.season().equals(season)).filter(m->from==null||m.date()==null||!m.date().isBefore(from)).filter(m->to==null||m.date()==null||!m.date().isAfter(to)).sorted(Comparator.comparing(Match::date,Comparator.nullsLast(Comparator.reverseOrder()))).limit(Math.max(1,Math.min(limit,500))).toList();}
  public List<Map<String,String>> findPlayers(String name,String nationality,String club,String position,int limit){return players.stream().filter(p->contains(p.get("Name"),name)).filter(p->contains(p.get("Nationality"),nationality)).filter(p->contains(p.get("Club"),club)).filter(p->contains(p.get("Position"),position)).sorted(Comparator.comparing((Map<String,String> p)->integer(p.get("Overall")),Comparator.nullsLast(Comparator.reverseOrder()))).limit(Math.max(1,Math.min(limit,500))).toList();}
  private static boolean contains(String v,String q){return q==null||q.isBlank()||Names.normalize(v).contains(Names.normalize(q));}
}
