package org.brazilsoccer.mcp;
import java.time.*;

public record Match(String competition, LocalDate date, String home, String away, int homeGoals, int awayGoals, Integer season, String round, String stage) {
  public boolean involves(String team) { String n=Names.normalize(team); return Names.normalize(home).contains(n) || Names.normalize(away).contains(n); }
}
