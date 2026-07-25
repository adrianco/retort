package com.brsoccer.mcp.tools;

import com.brsoccer.mcp.data.DataStore;
import com.brsoccer.mcp.data.TeamRegistry;
import com.brsoccer.mcp.model.Match;
import com.brsoccer.mcp.model.Player;
import com.brsoccer.mcp.query.QueryService;
import com.brsoccer.mcp.query.QueryService.Aggregate;
import com.brsoccer.mcp.query.QueryService.HeadToHead;
import com.brsoccer.mcp.query.QueryService.MatchFilter;
import com.brsoccer.mcp.query.QueryService.StandingRow;
import com.brsoccer.mcp.query.QueryService.TeamRank;
import com.brsoccer.mcp.query.QueryService.TeamStats;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDate;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Defines the MCP tools (name, description, JSON schema) and formats their text results. */
public class McpTools {

    private final QueryService q;
    private final TeamRegistry teams;
    private final ObjectMapper om = new ObjectMapper();

    public McpTools(QueryService q) {
        this.q = q;
        this.teams = q.store().teams;
    }

    // ------------------------------------------------------------------ tool list

    public ArrayNode toolList() {
        ArrayNode tools = om.createArrayNode();
        tools.add(tool("search_matches",
            "Search matches across all competitions (Brasileirão Série A/B/C, Copa do Brasil, "
                + "Copa Libertadores). Filter by team, opponent, competition, season, date range, "
                + "or stage (e.g. 'final', 'group stage'). Team names are normalized, so "
                + "'Flamengo', 'Flamengo-RJ' and 'Flamengo - RJ' all work.",
            props -> {
                str(props, "team", "Team name (matches home or away)");
                str(props, "opponent", "Second team, to find meetings between the two");
                str(props, "competition", "Competition, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie B'");
                intp(props, "season", "Season year, e.g. 2019");
                str(props, "date_from", "Earliest date, YYYY-MM-DD");
                str(props, "date_to", "Latest date, YYYY-MM-DD");
                str(props, "stage", "Stage filter, e.g. 'final', 'semifinals', 'group stage'");
                intp(props, "limit", "Max matches to list (default 20)");
            }));
        tools.add(tool("head_to_head",
            "Head-to-head record between two teams across every competition in the data: "
                + "wins, draws, goals, and the most recent meetings.",
            props -> {
                str(props, "team1", "First team name");
                str(props, "team2", "Second team name");
            }, "team1", "team2"));
        tools.add(tool("team_stats",
            "A team's record: matches, wins/draws/losses, goals for/against, win rate. "
                + "Optionally filter by season, competition, and venue (home/away).",
            props -> {
                str(props, "team", "Team name");
                intp(props, "season", "Season year");
                str(props, "competition", "Competition filter");
                str(props, "venue", "'home', 'away', or 'all' (default)");
            }, "team"));
        tools.add(tool("league_standings",
            "League table for a season computed from match results (3 points per win). "
                + "Defaults to Brasileirão Série A; Copa do Brasil and Libertadores are knockout "
                + "competitions so standings are most meaningful for league formats.",
            props -> {
                intp(props, "season", "Season year, e.g. 2019");
                str(props, "competition", "Competition (default Brasileirão Série A)");
                intp(props, "limit", "Max rows (default all)");
            }, "season"));
        tools.add(tool("search_players",
            "Search the FIFA player database (18k players) by name, nationality, club, position, "
                + "or minimum overall rating. Note: the dataset is FIFA 19, which contains no "
                + "Brazilian-league clubs, so club searches for e.g. Flamengo return no players.",
            props -> {
                str(props, "name", "Player name (partial, accent-insensitive)");
                str(props, "nationality", "e.g. 'Brazil'");
                str(props, "club", "Club name (partial)");
                str(props, "position", "Exact position code, e.g. ST, GK, CAM, LW");
                intp(props, "min_overall", "Minimum overall rating");
                str(props, "sort_by", "'overall' (default), 'potential', 'age', or 'name'");
                intp(props, "limit", "Max players to list (default 20)");
            }));
        tools.add(tool("player_info",
            "Detailed profile of a single player: ratings, club, position, physicals, and key "
                + "skill attributes. Picks the best (highest-rated) match for the name.",
            props -> str(props, "name", "Player name to look up"), "name"));
        tools.add(tool("competition_stats",
            "Aggregate statistics for a competition (optionally one season): matches, average "
                + "goals per match, home/away win rates, draw rate, and the biggest wins.",
            props -> {
                str(props, "competition", "Competition (omit for all matches)");
                intp(props, "season", "Season year");
            }));
        tools.add(tool("team_rankings",
            "Rank teams by a metric: 'points', 'wins', 'win_rate', 'goals_scored', or "
                + "'goals_conceded' (ascending = best defense). Filter by venue to answer e.g. "
                + "'which team has the best away record?'.",
            props -> {
                str(props, "metric", "'points', 'wins', 'win_rate' (default), 'goals_scored', 'goals_conceded'");
                str(props, "venue", "'home', 'away', or 'all' (default)");
                intp(props, "season", "Season year");
                str(props, "competition", "Competition filter");
                intp(props, "min_matches", "Minimum matches to qualify (default 10)");
                intp(props, "limit", "Max teams (default 10)");
            }));
        tools.add(tool("list_competitions",
            "List the loaded datasets and competitions with match counts and season coverage.",
            props -> {}));
        return tools;
    }

