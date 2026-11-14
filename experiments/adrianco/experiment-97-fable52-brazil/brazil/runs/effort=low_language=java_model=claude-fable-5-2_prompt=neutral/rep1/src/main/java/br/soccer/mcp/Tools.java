package br.soccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Function;

/** MCP tool catalogue: JSON schemas plus dispatch from tool arguments to {@link SoccerService}. */
final class Tools {
    private static final ObjectMapper JSON = new ObjectMapper();

    private record Tool(String description, ObjectNode schema, Function<JsonNode, String> handler) {}

    private final Map<String, Tool> tools = new LinkedHashMap<>();
    private final SoccerService svc;

    private static final String P_TEAM = "Team name; any spelling works (\"Palmeiras\", \"Palmeiras-SP\", \"São Paulo FC\")";
    private static final String P_COMP = "Competition: \"Brasileirão\" (Serie A), \"Serie B\", \"Serie C\", \"Copa do Brasil\" or \"Libertadores\"";
    private static final String P_SEASON = "Season year, e.g. 2019";

    Tools(SoccerService svc) {
        this.svc = svc;
        register("find_matches",
                "Search matches by team, opponent, venue, competition, season, date range, stage or round. "
                        + "Returns dated results and, when a team is given, its record (or head-to-head tally with the opponent).",
                schema(p("team", "string", P_TEAM), p("opponent", "string", "Second team, to list matches between two teams"),
                        pe("venue", "Where `team` played (default either)", "home", "away", "either"),
                        p("competition", "string", P_COMP), p("season", "integer", P_SEASON),
                        p("date_from", "string", "Earliest date, YYYY-MM-DD or DD/MM/YYYY"),
                        p("date_to", "string", "Latest date, YYYY-MM-DD or DD/MM/YYYY"),
                        pe("stage", "Knockout stage (Copa do Brasil / Libertadores)", "group stage", "round of 16", "quarterfinals", "semifinals", "final"),
                        p("round", "string", "Round number (Brasileirão, Copa do Brasil)"),
                        p("source", "string", "Restrict to one CSV file, e.g. \"BR-Football-Dataset.csv\"; disables de-duplication between files"),
                        pe("order", "Date order (default newest)", "newest", "oldest"),
                        p("include_stats", "boolean", "Append corners/shots/attacks where the data has them"),
                        p("limit", "integer", "Maximum matches to list (default 20, max 200)")),
                a -> svc.findMatches(filter(a), integer(a, "limit"), "oldest".equalsIgnoreCase(str(a, "order")), bool(a, "include_stats")));
        register("head_to_head", "Compare two teams head-to-head: wins, draws, goals, home/away split, per-competition breakdown and recent meetings.",
                schema(req("team_a", "string", P_TEAM), req("team_b", "string", P_TEAM), p("competition", "string", P_COMP),
                        p("season", "integer", P_SEASON), p("recent", "integer", "How many recent meetings to list (default 10)")),
                a -> svc.headToHead(str(a, "team_a"), str(a, "team_b"), str(a, "competition"), integer(a, "season"), integer(a, "recent")));
        register("team_stats", "Win/draw/loss record, goals for/against and win rate for one team, optionally filtered by season, competition and home/away.",
                schema(req("team", "string", P_TEAM), p("season", "integer", P_SEASON), p("competition", "string", P_COMP),
                        pe("venue", "home, away or either (default either)", "home", "away", "either")),
                a -> svc.teamStats(str(a, "team"), integer(a, "season"), str(a, "competition"), str(a, "venue")));
        register("team_profile", "Overview of a team across all files: competitions and seasons played, overall record, rivals, and its players in the FIFA data.",
                schema(req("team", "string", P_TEAM)), a -> svc.teamProfile(str(a, "team")));
        register("team_rankings", "Rank teams by a metric (best home/away record, most goals, ...) over a competition and/or season.",
                schema(pe("metric", "Ranking metric (default win_rate)", "win_rate", "points_per_game", "points", "wins", "goals_for", "goals_against", "goal_difference", "losses"),
                        pe("venue", "Count only home or away matches (default either)", "home", "away", "either"),
                        p("competition", "string", P_COMP), p("season", "integer", P_SEASON),
                        p("min_matches", "integer", "Minimum matches to qualify (default 5 with a season, otherwise 30)"),
                        p("limit", "integer", "Rows to return (default 10)")),
                a -> svc.teamRankings(str(a, "metric"), str(a, "venue"), str(a, "competition"), integer(a, "season"), integer(a, "min_matches"), integer(a, "limit")));
        register("standings", "League table for a Brasileirão season calculated from match results, with champion and relegated teams for complete Serie A seasons.",
                schema(req("season", "integer", P_SEASON), p("competition", "string", "League (default Brasileirão Serie A; also Serie B, Serie C)"),
                        p("limit", "integer", "Rows to return (default all)")),
                a -> svc.standings(str(a, "competition"), integer(a, "season"), integer(a, "limit")));
        register("competition_bracket", "Knockout rounds of a Copa Libertadores or Copa do Brasil season, with two-legged ties aggregated.",
                schema(req("season", "integer", P_SEASON), p("competition", "string", "\"Libertadores\" (default) or \"Copa do Brasil\""),
                        p("include_group_stage", "boolean", "Also list every group-stage match")),
                a -> svc.bracket(str(a, "competition"), integer(a, "season"), bool(a, "include_group_stage")));
        register("match_statistics", "Aggregate statistics over matches: average goals per match, home win / draw / away win rates, highest-scoring match, goals per season.",
                schema(p("competition", "string", P_COMP), p("season", "integer", P_SEASON), p("team", "string", "Only matches involving this team"),
                        p("date_from", "string", "Earliest date"), p("date_to", "string", "Latest date")),
                a -> svc.leagueStats(filter(a)));
        register("compare_seasons", "Compare two seasons of one competition side by side (goals, result rates, table leader).",
                schema(req("season_a", "integer", P_SEASON), req("season_b", "integer", P_SEASON), p("competition", "string", P_COMP + " (default Brasileirão)")),
                a -> svc.compareSeasons(str(a, "competition"), integer(a, "season_a"), integer(a, "season_b")));
        register("biggest_wins", "Largest winning margins, optionally filtered by competition, season or team.",
                schema(p("competition", "string", P_COMP), p("season", "integer", P_SEASON), p("team", "string", P_TEAM),
                        p("limit", "integer", "Rows to return (default 10)")),
                a -> svc.biggestWins(filter(a), integer(a, "limit")));
        register("derbies", "Matches between traditional rivals (Fla-Flu, Gre-Nal, Derby Paulista, ...), optionally by season, competition or team.",
                schema(p("season", "integer", P_SEASON), p("competition", "string", P_COMP), p("team", "string", P_TEAM),
                        p("limit", "integer", "Maximum matches to list (default 50)")),
                a -> svc.derbies(integer(a, "season"), str(a, "competition"), str(a, "team"), integer(a, "limit")));
        register("search_players", "Search the FIFA player database by name, nationality, club and position; sorted by rating by default.",
                schema(p("name", "string", "Full or partial player name"), p("nationality", "string", "Country, e.g. \"Brazil\""),
                        p("club", "string", "Club name, e.g. \"Santos\""),
                        p("position", "string", "FIFA position code (ST, GK, CDM, ...) or group: forward, midfielder, defender, goalkeeper"),
                        p("min_overall", "integer", "Minimum overall rating"), p("max_age", "integer", "Maximum age"),
                        p("brazilian_clubs_only", "boolean", "Only players at Brazilian clubs"),
                        pe("sort_by", "Sort order (default overall)", "overall", "potential", "age", "name"),
                        p("limit", "integer", "Maximum players to list (default 20, max 200)")),
                a -> svc.searchPlayers(str(a, "name"), str(a, "nationality"), str(a, "club"), str(a, "position"), integer(a, "min_overall"),
                        integer(a, "max_age"), bool(a, "brazilian_clubs_only"), str(a, "sort_by"), integer(a, "limit")));
        register("player_details", "Full profile of one player: club, position, ratings, physical data, key skill attributes, plus the club's record in the match data.",
                schema(p("name", "string", "Player name (best match is shown, others listed)"), p("id", "integer", "FIFA player id")),
                a -> svc.playerDetails(str(a, "name"), integer(a, "id") == null ? null : integer(a, "id").longValue()));
        register("players_by_club", "Group players by club with squad size, average rating and best player — e.g. Brazilian players at Brazilian clubs.",
                schema(p("nationality", "string", "Country filter, e.g. \"Brazil\""),
                        p("brazilian_clubs_only", "boolean", "Only Brazilian clubs (default true)"),
                        p("limit", "integer", "Maximum clubs to list (default 25)")),
                a -> svc.playersByClub(str(a, "nationality"), !a.has("brazilian_clubs_only") || bool(a, "brazilian_clubs_only"), integer(a, "limit")));
        register("dataset_info", "Describe the loaded data: files, row counts, competitions and seasons covered, known limitations.",
                schema(), a -> svc.datasetInfo());
    }

