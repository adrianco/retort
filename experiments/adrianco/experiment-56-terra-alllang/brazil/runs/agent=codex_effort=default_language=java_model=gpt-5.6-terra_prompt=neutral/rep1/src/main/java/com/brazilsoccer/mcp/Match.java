package com.brazilsoccer.mcp;
import java.time.*;import java.util.*;
public record Match(String competition, LocalDate date, String home, String away, Integer homeGoals, Integer awayGoals, String season, String round, Map<String,String> extras) {
  boolean involves(String team){return TeamNames.matches(home,team)||TeamNames.matches(away,team);}
  int goalDifference(){return homeGoals==null||awayGoals==null?-1:Math.abs(homeGoals-awayGoals);}
}