    private interface PropBuilder {
        void build(ObjectNode props);
    }

    private ObjectNode tool(String name, String description, PropBuilder pb, String... required) {
        ObjectNode t = om.createObjectNode();
        t.put("name", name);
        t.put("description", description);
        ObjectNode schema = t.putObject("inputSchema");
        schema.put("type", "object");
        ObjectNode props = schema.putObject("properties");
        pb.build(props);
        if (required.length > 0) {
            ArrayNode req = schema.putArray("required");
            for (String r : required) req.add(r);
        }
        return t;
    }

    private static void str(ObjectNode props, String name, String desc) {
        ObjectNode p = props.putObject(name);
        p.put("type", "string");
        p.put("description", desc);
    }

    private static void intp(ObjectNode props, String name, String desc) {
        ObjectNode p = props.putObject(name);
        p.put("type", "integer");
        p.put("description", desc);
    }

    // ------------------------------------------------------------------ dispatch

    public String call(String name, JsonNode args) {
        if (args == null || args.isNull()) args = om.createObjectNode();
        return switch (name) {
            case "search_matches" -> searchMatches(args);
            case "head_to_head" -> headToHead(args);
            case "team_stats" -> teamStats(args);
            case "league_standings" -> standings(args);
            case "search_players" -> searchPlayers(args);
            case "player_info" -> playerInfo(args);
            case "competition_stats" -> competitionStats(args);
            case "team_rankings" -> teamRankings(args);
            case "list_competitions" -> listCompetitions();
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };
    }

    private static String s(JsonNode args, String field) {
        JsonNode n = args.get(field);
        if (n == null || n.isNull()) return null;
        String v = n.asText().trim();
        return v.isEmpty() ? null : v;
    }

    private static Integer i(JsonNode args, String field) {
        JsonNode n = args.get(field);
        if (n == null || n.isNull()) return null;
        if (n.isNumber()) return n.asInt();
        return DataStore.parseIntStr(n.asText());
    }

    private static LocalDate d(JsonNode args, String field) {
        String v = s(args, field);
        if (v == null) return null;
        LocalDate date = DataStore.parseDate(v);
        if (date == null) throw new IllegalArgumentException("Unparseable date for " + field + ": " + v);
        return date;
    }

    // ------------------------------------------------------------------ handlers

