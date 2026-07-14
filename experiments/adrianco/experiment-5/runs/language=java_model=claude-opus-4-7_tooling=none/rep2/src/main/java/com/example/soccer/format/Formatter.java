package com.example.soccer.format;

import com.example.soccer.data.Match;
import com.example.soccer.data.Player;
import com.example.soccer.data.TeamNames;
import com.example.soccer.query.QueryService;
import com.example.soccer.query.TeamRecord;

import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class Formatter {

    private Formatter() {}

    public static String formatMatches(List<Match> matches, int limit) {
        if (matches.isEmpty()) return "No matches found.";
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(matches.size()).append(" match")
                .append(matches.size() == 1 ? "" : "es").append(".\n");
        int n = Math.min(limit, matches.size());
        for (int i = 0; i < n; i++) {
            sb.append("- ").append(formatMatchLine(matches.get(i))).append('\n');
        }
        if (matches.size() > n) {
            sb.append("... (").append(matches.size() - n).append(" more)\n");
        }
        return sb.toString();
    }

    public static String formatMatchLine(Match m) {
        StringBuilder sb = new StringBuilder();
        sb.append(m.date() == null ? "????-??-??" : m.date().toString())
                .append(": ")
                .append(TeamNames.canonical(m.homeTeam()))
                .append(' ')
                .append(m.homeGoal() == null ? "?" : m.homeGoal())
                .append('-')
                .append(m.awayGoal() == null ? "?" : m.awayGoal())
                .append(' ')
                .append(TeamNames.canonical(m.awayTeam()))
                .append(" (")
                .append(m.competition());
        if (m.round() != null) sb.append(" R").append(m.round());
        if (m.stage() != null) sb.append(" - ").append(m.stage());
        sb.append(')');
        return sb.toString();
    }

    public static String formatTeamRecord(String label, TeamRecord rec) {
        StringBuilder sb = new StringBuilder();
        sb.append(label).append('\n');
        sb.append("- Matches: ").append(rec.matches).append('\n');
        sb.append("- Wins: ").append(rec.wins)
                .append(", Draws: ").append(rec.draws)
                .append(", Losses: ").append(rec.losses).append('\n');
        sb.append("- Goals For: ").append(rec.goalsFor)
                .append(", Goals Against: ").append(rec.goalsAgainst)
                .append(", Diff: ").append(rec.goalDifference()).append('\n');
        sb.append("- Points: ").append(rec.points()).append('\n');
        sb.append(String.format(Locale.ROOT, "- Win rate: %.1f%%%n", rec.winRate() * 100));
        return sb.toString();
    }

    public static String formatHeadToHead(QueryService.HeadToHead h, int matchLimit) {
        StringBuilder sb = new StringBuilder();
        sb.append("Head-to-head: ").append(h.teamA).append(" vs ").append(h.teamB).append('\n');
        sb.append("- ").append(h.teamA).append(" wins: ").append(h.winsA).append('\n');
        sb.append("- ").append(h.teamB).append(" wins: ").append(h.winsB).append('\n');
        sb.append("- Draws: ").append(h.draws).append('\n');
        sb.append("- Goals: ").append(h.teamA).append(' ').append(h.goalsA)
                .append(" - ").append(h.goalsB).append(' ').append(h.teamB).append('\n');
        if (!h.matches.isEmpty()) {
            sb.append("Matches:\n");
            int n = Math.min(matchLimit, h.matches.size());
            for (int i = 0; i < n; i++) {
                sb.append("- ").append(formatMatchLine(h.matches.get(i))).append('\n');
            }
            if (h.matches.size() > n) {
                sb.append("... (").append(h.matches.size() - n).append(" more)\n");
            }
        }
        return sb.toString();
    }

    public static String formatStandings(List<QueryService.Standing> standings, int limit) {
        if (standings.isEmpty()) return "No standings available.";
        StringBuilder sb = new StringBuilder();
        sb.append("Standings (calculated from matches):\n");
        int n = Math.min(limit, standings.size());
        for (int i = 0; i < n; i++) {
            QueryService.Standing s = standings.get(i);
            TeamRecord r = s.record;
            sb.append(String.format(Locale.ROOT,
                    "%2d. %s - %d pts (%dW %dD %dL, GF %d, GA %d, GD %+d)%n",
                    i + 1, s.team, r.points(), r.wins, r.draws, r.losses,
                    r.goalsFor, r.goalsAgainst, r.goalDifference()));
        }
        if (standings.size() > n) {
            sb.append("... (").append(standings.size() - n).append(" more)\n");
        }
        return sb.toString();
    }

    public static String formatPlayers(List<Player> players, int limit) {
        if (players.isEmpty()) return "No players found.";
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(players.size()).append(" player")
                .append(players.size() == 1 ? "" : "s").append(".\n");
        int n = Math.min(limit, players.size());
        for (int i = 0; i < n; i++) {
            Player p = players.get(i);
            sb.append(String.format(Locale.ROOT,
                    "%2d. %s - Overall: %s, Position: %s, Club: %s, Nationality: %s%n",
                    i + 1,
                    p.name(),
                    p.overall() == null ? "?" : p.overall().toString(),
                    p.position() == null ? "?" : p.position(),
                    p.club() == null ? "?" : p.club(),
                    p.nationality() == null ? "?" : p.nationality()));
        }
        if (players.size() > n) {
            sb.append("... (").append(players.size() - n).append(" more)\n");
        }
        return sb.toString();
    }

    public static String formatStats(Map<String, Object> stats) {
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, Object> e : stats.entrySet()) {
            Object v = e.getValue();
            if (v instanceof Double d) {
                sb.append(e.getKey()).append(": ")
                        .append(String.format(Locale.ROOT, "%.3f", d)).append('\n');
            } else {
                sb.append(e.getKey()).append(": ").append(v).append('\n');
            }
        }
        return sb.toString();
    }
}