    private void register(String name, String description, ObjectNode schema, Function<JsonNode, String> handler) {
        tools.put(name, new Tool(description, schema, handler));
    }

    /** The `tools` array for a tools/list response. */
    ArrayNode list() {
        ArrayNode arr = JSON.createArrayNode();
        tools.forEach((name, t) -> {
            ObjectNode o = arr.addObject();
            o.put("name", name);
            o.put("description", t.description);
            o.set("inputSchema", t.schema);
        });
        return arr;
    }

    boolean has(String name) { return tools.containsKey(name); }

    /** Runs a tool. Throws IllegalArgumentException for bad arguments. */
    String call(String name, JsonNode args) {
        Tool t = tools.get(name);
        if (t == null) throw new IllegalArgumentException("Unknown tool: " + name);
        return t.handler.apply(args == null || args.isNull() ? JSON.createObjectNode() : args);
    }

    // ---------- argument helpers ----------

    private static SoccerService.MatchFilter filter(JsonNode a) {
        SoccerService.MatchFilter f = new SoccerService.MatchFilter();
        f.team = str(a, "team");
        f.opponent = str(a, "opponent");
        f.venue = str(a, "venue");
        f.competition = str(a, "competition");
        f.season = integer(a, "season");
        f.stage = str(a, "stage");
        f.round = str(a, "round");
        f.source = str(a, "source");
        f.from = date(a, "date_from");
        f.to = date(a, "date_to");
        return f;
    }