    private String searchMatches(JsonNode args) {
        Integer limit = i(args, "limit");
        int max = limit == null ? 20 : Math.max(1, limit);
        List<Match> ms = q.findMatches(new MatchFilter(
            s(args, "team"), s(args, "opponent"), s(args, "competition"), i(args, "season"),
            d(args, "date_from"), d(args, "date_to"), s(args, "stage")));
        if (ms.isEmpty()) return "No matches found for the given criteria.";
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(ms.size()).append(" match(es):\n");
        List<Match> recent = ms.reversed();
        for (int idx = 0; idx < Math.min(max, recent.size()); idx++) {
            sb.append("- ").append(formatMatch(recent.get(idx))).append('\n');
        }
        if (ms.size() > max) {
            sb.append("... (").append(ms.size() - max).append(" more matches not shown; raise 'limit' to see them)\n");
        }
        return sb.toString();
    }

    private String headToHead(JsonNode args) {
        String t1 = req(args, "team1");
        String t2 = req(args, "team2");
        HeadToHead h = q.headToHead(t1, t2);
        String n1 = teams.display(h.team1Key());
        String n2 = teams.display(h.team2Key());
        if (h.matches().isEmpty()) return "No matches found between " + n1 + " and " + n2 + " in the data.";
        StringBuilder sb = new StringBuilder();
        sb.append(n1).append(" vs ").append(n2).append(" — ").append(h.matches().size())
            .append(" meetings in the data:\n");
        sb.append(String.format("Head-to-head: %s %d wins, %s %d wins, %d draws%n",
            n1, h.team1Wins(), n2, h.team2Wins(), h.draws()));
        sb.append(String.format("Goals: %s %d, %s %d%n%nMost recent meetings:%n", n1, h.team1Goals(), n2, h.team2Goals()));
        List<Match> recent = h.matches().reversed();
        for (int idx = 0; idx < Math.min(10, recent.size()); idx++) {
            sb.append("- ").append(formatMatch(recent.get(idx))).append('\n');
        }
        if (recent.size() > 10) sb.append("... (").append(recent.size() - 10).append(" earlier matches)\n");
        return sb.toString();
    }

    private String teamStats(JsonNode args) {
        String team = req(args, "team");
        Integer season = i(args, "season");
        String comp = s(args, "competition");
        String venue = s(args, "venue");
        TeamStats st = q.teamStats(team, season, comp, venue);
        String name = teams.display(st.teamKey());
        if (st.played() == 0) return "No matches found for " + name + " with the given filters.";
        String scope = (venue != null && !venue.equalsIgnoreCase("all") ? venue.toLowerCase() + " " : "")
            + "record" + (season != null ? " in " + season : "")
            + (comp != null ? " (" + DataStore.canonicalCompetition(comp) + ")" : " (all competitions)");
        StringBuilder sb = new StringBuilder();
        sb.append(name).append(' ').append(scope).append(":\n");
        sb.append("- Matches: ").append(st.played()).append('\n');
        sb.append("- Wins: ").append(st.wins()).append(", Draws: ").append(st.draws())
            .append(", Losses: ").append(st.losses()).append('\n');
        sb.append("- Goals For: ").append(st.goalsFor()).append(", Goals Against: ").append(st.goalsAgainst()).append('\n');
        sb.append(String.format(Locale.US, "- Win rate: %.1f%%%n", st.winRate()));
        return sb.toString();
    }

    private String standings(JsonNode args) {
        Integer season = i(args, "season");
        if (season == null) throw new IllegalArgumentException("'season' is required");
        String comp = DataStore.canonicalCompetition(s(args, "competition"));
        if (comp == null) comp = DataStore.SERIE_A;
        List<StandingRow> rows = q.standings(season, comp);
        if (rows.isEmpty()) return "No " + comp + " matches found for season " + season + ".";
        Integer limit = i(args, "limit");
        int max = limit == null ? rows.size() : Math.max(1, limit);
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(' ').append(comp).append(" standings (computed from match results):\n");
        for (int idx = 0; idx < Math.min(max, rows.size()); idx++) {
            StandingRow r = rows.get(idx);
            sb.append(String.format("%2d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)%n",
                idx + 1, teams.display(r.teamKey()), r.points(), r.wins(), r.draws(), r.losses(),
                r.goalsFor(), r.goalsAgainst(), r.goalDiff()));
        }
        if (comp.equals(DataStore.SERIE_A)) {
            sb.append("Champion: ").append(teams.display(rows.get(0).teamKey())).append('\n');
            if (rows.size() >= 4 && max >= rows.size()) {
                sb.append("Relegation zone (bottom 4): ");
                for (int idx = rows.size() - 4; idx < rows.size(); idx++) {
                    sb.append(teams.display(rows.get(idx).teamKey()));
                    if (idx < rows.size() - 1) sb.append(", ");
                }
                sb.append('\n');
            }
        }
        return sb.toString();
    }

