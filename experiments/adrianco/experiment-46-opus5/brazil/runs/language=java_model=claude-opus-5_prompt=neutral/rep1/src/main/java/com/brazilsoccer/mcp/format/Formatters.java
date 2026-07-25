package com.brazilsoccer.mcp.format;

import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.List;
import java.util.Locale;

/**
 * Rendering helpers shared by the MCP tools.
 *
 * <p>Tool results are plain text on purpose: an LLM consumes them directly, and the format follows
 * the examples of the specification ("2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)").
 */
public final class Formatters {

    private Formatters() {
    }

    /** One match as a single line, with date, score and competition context. */
    public static String matchLine(KnowledgeGraph graph, Match match) {
        StringBuilder line = new StringBuilder();
        line.append(match.date() == null ? "date unknown" : match.date().toString()).append(": ");
        line.append(graph.nameOf(match.homeTeamId())).append(' ');
        line.append(match.isPlayed() ? match.homeGoals() + "-" + match.awayGoals() : "vs");
        line.append(' ').append(graph.nameOf(match.awayTeamId()));
        line.append(" (").append(match.competition().displayName()).append(' ').append(match.season());
        if (match.round() != null && !match.round().isBlank()) {
            line.append(isNumeric(match.round()) ? ", round " + match.round() : ", " + match.round());
        }
        line.append(')');
        if (match.arena() != null) {
            line.append(" @ ").append(match.arena());
        }
        return line.toString();
    }

    /** Several matches as a bullet list, with an ellipsis line when truncated. */
    public static String matchList(KnowledgeGraph graph, List<Match> matches, int total) {
        if (matches.isEmpty()) {
            return "  (no matches)";
        }
        StringBuilder builder = new StringBuilder();
        for (Match match : matches) {
            builder.append("- ").append(matchLine(graph, match)).append('\n');
        }
        int remaining = total - matches.size();
        if (remaining > 0) {
            builder.append("- ... (").append(remaining)
                    .append(remaining == 1 ? " more match" : " more matches").append(" in the dataset)\n");
        }
        return builder.toString().stripTrailing();
    }

    /** "19 matches: 11W 5D 3L | GF 28 GA 15 (+13) | 38 pts | win rate 57.9%" */
    public static String recordLine(TeamRecord record) {
        return String.format(Locale.ROOT, "%d matches: %dW %dD %dL | GF %d GA %d (%+d) | %d pts | win rate %s",
                record.played(), record.wins(), record.draws(), record.losses(),
                record.goalsFor(), record.goalsAgainst(), record.goalDifference(), record.points(),
                TextUtils.percent(record.wins(), record.played()));
    }

    /** Multi-line block describing a record, matching the answer format of the specification. */
    public static String recordBlock(TeamRecord record, String indent) {
        return indent + "Matches: " + record.played() + "\n"
                + indent + "Wins: " + record.wins() + ", Draws: " + record.draws() + ", Losses: " + record.losses() + "\n"
                + indent + "Goals For: " + record.goalsFor() + ", Goals Against: " + record.goalsAgainst()
                + " (" + String.format(Locale.ROOT, "%+d", record.goalDifference()) + ")\n"
                + indent + "Points: " + record.points()
                + " (" + TextUtils.round(record.pointsPerGame(), 2) + " per game)\n"
                + indent + "Win rate: " + TextUtils.percent(record.wins(), record.played());
    }

    /** One player as a single line: "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain". */
    public static String playerLine(Player player) {
        StringBuilder line = new StringBuilder(player.name());
        line.append(" - Overall: ").append(player.overall() == null ? "?" : player.overall());
        if (player.potential() != null) {
            line.append(" (potential ").append(player.potential()).append(')');
        }
        line.append(", Position: ").append(player.position() == null ? "?" : player.position());
        line.append(", Club: ").append(player.hasClub() ? player.club() : "free agent");
        if (player.age() != null) {
            line.append(", Age: ").append(player.age());
        }
        if (player.nationality() != null) {
            line.append(", ").append(player.nationality());
        }
        return line.toString();
    }

    /** Numbered list of players. */
    public static String playerList(List<Player> players, int total) {
        if (players.isEmpty()) {
            return "  (no players)";
        }
        StringBuilder builder = new StringBuilder();
        int index = 1;
        for (Player player : players) {
            builder.append(index++).append(". ").append(playerLine(player)).append('\n');
        }
        if (total > players.size()) {
            builder.append("... (").append(total - players.size()).append(" more players match)\n");
        }
        return builder.toString().stripTrailing();
    }

    /** Fixed width text table. */
    public static String table(List<String> headers, List<List<String>> rows) {
        int columns = headers.size();
        int[] widths = new int[columns];
        for (int i = 0; i < columns; i++) {
            widths[i] = headers.get(i).length();
        }
        for (List<String> row : rows) {
            for (int i = 0; i < columns && i < row.size(); i++) {
                widths[i] = Math.max(widths[i], row.get(i) == null ? 0 : row.get(i).length());
            }
        }
        // Numeric columns are right aligned, text columns left aligned.
        boolean[] numeric = new boolean[columns];
        for (int i = 0; i < columns; i++) {
            numeric[i] = true;
            for (List<String> row : rows) {
                if (i < row.size() && !isNumericCell(row.get(i))) {
                    numeric[i] = false;
                    break;
                }
            }
        }
        StringBuilder builder = new StringBuilder();
        appendRow(builder, headers, widths, numeric);
        builder.append("-".repeat(Math.min(160, sum(widths) + 2 * (columns - 1)))).append('\n');
        for (List<String> row : rows) {
            appendRow(builder, row, widths, numeric);
        }
        return builder.toString().stripTrailing();
    }

    private static void appendRow(StringBuilder builder, List<String> cells, int[] widths, boolean[] numeric) {
        StringBuilder line = new StringBuilder();
        for (int i = 0; i < widths.length; i++) {
            String cell = i < cells.size() && cells.get(i) != null ? cells.get(i) : "";
            String padded = numeric[i] ? TextUtils.padLeft(cell, widths[i]) : TextUtils.pad(cell, widths[i]);
            line.append(i == 0 ? padded : "  " + padded);
        }
        builder.append(line.toString().stripTrailing()).append('\n');
    }

    /** True for values made of digits, signs, separators and percent signs. */
    private static boolean isNumericCell(String value) {
        if (value == null || value.isBlank()) {
            return true;
        }
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (!Character.isDigit(c) && c != '.' && c != ',' && c != '+' && c != '-' && c != '%' && c != ' ') {
                return false;
            }
        }
        return true;
    }

    private static int sum(int[] values) {
        int total = 0;
        for (int value : values) {
            total += value;
        }
        return total;
    }

    private static boolean isNumeric(String value) {
        for (int i = 0; i < value.length(); i++) {
            if (!Character.isDigit(value.charAt(i))) {
                return false;
            }
        }
        return !value.isEmpty();
    }
}
