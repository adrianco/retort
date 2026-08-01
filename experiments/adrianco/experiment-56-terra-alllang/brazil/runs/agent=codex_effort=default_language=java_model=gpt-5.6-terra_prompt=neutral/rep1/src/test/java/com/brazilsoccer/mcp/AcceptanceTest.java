package com.brazilsoccer.mcp;

import java.nio.file.*;import java.time.*;import java.util.*;

/** Dependency-free Given/When/Then acceptance tests; run with `mvn test` via exec plugin or javac command below. */
public final class AcceptanceTest {
  public static void main(String[] args) throws Exception {
    // Given all supplied datasets are loaded
    SoccerRepository repo=SoccerRepository.load(Path.of("data/kaggle")); SoccerService soccer=new SoccerService(repo);
    check(repo.matches().size()>20000,"all five match files should load"); check(repo.players().size()>18000,"FIFA player file should load");
    // When a user searches normalized names; Then score, date and competition are returned.
    List<Match> fla= soccer.findMatches("Flamengo-RJ",null,null,null,null,null,30);
    check(!fla.isEmpty()&&fla.stream().allMatch(m->m.homeGoals()!=null&&m.awayGoals()!=null&&!m.competition().isBlank()),"team lookup should return complete matches");
    // When team statistics are requested; Then W/D/L and goals reconcile with matches.
    SoccerService.TeamStats stats=soccer.teamStats("Palmeiras", "2023", "Brasileirão", false);
    check(stats.matches()==stats.wins()+stats.draws()+stats.losses(),"record must reconcile");
    // When two teams are compared; Then each result has one outcome.
    SoccerService.HeadToHead h=soccer.headToHead("Flamengo","Fluminense",null,"Brasileirão"); check(h.matches()>0&&h.matches()==h.firstWins()+h.secondWins()+h.draws(),"head-to-head must reconcile");
    // When a season is tabled; Then the table is ordered by points.
    List<SoccerService.Standing> table=soccer.standings("2019","Brasileirão"); check(!table.isEmpty()&&table.get(0).points()>=table.get(table.size()-1).points(),"standings must be sorted");
    // When a player filter is applied; Then every returned player satisfies it.
    List<Player> brazil=soccer.findPlayers(null,"Brazil",null,null,100);check(!brazil.isEmpty()&&brazil.stream().allMatch(p->TeamNames.normalize(p.nationality()).contains("brazil")),"player nationality filter must work");
    check(TeamNames.matches("São Paulo-SP","sao paulo")&&TeamNames.matches("Flamengo-RJ","Flamengo"),"accent and state variants must match");
    System.out.println("Acceptance tests passed");
  }
  private static void check(boolean ok,String msg){if(!ok)throw new AssertionError(msg);}
}
