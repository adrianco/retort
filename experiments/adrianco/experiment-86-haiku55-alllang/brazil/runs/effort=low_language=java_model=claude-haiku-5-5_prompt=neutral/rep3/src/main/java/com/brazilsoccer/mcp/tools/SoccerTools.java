/*
 * Context block: MCP tool catalogue for the Brazilian soccer knowledge base.
 * Each tool takes simple typed arguments (team names, competition, season, dates) and
 * returns plain text formatted in the style the spec's example answers use, so an LLM
 * can relay it directly. Argument problems raise IllegalArgumentException, which the
 * protocol layer reports back to the client as a tool error.
 */
package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.data.Competition;
import com.brazilsoccer.mcp.data.HeadToHead;
import com.brazilsoccer.mcp.data.Match;
import com.brazilsoccer.mcp.data.MatchFilter;
import com.brazilsoccer.mcp.data.Player;
import com.brazilsoccer.mcp.data.PlayerFilter;
import com.brazilsoccer.mcp.data.SoccerDatabase;
import com.brazilsoccer.mcp.data.SoccerDatabase.MatchStatistics;
import com.brazilsoccer.mcp.data.SoccerDatabase.Venue;
import com.brazilsoccer.mcp.data.StandingRow;
import com.brazilsoccer.mcp.data.TeamRecord;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class SoccerTools {

    static final Set<String> NAMES = Set.of(
            "search_matches", "team_stats", "head_to_head", "search_players",
            "competition_standings", "match_statistics");

    private static final int DEFAULT_LIMIT = 20;
    private static final int MAX_LIMIT = 100;

    private final SoccerDatabase db;
    private final ObjectMapper mapper;

    public SoccerTools(SoccerDatabase db, ObjectMapper mapper) {
        this.db = db;
        this.mapper = mapper;
    }

    public boolean has(String name) {
        return NAMES.contains(name);
    }

    // ------------------------------------------------------------ descriptors

    public ArrayNode descriptors() {
        ArrayNode tools = mapper.createArrayNode();
        tools.add(descriptor("search_matches",
                "Find matches by team, opponent, competition, season or date range. Returns most recent first. "
                        + "Give both team and opponent for a head-to-head list.",
                schema()
                        .put("team", "string", "Team name, e.g. 'Flamengo', 'Atletico-MG' or 'Palmeiras-SP'")
                        .put("opponent", "string", "Second team. With team, returns matches between the two in either venue")
                        .put("competition", "string", "brasileirao, copa do brasil, libertadores, serie b or serie c")
                        .put("season", "integer", "Season year, e.g. 2023")
                        .put("from", "string", "Earliest date, YYYY-MM-DD")
                        .put("to", "string", "Latest date, YYYY-MM-DD")
                        .put("limit", "integer", "Maximum matches to list (default 20, max 100)")));
        tools.add(descriptor("team_stats",
                "Win/draw/loss record and goals for a team, optionally filtered by competition, season and venue.",
                schema()
                        .put("team", "string", "Team name")
                        .put("competition", "string", "Competition filter (see search_matches)")
                        .put("season", "integer", "Season year")
                        .put("venue", "string", "any (default), home or away")
                        .require("team")));
        tools.add(descriptor("head_to_head",
                "Head-to-head record between two teams across all competitions in the dataset, with the most recent meetings.",
                schema()
                        .put("team", "string", "First team")
                        .put("opponent", "string", "Second team")
                        .require("team", "opponent")));
        tools.add(descriptor("search_players",
                "Search FIFA player data by name, nationality, club, position or minimum overall rating. Highest rated first.",
                schema()
                        .put("name", "string", "Full or partial name, e.g. 'Gabriel Barbosa' or 'Neymar'")
                        .put("nationality", "string", "Nationality, e.g. 'Brazil'")
                        .put("club", "string", "Club name, e.g. 'Flamengo' or 'São Paulo'")
                        .put("position", "string", "Position code (ST, CDM) or group: goalkeeper, defender, midfielder, forward")
                        .put("min_overall", "integer", "Minimum overall rating")
                        .put("limit", "integer", "Maximum players to list (default 20, max 100)")));
        tools.add(descriptor("competition_standings",
                "League table for a Brasileirão, Serie B or Serie C season, calculated from match results.",
                schema()
                        .put("competition", "string", "brasileirao, serie b or serie c")
                        .put("season", "integer", "Season year, e.g. 2019")
                        .require("competition", "season")));
        tools.add(descriptor("match_statistics",
                "Aggregate statistics: summary (match count, goals per game, home win rate), biggest_wins, "
                        + "or best_away_record (teams ranked by away win rate).",
                schema()
                        .put("metric", "string", "summary (default), biggest_wins or best_away_record")
                        .put("competition", "string", "Competition filter (see search_matches)")
                        .put("season", "integer", "Season year")
                        .put("team", "string", "Team filter (summary and biggest_wins only)")
                        .put("from", "string", "Earliest date, YYYY-MM-DD")
                        .put("to", "string", "Latest date, YYYY-MM-DD")
                        .put("min_away_games", "integer", "best_away_record only: minimum away games (default 5)")
                        .put("limit", "integer", "Rows to list for biggest_wins and best_away_record (default 10)")));
        return tools;
    }

    // ------------------------------------------------------------------ calls

    public String call(String name, JsonNode args) {
        return switch (name) {
            case "search_matches" -> searchMatches(args);
            case "team_stats" -> teamStats(args);
            case "head_to_head" -> headToHead(args);
            case "search_players" -> searchPlayers(args);
            case "competition_standings" -> standings(args);
            case "match_statistics" -> matchStatistics(args);
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };
    }

    String searchMatches(JsonNode args) {
        MatchFilter filter = filterFrom(args);
        int limit = limit(args, DEFAULT_LIMIT);
        List<Match> found = db.findMatches(filter);
        if (found.isEmpty()) {
            return "No matches found for the given criteria.";
        }
        StringBuilder out = new StringBuilder();
        if (filter.team() != null && filter.opponent() != null) {
            HeadToHead h2h = db.headToHead(filter.team(), filter.opponent(), filter);
            out.append(h2h.teamA()).append(" vs ").append(h2h.teamB()).append(":\n");
            for (Match m : found.stream().limit(limit).toList()) {
                out.append("- ").append(matchLine(m)).append('\n');
            }
            if (found.size() > limit) {
                out.append("- ... (").append(found.size() - limit).append(" more matches in dataset)\n");
            }
            out.append('\n').append(headToHeadLine(h2h)).append('\n');
        } else {
            for (Match m : found.stream().limit(limit).toList()) {
                out.append("- ").append(matchLine(m)).append('\n');
            }
            if (found.size() > limit) {
                out.append("... (").append(found.size() - limit).append(" more matches in dataset)\n");
            }
            out.append("\nTotal matches: ").append(found.size()).append('\n');
        }
        return out.toString().stripTrailing();
    }

    String teamStats(JsonNode args) {
        String team = required(args, "team");
        MatchFilter filter = filterFrom(args).withTeam(null).withOpponent(null);
        Venue venue = venue(args);
        TeamRecord r = db.teamRecord(team, filter, venue);
        if (r.played() == 0) {
            return "No matches found for " + team + " with the given criteria.";
        }
        String scope = scopeLabel(filter) + (venue == Venue.ANY ? "" : ", " + venue.name().toLowerCase(Locale.ROOT) + " only");
        return String.format(Locale.ROOT, "%s record%s:%n- Matches: %d%n- Wins: %d, Draws: %d, Losses: %d%n"
                        + "- Goals For: %d, Goals Against: %d%n- Win rate: %.1f%%",
                r.team(), scope.isEmpty() ? "" : " (" + scope + ")", r.played(), r.wins(), r.draws(), r.losses(),
                r.goalsFor(), r.goalsAgainst(), r.winRate() * 100);
    }

    String headToHead(JsonNode args) {
        String team = required(args, "team");
        String opponent = required(args, "opponent");
        HeadToHead h = db.headToHead(team, opponent, MatchFilter.any());
        if (h.played() == 0) {
            return "No matches between " + team + " and " + opponent + " in the dataset.";
        }
        StringBuilder out = new StringBuilder();
        out.append(h.teamA()).append(" vs ").append(h.teamB()).append(" head-to-head:\n");
        out.append("- Matches: ").append(h.played()).append('\n');
        out.append(String.format(Locale.ROOT, "- %s wins: %d, Draws: %d, %s wins: %d%n",
                h.teamA(), h.winsA(), h.draws(), h.teamB(), h.winsB()));
        out.append(String.format(Locale.ROOT, "- Goals: %s %d, %s %d%n", h.teamA(), h.goalsA(), h.teamB(), h.goalsB()));
        out.append("\nMost recent meetings:\n");
        for (Match m : h.matches().stream().limit(5).toList()) {
            out.append("- ").append(matchLine(m)).append('\n');
        }
        return out.toString().stripTrailing();
    }

    String searchPlayers(JsonNode args) {
        PlayerFilter filter = new PlayerFilter(
                optional(args, "name"),
                optional(args, "nationality"),
                optional(args, "club"),
                optional(args, "position"),
                optionalInt(args, "min_overall"));
        if (filter.name() == null && filter.nationality() == null && filter.club() == null
                && filter.position() == null && filter.minOverall() == null) {
            throw new IllegalArgumentException("Provide at least one of: name, nationality, club, position, min_overall");
        }
        List<Player> found = db.findPlayers(filter, limit(args, DEFAULT_LIMIT));
        if (found.isEmpty()) {
            return "No players found for the given criteria.";
        }
        StringBuilder out = new StringBuilder();
        int i = 1;
        for (Player p : found) {
            out.append(String.format(Locale.ROOT, "%d. %s - Overall: %d, Position: %s, Club: %s%n",
                    i++, p.name(), p.overall(), p.position(), p.club()));
        }
        return out.toString().stripTrailing();
    }

    String standings(JsonNode args) {
        Competition competition = competition(required(args, "competition"));
        int season = requiredInt(args, "season");
        if (competition == Competition.COPA_DO_BRASIL || competition == Competition.LIBERTADORES) {
            throw new IllegalArgumentException("Standings are only calculated for league competitions "
                    + "(brasileirao, serie b, serie c)");
        }
        List<StandingRow> table = db.standings(competition, season);
        if (table.isEmpty()) {
            return "No " + competition.label() + " matches found for " + season + ".";
        }
        StringBuilder out = new StringBuilder();
        out.append(competition.label()).append(' ').append(season).append(" standings (calculated from matches):\n");
        for (StandingRow r : table) {
            out.append(String.format(Locale.ROOT, "%d. %s - %d pts (%dW, %dD, %dL) GF %d, GA %d, GD %+d",
                    r.position(), r.team(), r.points(), r.wins(), r.draws(), r.losses(),
                    r.goalsFor(), r.goalsAgainst(), r.goalDifference()));
            if (r.position() == 1) {
                out.append(" - Champion");
            }
            out.append('\n');
        }
        return out.toString().stripTrailing();
    }

    String matchStatistics(JsonNode args) {
        String metric = optional(args, "metric");
        metric = metric == null ? "summary" : metric.toLowerCase(Locale.ROOT);
        MatchFilter filter = filterFrom(args);
        int limit = limit(args, 10);
        return switch (metric) {
            case "summary" -> summary(filter);
            case "biggest_wins" -> biggestWins(filter, limit);
            case "best_away_record" -> bestAwayRecord(filter, optionalInt(args, "min_away_games") == null
                    ? 5 : optionalInt(args, "min_away_games"), limit);
            default -> throw new IllegalArgumentException(
                    "Unknown metric '" + metric + "'. Use summary, biggest_wins or best_away_record");
        };
    }

    private String summary(MatchFilter filter) {
        MatchStatistics s = db.statistics(filter);
        if (s.matches() == 0) {
            return "No matches found for the given criteria.";
        }
        return String.format(Locale.ROOT, "%sMatches: %d%nAverage goals per match: %.2f%n"
                        + "Home win rate: %.1f%% (home wins %d, draws %d, away wins %d)",
                filter.team() == null ? "" : filter.team() + " - ",
                s.matches(), s.averageGoals(), s.homeWinRate() * 100, s.homeWins(), s.draws(), s.awayWins());
    }

    private String biggestWins(MatchFilter filter, int limit) {
        List<Match> wins = db.biggestWins(filter, limit);
        if (wins.isEmpty()) {
            return "No matches found for the given criteria.";
        }
        String scope = scopeLabel(filter);
        StringBuilder out = new StringBuilder("Biggest wins (" + (scope.isEmpty() ? "all matches" : scope) + "):\n");
        int i = 1;
        for (Match m : wins) {
            out.append(i++).append(". ").append(matchLine(m)).append('\n');
        }
        return out.toString().stripTrailing();
    }

    private String bestAwayRecord(MatchFilter filter, int minAway, int limit) {
        List<TeamRecord> records = db.bestAwayRecords(filter, minAway, limit);
        if (records.isEmpty()) {
            return "No teams with at least " + minAway + " away matches for the given criteria.";
        }
        StringBuilder out = new StringBuilder("Best away records (" + scopeLabel(filter)
                + ", minimum " + minAway + " away matches):\n");
        int i = 1;
        for (TeamRecord r : records) {
            out.append(String.format(Locale.ROOT, "%d. %s - %.1f%% away win rate (%dW, %dD, %dL in %d away matches)%n",
                    i++, r.team(), r.winRate() * 100, r.wins(), r.draws(), r.losses(), r.played()));
        }
        return out.toString().stripTrailing();
    }

    // ---------------------------------------------------------------- helpers

    private String matchLine(Match m) {
        String detail = m.competition().label() + " " + m.season();
        if (!m.round().isEmpty()) {
            detail += ", " + (m.round().chars().allMatch(Character::isDigit) ? "Round " + m.round() : m.round());
        }
        return String.format(Locale.ROOT, "%s: %s %d-%d %s (%s)",
                m.date(), m.home().display(), m.homeGoals(), m.awayGoals(), m.away().display(), detail);
    }

    private static String headToHeadLine(HeadToHead h) {
        return String.format(Locale.ROOT, "Head-to-head in dataset: %s %d wins, %d draws, %s %d wins",
                h.teamA(), h.winsA(), h.draws(), h.teamB(), h.winsB());
    }

    private static String scopeLabel(MatchFilter f) {
        StringBuilder s = new StringBuilder();
        if (f.competition() != null) {
            s.append(f.competition().label());
        }
        if (f.season() != null) {
            s.append(s.isEmpty() ? "" : " ").append(f.season());
        }
        if (f.from() != null || f.to() != null) {
            s.append(s.isEmpty() ? "" : ", ").append(f.from() == null ? "" : f.from()).append(" to ")
                    .append(f.to() == null ? "" : f.to());
        }
        return s.toString();
    }

    private MatchFilter filterFrom(JsonNode args) {
        return new MatchFilter(
                optional(args, "team"),
                optional(args, "opponent"),
                optional(args, "competition") == null ? null : competition(optional(args, "competition")),
                optionalInt(args, "season"),
                date(args, "from"),
                date(args, "to"));
    }

    private static Competition competition(String text) {
        return Competition.parse(text).orElseThrow(() -> new IllegalArgumentException(
                "Unknown competition '" + text + "'. Use brasileirao, copa do brasil, libertadores, serie b or serie c"));
    }

    private static Venue venue(JsonNode args) {
        String v = optional(args, "venue");
        if (v == null) {
            return Venue.ANY;
        }
        return switch (v.toLowerCase(Locale.ROOT)) {
            case "any" -> Venue.ANY;
            case "home" -> Venue.HOME;
            case "away" -> Venue.AWAY;
            default -> throw new IllegalArgumentException("venue must be any, home or away");
        };
    }

    private static int limit(JsonNode args, int fallback) {
        Integer value = optionalInt(args, "limit");
        if (value == null) {
            return fallback;
        }
        if (value < 1 || value > MAX_LIMIT) {
            throw new IllegalArgumentException("limit must be between 1 and " + MAX_LIMIT);
        }
        return value;
    }

    private static LocalDate date(JsonNode args, String key) {
        String text = optional(args, key);
        if (text == null) {
            return null;
        }
        try {
            return LocalDate.parse(text);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException(key + " must be a date in YYYY-MM-DD format");
        }
    }

    private static String required(JsonNode args, String key) {
        String value = optional(args, key);
        if (value == null) {
            throw new IllegalArgumentException("Missing required argument: " + key);
        }
        return value;
    }

    private static int requiredInt(JsonNode args, String key) {
        Integer value = optionalInt(args, key);
        if (value == null) {
            throw new IllegalArgumentException("Missing required integer argument: " + key);
        }
        return value;
    }

    private static String optional(JsonNode args, String key) {
        JsonNode node = args == null ? null : args.get(key);
        if (node == null || node.isNull()) {
            return null;
        }
        String text = node.asText().trim();
        return text.isEmpty() ? null : text;
    }

    private static Integer optionalInt(JsonNode args, String key) {
        JsonNode node = args == null ? null : args.get(key);
        if (node == null || node.isNull()) {
            return null;
        }
        if (node.isInt() || node.isLong()) {
            return node.asInt();
        }
        try {
            return Integer.parseInt(node.asText().trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(key + " must be an integer");
        }
    }

    private ObjectNode descriptor(String name, String description, SchemaBuilder schema) {
        ObjectNode node = mapper.createObjectNode();
        node.put("name", name);
        node.put("description", description);
        node.set("inputSchema", schema.build());
        return node;
    }

    private SchemaBuilder schema() {
        return new SchemaBuilder(mapper);
    }

    /** Small helper that builds a JSON Schema object for a tool's arguments. */
    private static final class SchemaBuilder {
        private final ObjectMapper mapper;
        private final ObjectNode root;
        private final ObjectNode properties;
        private final ArrayNode required;

        SchemaBuilder(ObjectMapper mapper) {
            this.mapper = mapper;
            this.root = mapper.createObjectNode();
            this.root.put("type", "object");
            this.properties = root.putObject("properties");
            this.required = root.putArray("required");
        }

        SchemaBuilder put(String name, String type, String description) {
            ObjectNode prop = properties.putObject(name);
            prop.put("type", type);
            prop.put("description", description);
            return this;
        }

        SchemaBuilder require(String... names) {
            for (String n : names) {
                required.add(n);
            }
            return this;
        }

        ObjectNode build() {
            if (required.isEmpty()) {
                root.remove("required");
            }
            return root;
        }
    }
}
