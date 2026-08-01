package com.brazilsoccer.mcp;

import java.io.*;import java.nio.file.*;import java.time.*;import java.time.format.*;import java.util.*;

/** Immutable in-memory view of all supplied Kaggle CSV files. */
public final class SoccerRepository {
  private final List<Match> matches; private final List<Player> players;
  private SoccerRepository(List<Match> matches,List<Player> players){this.matches=List.copyOf(matches);this.players=List.copyOf(players);}
  public static SoccerRepository load(Path dataDir) throws IOException {
    List<Match> all=new ArrayList<>();
    add(all,Csv.read(dataDir.resolve("Brasileirao_Matches.csv")),"Brasileirão","datetime","home_team","away_team","home_goal","away_goal","season","round");
    add(all,Csv.read(dataDir.resolve("Brazilian_Cup_Matches.csv")),"Copa do Brasil","datetime","home_team","away_team","home_goal","away_goal","season","round");
    add(all,Csv.read(dataDir.resolve("Libertadores_Matches.csv")),"Libertadores","datetime","home_team","away_team","home_goal","away_goal","season","stage");
    add(all,Csv.read(dataDir.resolve("BR-Football-Dataset.csv")),null,"date","home","away","home_goal","away_goal",null,"tournament");
    add(all,Csv.read(dataDir.resolve("novo_campeonato_brasileiro.csv")),"Brasileirão","Data","Equipe_mandante","Equipe_visitante","Gols_mandante","Gols_visitante","Ano","Rodada");
    List<Player> ps=new ArrayList<>();for(Map<String,String> r:Csv.read(dataDir.resolve("fifa_data.csv")))ps.add(new Player(v(r,"ID"),v(r,"Name"),v(r,"Nationality"),integer(v(r,"Age")),integer(v(r,"Overall")),integer(v(r,"Potential")),v(r,"Club"),v(r,"Position")));
    return new SoccerRepository(all,ps);
  }
  private static void add(List<Match> out,List<Map<String,String>> rows,String fixed,String date,String home,String away,String hg,String ag,String season,String round){for(Map<String,String> r:rows){String comp=fixed==null?v(r,"tournament"):fixed;out.add(new Match(comp,parseDate(v(r,date)),v(r,home),v(r,away),integer(v(r,hg)),integer(v(r,ag)),season==null?guessSeason(v(r,date)):v(r,season),v(r,round),Map.copyOf(r)));}}
  private static String guessSeason(String d){LocalDate x=parseDate(d);return x==null?"":String.valueOf(x.getYear());}
  static LocalDate parseDate(String text){if(text==null||text.isBlank())return null;String s=text.trim();for(DateTimeFormatter f:List.of(DateTimeFormatter.ISO_LOCAL_DATE,DateTimeFormatter.ofPattern("d/M/uuuu"),DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss"))){try{return s.length()>10&&f.toString().contains("HourOfDay")?LocalDateTime.parse(s,f).toLocalDate():LocalDate.parse(s,f);}catch(DateTimeParseException ignored){}}return null;}
  private static Integer integer(String v){try{return v==null||v.isBlank()?null:(int)Double.parseDouble(v);}catch(NumberFormatException e){return null;}}
  private static String v(Map<String,String> m,String key){return m.getOrDefault(key,"").trim();}
  public List<Match> matches(){return matches;} public List<Player> players(){return players;}
}