    private String searchPlayers(JsonNode args) {
        Integer limit = i(args, "limit");
        int max = limit == null ? 20 : Math.max(1, limit);
        List<Player> ps = q.searchPlayers(s(args, "name"), s(args, "nationality"), s(args, "club"),
            s(args, "position"), i(args, "min_overall"), s(args, "sort_by"), max + 1);
        if (ps.isEmpty()) return "No players found for the given criteria.";
        StringBuilder sb = new StringBuilder();
        sb.append("Players found").append(ps.size() > max ? " (showing first " + max + ")" : "").append(":\n");
        for (int idx = 0; idx < Math.min(max, ps.size()); idx++) {
            Player p = ps.get(idx);
            sb.append(String.format("%2d. %s - Overall: %s, Potential: %s, Position: %s, Age: %s, Club: %s, Nationality: %s%n",
                idx + 1, p.name, nz(p.overall), nz(p.potential), nzs(p.position), nz(p.age),
                nzs(p.club), nzs(p.nationality)));
        }
        return sb.toString();
    }

    private String playerInfo(JsonNode args) {
        String name = req(args, "name");
        List<Player> ps = q.searchPlayers(name, null, null, null, null, "overall", 1);
        if (ps.isEmpty()) return "No player found matching '" + name + "'.";
        Player p = ps.get(0);
        StringBuilder sb = new StringBuilder();
        sb.append(p.name).append('\n');
        sb.append("- Overall: ").append(nz(p.overall)).append(", Potential: ").append(nz(p.potential)).append('\n');
        sb.append("- Position: ").append(nzs(p.position)).append(", Jersey: ").append(nzs(p.jerseyNumber)).append('\n');
        sb.append("- Club: ").append(nzs(p.club)).append('\n');
        sb.append("- Nationality: ").append(nzs(p.nationality)).append(", Age: ").append(nz(p.age)).append('\n');
        sb.append("- Height: ").append(nzs(p.height)).append(", Weight: ").append(nzs(p.weight))
            .append(", Preferred foot: ").append(nzs(p.preferredFoot)).append('\n');
        sb.append("- Value: ").append(nzs(p.value)).append(", Wage: ").append(nzs(p.wage)).append('\n');
        if (!p.attributes.isEmpty()) {
            sb.append("Key attributes:\n");
            int col = 0;
            for (Map.Entry<String, Integer> e : p.attributes.entrySet()) {
                boolean gk = e.getKey().startsWith("GK");
                boolean isGoalkeeper = "GK".equalsIgnoreCase(nzs(p.position));
                if (gk != isGoalkeeper) continue;
                sb.append(String.format("  %s: %d", e.getKey(), e.getValue()));
                if (++col % 4 == 0) sb.append('\n');
            }
            if (col % 4 != 0) sb.append('\n');
        }
        return sb.toString();
    }

