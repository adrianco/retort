package com.brazilsoccer.mcp;
import java.text.Normalizer;import java.util.*;

/** Normalizes accents, state suffixes, and common long club names before matching. */
public final class TeamNames {
  private static final Map<String,String> ALIASES=Map.ofEntries(Map.entry("sport club corinthians paulista","corinthians"),Map.entry("sao paulo futebol clube","sao paulo"),Map.entry("club de regatas flamengo","flamengo"),Map.entry("sociedade esportiva palmeiras","palmeiras"),Map.entry("fluminense football club","fluminense"),Map.entry("gremio foot ball porto alegrense","gremio"));
  private TeamNames(){}
  public static String normalize(String value){if(value==null)return "";String s=Normalizer.normalize(value,Normalizer.Form.NFD).replaceAll("\\p{M}","").toLowerCase(Locale.ROOT).replaceAll("\\([^)]*\\)"," ").replaceAll("\\s*-\\s*(sp|rj|mg|rs|pr|sc|ba|pe|ce|go|df|pa|am|es|mt|ms|al|pb|rn|se|ma|pi|to|ro|ac|ap)\\b"," ").replaceAll("[^a-z0-9 ]"," ").replaceAll("\\s+"," ").trim();return ALIASES.getOrDefault(s,s);}
  public static boolean matches(String stored,String query){String a=normalize(stored),b=normalize(query);return !b.isBlank()&&(a.equals(b)||a.contains(b)||b.contains(a));}
}
