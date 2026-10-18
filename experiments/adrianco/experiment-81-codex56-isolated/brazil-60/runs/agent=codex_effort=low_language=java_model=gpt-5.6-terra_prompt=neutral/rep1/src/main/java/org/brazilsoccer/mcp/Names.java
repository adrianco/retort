package org.brazilsoccer.mcp;
import java.text.Normalizer;

public final class Names {
  private Names() {}
  /** Removes accents, state suffixes and common club-name noise for cross-file matching. */
  public static String normalize(String value) {
    if(value==null) return "";
    String s=Normalizer.normalize(value, Normalizer.Form.NFD).replaceAll("\\p{M}","").toLowerCase();
    s=s.replaceAll("\\s*-\\s*(sp|rj|mg|rs|pr|sc|ba|pe|ce|go|df|pa|am|mt|ms|es|al|pb|rn|se|ma|pi|ro|ac|ap|to)\\b", "");
    s=s.replaceAll("\\b(sport club|clube|esporte clube|football club|futebol clube|sociedade esportiva|associacao)\\b", " ");
    return s.replaceAll("[^a-z0-9]+", " ").trim().replaceAll("\\s+", " ");
  }
  public static boolean same(String a,String b) { String x=normalize(a), y=normalize(b); return x.equals(y) || (!x.isEmpty() && (x.contains(y)||y.contains(x))); }
}