    private static String str(JsonNode a, String k) {
        JsonNode n = a.get(k);
        if (n == null || n.isNull()) return null;
        if (n.isContainerNode()) throw new IllegalArgumentException(k + " must be a string.");
        String s = n.asText().trim();
        return s.isEmpty() ? null : s;
    }

    private static Integer integer(JsonNode a, String k) {
        JsonNode n = a.get(k);
        if (n == null || n.isNull()) return null;
        if (n.isIntegralNumber() && n.canConvertToInt()) return n.intValue();
        if (n.isTextual()) {
            if (n.asText().isBlank()) return null;
            try {
                return Integer.parseInt(n.asText().trim());
            } catch (NumberFormatException e) {
                // fall through
            }
        }
        throw new IllegalArgumentException(k + " must be an integer.");
    }

    private static boolean bool(JsonNode a, String k) {
        JsonNode n = a.get(k);
        if (n == null || n.isNull()) return false;
        if (n.isBoolean()) return n.booleanValue();
        if (n.isTextual() && (n.asText().equalsIgnoreCase("true") || n.asText().equalsIgnoreCase("false"))) {
            return Boolean.parseBoolean(n.asText());
        }
        throw new IllegalArgumentException(k + " must be a boolean.");
    }

    private static LocalDate date(JsonNode a, String k) {
        String s = str(a, k);
        if (s == null) return null;
        LocalDate d = DataStore.parseDate(s);
        if (d == null) throw new IllegalArgumentException(k + " must be a date in YYYY-MM-DD or DD/MM/YYYY format.");
        return d;
    }

    // ---------- schema helpers ----------

    private record Prop(String name, ObjectNode def, boolean required) {}

    private static Prop p(String name, String type, String description) {
        ObjectNode o = JSON.createObjectNode();
        o.put("type", type);
        o.put("description", description);
        return new Prop(name, o, false);
    }

    private static Prop req(String name, String type, String description) {
        return new Prop(name, p(name, type, description).def, true);
    }

    private static Prop pe(String name, String description, String... values) {
        Prop pr = p(name, "string", description);
        ArrayNode e = pr.def.putArray("enum");
        for (String v : values) e.add(v);
        return pr;
    }

    private static ObjectNode schema(Prop... props) {
        ObjectNode s = JSON.createObjectNode();
        s.put("type", "object");
        ObjectNode ps = s.putObject("properties");
        ArrayNode required = JSON.createArrayNode();
        for (Prop pr : props) {
            ps.set(pr.name, pr.def);
            if (pr.required) required.add(pr.name);
        }
        if (!required.isEmpty()) s.set("required", required);
        return s;
    }
}
