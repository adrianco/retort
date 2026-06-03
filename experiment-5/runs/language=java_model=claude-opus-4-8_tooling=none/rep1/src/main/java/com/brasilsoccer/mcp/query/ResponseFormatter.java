/*
 * ============================================================================
 * ResponseFormatter - renders query results as human-readable text
 * ============================================================================
 * Context:
 *   MCP tool calls return text content for an LLM to consume. This class turns
 *   the structured Results records into the readable, example-style output shown
 *   in the specification (match lists with scores and competition, standings
 *   tables, head-to-head summaries, player rankings, etc.).
 *
 *   Kept separate from both the query engine and the transport so it can be unit
 *   tested directly and reused by any front end.
 * ============================================================================
 */
package com.brasilsoccer.mcp.query;

import com.brasilsoccer.mcp.model.Match;
import com.brasilsoccer.mcp.model.Player;

import java.util.List;
import java.util.Locale;

public final class ResponseFormatter {

    private ResponseFormatter() {
    }

    public static String matchSearch(Results.MatchSearch r) {
        if (r.matches().isEmpty()) {
            return "No matches found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(r.totalFound()).append(" match")
                .append(r.totalFound() == 1 ? "" : "es");
        if (r.matches().size() < r.totalFound()) {
            sb.append(" (showing ").append(r.matches().size()).append(")");
        }
        sb.append(":\n");
        for (Match m : r.matches()) {
            sb.append("- ").append(matchLine(m)).append("\n");
        }
        if (r.headToHead() != null) {
            sb.append("\n").append(headToHead(r.headToHead()));
        }
        return sb.toString().stripTrailing();
    }

    public static String matchLine(Match m) {
        StringBuilder sb = new StringBuilder();
        sb.append(m.date() == null ? "????-??-??" : m.date()).append(": ");
        sb.append(m.homeTeam()).append(" ").append(m.homeGoal())
                .append("-").append(m.awayGoal()).append(" ").append(m.awayTeam());
        sb.append(" (").append(m.competition());
        if (m.season() != null) {
            sb.append(" ").append(m.season());
        }
        if (m.round() != null) {
            sb.append(", Round ").append(m.round());
        }
        if (m.stage() != null) {
            sb.append(", ").append(m.stage());
        }
        sb.append(")");
        return sb.toString();
    }

    public static String headToHead(Results.HeadToHead h) {
        StringBuilder sb = new StringBuilder();
        sb.append("Head-to-head: ").append(h.team1()).append(" vs ").append(h.team2()).append("\n");
        sb.append("Total meetings: ").append(h.total()).append("\n");
        sb.append(h.team1()).append(" wins: ").append(h.team1Wins())
                .append(" | ").append(h.team2()).append(" wins: ").append(h.team2Wins())
                .append(" | Draws: ").append(h.draws()).append("\n");
        sb.append("Goals: ").append(h.team1()).append(" ").append(h.team1Goals())
                .append(" - ").append(h.team2Goals()).append(" ").append(h.team2());
        return sb.toString();
    }

    public static String teamRecord(Results.TeamRecord t) {
        StringBuilder sb = new StringBuilder();
        sb.append(t.team()).append(" record");
        if (!"all".equals(t.venue())) {
            sb.append(" (").append(t.venue()).append(" only)");
        }
        if (t.competition() != null || t.season() != null) {
            sb.append(" [");
            if (t.competition() != null) {
                sb.append(t.competition());
            }
            if (t.season() != null) {
                sb.append(t.competition() != null ? " " : "").append(t.season());
            }
            sb.append("]");
        }
        sb.append(":\n");
        sb.append("- Matches: ").append(t.played()).append("\n");
        sb.append("- Wins: ").append(t.wins())
                .append(", Draws: ").append(t.draws())
                .append(", Losses: ").append(t.losses()).append("\n");
        sb.append("- Goals For: ").append(t.goalsFor())
                .append(", Goals Against: ").append(t.goalsAgainst())
                .append(" (GD ").append(signed(t.goalDifference())).append(")").append("\n");
        sb.append("- Points: ").append(t.points()).append("\n");
        sb.append("- Win rate: ").append(pct(t.winRate()));
        return sb.toString();
    }

    public static String standings(Results.Standings s) {
        if (s.rows().isEmpty()) {
            return "No standings available for " + s.competition() + " " + s.season() + ".";
        }
        StringBuilder sb = new StringBuilder();
        sb.append(s.season()).append(" ").append(s.competition())
                .append(" - Final Standings (calculated from matches):\n");
        sb.append(String.format("%-4s %-26s %3s %3s %3s %3s %4s %4s %4s %4s%n",
                "Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"));
        for (Results.StandingRow r : s.rows()) {
            sb.append(String.format("%-4d %-26s %3d %3d %3d %3d %4d %4d %4d %4d%n",
                    r.position(), truncate(r.team(), 26), r.played(), r.wins(), r.draws(),
                    r.losses(), r.goalsFor(), r.goalsAgainst(), r.goalDifference(), r.points()));
        }
        if (!s.rows().isEmpty()) {
            sb.append("Champion: ").append(s.rows().get(0).team());
        }
        return sb.toString().stripTrailing();
    }

    public static String leagueStats(Results.LeagueStats s) {
        StringBuilder sb = new StringBuilder();
        sb.append("Statistics for ").append(s.competition());
        if (s.season() != null) {
            sb.append(" ").append(s.season());
        }
        sb.append(":\n");
        sb.append("- Matches analysed: ").append(s.matches()).append("\n");
        sb.append("- Total goals: ").append(s.totalGoals()).append("\n");
        sb.append("- Average goals per match: ")
                .append(String.format(Locale.US, "%.2f", s.avgGoalsPerMatch())).append("\n");
        sb.append("- Home wins: ").append(s.homeWins())
                .append(" (").append(pct(s.homeWinRate())).append(")\n");
        sb.append("- Away wins: ").append(s.awayWins())
                .append(" (").append(pct(s.awayWinRate())).append(")\n");
        sb.append("- Draws: ").append(s.draws())
                .append(" (").append(pct(s.drawRate())).append(")");
        return sb.toString();
    }

    public static String biggestWins(List<Match> matches, String label) {
        if (matches.isEmpty()) {
            return "No matches found.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Biggest victories").append(label == null ? "" : " (" + label + ")").append(":\n");
        int i = 1;
        for (Match m : matches) {
            sb.append(i++).append(". ").append(matchLine(m))
                    .append(" [margin ").append(m.margin()).append("]\n");
        }
        return sb.toString().stripTrailing();
    }

    public static String players(Results.PlayerSearch r, String heading) {
        if (r.players().isEmpty()) {
            return "No players found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        if (heading != null) {
            sb.append(heading).append("\n");
        }
        sb.append("Found ").append(r.totalFound()).append(" player")
                .append(r.totalFound() == 1 ? "" : "s");
        if (r.players().size() < r.totalFound()) {
            sb.append(" (showing ").append(r.players().size()).append(")");
        }
        sb.append(":\n");
        int i = 1;
        for (Player p : r.players()) {
            sb.append(i++).append(". ").append(p.name())
                    .append(" - Overall: ").append(p.overall())
                    .append(", Potential: ").append(p.potential())
                    .append(", Position: ").append(p.position().isEmpty() ? "?" : p.position())
                    .append(", Age: ").append(p.age())
                    .append(", Nationality: ").append(p.nationality())
                    .append(", Club: ").append(p.club().isEmpty() ? "Free agent" : p.club())
                    .append("\n");
        }
        return sb.toString().stripTrailing();
    }

    public static String summary(Results.Summary s) {
        StringBuilder sb = new StringBuilder();
        sb.append("Brazilian Soccer Knowledge Base\n");
        sb.append("- Matches loaded: ").append(s.totalMatches()).append("\n");
        sb.append("- Players loaded: ").append(s.totalPlayers()).append("\n");
        sb.append("- Competitions: ").append(String.join(", ", s.competitions())).append("\n");
        if (!s.seasons().isEmpty()) {
            sb.append("- Seasons: ").append(s.seasons().get(0)).append("-")
                    .append(s.seasons().get(s.seasons().size() - 1));
        }
        return sb.toString().stripTrailing();
    }

    // -------------------------------------------------------------- small helpers

    private static String pct(double v) {
        return String.format(Locale.US, "%.1f%%", v);
    }

    private static String signed(int v) {
        return v > 0 ? "+" + v : Integer.toString(v);
    }

    private static String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max - 1) + "…";
    }
}