    private String competitionStats(JsonNode args) {
        String comp = s(args, "competition");
        Integer season = i(args, "season");
        Aggregate a = q.aggregate(comp, season);
        if (a.matches() == 0) return "No matches found for the given criteria.";
        String scope = (comp != null ? DataStore.canonicalCompetition(comp) : "All competitions")
            + (season != null ? ", season " + season : " (all seasons)");
        StringBuilder sb = new StringBuilder();
        sb.append(scope).append(":\n");
        sb.append("- Matches: ").append(a.matches()).append('\n');
        sb.append(String.format(Locale.US, "- Average goals per match: %.2f%n", a.avgGoals()));
        sb.append(String.format(Locale.US, "- Home win rate: %.1f%%, Away win rate: %.1f%%, Draws: %.1f%%%n",
            a.homeWinPct(), a.awayWinPct(), a.drawPct()));
        List<Match> big = q.biggestWins(comp, season, 5);
        if (!big.isEmpty()) {
            sb.append("Biggest wins:\n");
            for (Match m : big) sb.append("- ").append(formatMatch(m)).append('\n');
        }
        return sb.toString();
    }

    private String teamRankings(JsonNode args) {
        String metric = s(args, "metric");
        String venue = s(args, "venue");
        Integer minM = i(args, "min_matches");
        Integer limit = i(args, "limit");
        List<TeamRank> rs = q.rankings(metric, venue, i(args, "season"), s(args, "competition"),
            minM == null ? 10 : minM, limit == null ? 10 : limit);
        if (rs.isEmpty()) return "No teams qualified for the given criteria (try lowering min_matches).";
        String met = metric == null ? "win_rate" : metric.toLowerCase();
        StringBuilder sb = new StringBuilder();
        sb.append("Team rankings by ").append(met)
            .append(venue != null && !venue.equalsIgnoreCase("all") ? " (" + venue.toLowerCase() + " matches)" : "")
            .append(":\n");
        for (int idx = 0; idx < rs.size(); idx++) {
            TeamRank r = rs.get(idx);
            TeamStats st = r.stats();
            String val = met.equals("win_rate")
                ? String.format(Locale.US, "%.1f%%", r.value())
                : String.valueOf((int) r.value());
            sb.append(String.format("%2d. %s - %s %s (%dP %dW %dD %dL, GF %d, GA %d)%n",
                idx + 1, teams.display(r.teamKey()), met, val, st.played(), st.wins(), st.draws(),
                st.losses(), st.goalsFor(), st.goalsAgainst()));
        }
        return sb.toString();
    }

    private String listCompetitions() {
        StringBuilder sb = new StringBuilder();
        sb.append("Loaded datasets (after de-duplication across files):\n");
        q.store().sourceCounts().forEach((src, n) -> sb.append(String.format("- %s: %,d records%n", src, n)));
        sb.append(String.format("Total unique matches: %,d; duplicate rows merged: %,d%n",
            q.store().matches().size(), q.store().duplicatesMerged()));
        sb.append("Competitions: Brasileirão Série A (2003-2022), Brasileirão Série B/C, ")
            .append("Copa do Brasil (2012-2022), Copa Libertadores (2013-2022)\n");
        sb.append("Players: FIFA database, ").append(String.format("%,d", q.store().players().size()))
            .append(" players (FIFA 19 — no Brazilian-league clubs present)\n");
        return sb.toString();
    }

    // ------------------------------------------------------------------ helpers

    private String formatMatch(Match m) {
        StringBuilder sb = new StringBuilder();
        sb.append(m.date).append(": ")
            .append(teams.display(m.homeKey)).append(' ').append(m.homeGoals)
            .append('-').append(m.awayGoals).append(' ').append(teams.display(m.awayKey))
            .append(" (").append(m.competition);
        if (m.round != null) sb.append(", Round ").append(m.round);
        if (m.stage != null) sb.append(", ").append(m.stage);
        if (m.venue != null) sb.append(", at ").append(m.venue);
        sb.append(')');
        return sb.toString();
    }

    private static String req(JsonNode args, String field) {
        String v = s(args, field);
        if (v == null) throw new IllegalArgumentException("'" + field + "' is required");
        return v;
    }

    private static String nz(Integer v) {
        return v == null ? "?" : String.valueOf(v);
    }

    private static String nzs(String v) {
        return v == null || v.isEmpty() ? "?" : v;
    }
}
