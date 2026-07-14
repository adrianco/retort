package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * The query layer over the loaded datasets. Each public {@code tool*} method takes
 * the tool arguments as JSON and returns a JSON result describing the answer in the
 * language of the domain (matches, records, standings, players, statistics).
 */
public final class SoccerService {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final int DEFAULT_MATCH_LIMIT = 50;
    private static final int DEFAULT_PLAYER_LIMIT = 25;

    private final DataStore data;

    public SoccerService(DataStore data) {
        this.data = data;
    }

    public static SoccerService load(Path dataDir) {
        return new SoccerService(DataStore.load(dataDir));
    }

    // ---- find_matches --------------------------------------------------------

    public JsonNode toolFindMatches(JsonNode args) {
        String teamBase = key(text(args, "team"));
        String oppBase = key(text(args, "opponent"));
        Competition comp = Competition.resolve(text(args, "competition"));
        Integer season = optInt(args, "season");
        String venue = text(args, "venue");
        int limit = clamp(optInt(args, "limit", DEFAULT_MATCH_LIMIT), 1, 500);

        List<Match> filtered = new ArrayList<>();
        for (Match m : data.matches()) {
            if (comp != null && m.competition != comp) continue;
            if (season != null && m.season != season) continue;
            if (!teamBase.isEmpty() && !oppBase.isEmpty()) {
                boolean meeting = (m.homeIs(teamBase) && m.awayIs(oppBase))
                        || (m.homeIs(oppBase) && m.awayIs(teamBase));
                if (!meeting) continue;
            } else if (!teamBase.isEmpty()) {
                if (!matchesVenue(m, teamBase, venue)) continue;
            } else if (!oppBase.isEmpty()) {
                if (!m.involvesBase(oppBase)) continue;
            }
            filtered.add(m);
        }
        filtered.sort(byDateDescending());

        ObjectNode result = MAPPER.createObjectNode();
        result.put("count", filtered.size());
        ArrayNode list = result.putArray("matches");
        filtered.stream().limit(limit).forEach(m -> list.add(matchNode(m)));
        return result;
    }

    // ---- head_to_head --------------------------------------------------------

    public JsonNode toolHeadToHead(JsonNode args) {
        String aBase = key(text(args, "teamA"));
        String bBase = key(text(args, "teamB"));
        require(!aBase.isEmpty() && !bBase.isEmpty(), "head_to_head requires teamA and teamB");

        int aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
        String aDisplay = text(args, "teamA");
        String bDisplay = text(args, "teamB");
        List<Match> meetings = new ArrayList<>();

        for (Match m : data.matches()) {
            boolean aHome = m.homeIs(aBase) && m.awayIs(bBase);
            boolean bHome = m.homeIs(bBase) && m.awayIs(aBase);
            if (!aHome && !bHome) continue;
            meetings.add(m);

            int aFor = aHome ? m.homeGoals : m.awayGoals;
            int bFor = aHome ? m.awayGoals : m.homeGoals;
            aGoals += aFor;
            bGoals += bFor;
            if (aFor > bFor) aWins++;
            else if (bFor > aFor) bWins++;
            else draws++;
            aDisplay = aHome ? m.homeDisplay : m.awayDisplay;
            bDisplay = aHome ? m.awayDisplay : m.homeDisplay;
        }
        meetings.sort(byDateDescending());

        ObjectNode result = MAPPER.createObjectNode();
        result.put("teamA", aDisplay);
        result.put("teamB", bDisplay);
        result.put("totalMatches", meetings.size());
        result.put("teamAWins", aWins);
        result.put("teamBWins", bWins);
        result.put("draws", draws);
        result.put("teamAGoals", aGoals);
        result.put("teamBGoals", bGoals);
        ArrayNode list = result.putArray("matches");
        meetings.stream().limit(DEFAULT_MATCH_LIMIT).forEach(m -> list.add(matchNode(m)));
        return result;
    }

    // ---- team_stats ----------------------------------------------------------

    public JsonNode toolTeamStats(JsonNode args) {
        String teamBase = key(text(args, "team"));
        require(!teamBase.isEmpty(), "team_stats requires a team");
        Competition comp = Competition.resolve(text(args, "competition"));
        Integer season = optInt(args, "season");
        String venue = text(args, "venue");

        int matches = 0, wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        String display = text(args, "team");

        for (Match m : data.matches()) {
            if (comp != null && m.competition != comp) continue;
            if (season != null && m.season != season) continue;
            if (!matchesVenue(m, teamBase, venue)) continue;

            boolean home = m.homeIs(teamBase);
            int forGoals = home ? m.homeGoals : m.awayGoals;
            int againstGoals = home ? m.awayGoals : m.homeGoals;
            display = home ? m.homeDisplay : m.awayDisplay;

            matches++;
            gf += forGoals;
            ga += againstGoals;
            if (forGoals > againstGoals) wins++;
            else if (forGoals < againstGoals) losses++;
            else draws++;
        }

        ObjectNode result = MAPPER.createObjectNode();
        result.put("team", display);
        if (comp != null) result.put("competition", comp.key());
        if (season != null) result.put("season", season);
        result.put("venue", venueLabel(venue));
        result.put("matches", matches);
        result.put("wins", wins);
        result.put("draws", draws);
        result.put("losses", losses);
        result.put("goalsFor", gf);
        result.put("goalsAgainst", ga);
        result.put("goalDifference", gf - ga);
        result.put("winRate", matches == 0 ? 0.0 : round(wins / (double) matches));
        return result;
    }

    // ---- search_players ------------------------------------------------------

    public JsonNode toolSearchPlayers(JsonNode args) {
        String name = TeamNames.normalize(text(args, "name"));
        String nationality = TeamNames.normalize(text(args, "nationality"));
        String club = TeamNames.normalize(text(args, "club"));
        String position = text(args, "position").trim();
        Integer minOverall = optInt(args, "minOverall");
        int limit = clamp(optInt(args, "limit", DEFAULT_PLAYER_LIMIT), 1, 500);

        List<Player> filtered = new ArrayList<>();
        for (Player p : data.players()) {
            if (!name.isEmpty() && !p.nameKey.contains(name)) continue;
            if (!nationality.isEmpty() && !p.nationalityKey.equals(nationality)
                    && !p.nationalityKey.contains(nationality)) continue;
            if (!club.isEmpty() && !p.clubKey.contains(club)) continue;
            if (!position.isEmpty() && !p.position.equalsIgnoreCase(position)) continue;
            if (minOverall != null && p.overall < minOverall) continue;
            filtered.add(p);
        }
        filtered.sort(Comparator.comparingInt((Player p) -> p.overall).reversed()
                .thenComparing(p -> p.name));

        ObjectNode result = MAPPER.createObjectNode();
        result.put("count", filtered.size());
        ArrayNode list = result.putArray("players");
        filtered.stream().limit(limit).forEach(p -> list.add(playerNode(p)));
        return result;
    }

    // ---- competition_standings -----------------------------------------------

    public JsonNode toolStandings(JsonNode args) {
        Competition comp = Competition.resolve(text(args, "competition"));
        require(comp != null, "competition_standings requires a known competition");
        Integer season = optInt(args, "season");
        require(season != null, "competition_standings requires a season");

        Map<String, Standing> table = new LinkedHashMap<>();
        for (Match m : data.matches()) {
            if (m.competition != comp || m.season != season) continue;
            Standing home = table.computeIfAbsent(m.homeIdentity, k -> new Standing(m.homeDisplay));
            Standing away = table.computeIfAbsent(m.awayIdentity, k -> new Standing(m.awayDisplay));
            home.record(m.homeGoals, m.awayGoals);
            away.record(m.awayGoals, m.homeGoals);
        }

        List<Standing> rows = new ArrayList<>(table.values());
        rows.sort(Comparator.comparingInt((Standing s) -> s.points()).reversed()
                .thenComparing(Comparator.comparingInt(Standing::goalDifference).reversed())
                .thenComparing(Comparator.comparingInt((Standing s) -> s.goalsFor).reversed())
                .thenComparing(s -> s.team));

        ObjectNode result = MAPPER.createObjectNode();
        result.put("competition", comp.key());
        result.put("season", season);
        ArrayNode arr = result.putArray("table");
        int rank = 1;
        for (Standing s : rows) {
            ObjectNode row = arr.addObject();
            row.put("rank", rank++);
            row.put("team", s.team);
            row.put("points", s.points());
            row.put("played", s.played);
            row.put("wins", s.wins);
            row.put("draws", s.draws);
            row.put("losses", s.losses);
            row.put("goalsFor", s.goalsFor);
            row.put("goalsAgainst", s.goalsAgainst);
            row.put("goalDifference", s.goalDifference());
        }
        result.put("champion", rows.isEmpty() ? null : rows.get(0).team);
        return result;
    }

    // ---- league_statistics ---------------------------------------------------

    public JsonNode toolLeagueStatistics(JsonNode args) {
        Competition comp = Competition.resolve(text(args, "competition"));
        Integer season = optInt(args, "season");

        int matches = 0, totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0;
        List<Match> played = new ArrayList<>();
        for (Match m : data.matches()) {
            if (comp != null && m.competition != comp) continue;
            if (season != null && m.season != season) continue;
            matches++;
            totalGoals += m.homeGoals + m.awayGoals;
            if (m.homeGoals > m.awayGoals) homeWins++;
            else if (m.homeGoals < m.awayGoals) awayWins++;
            else draws++;
            played.add(m);
        }

        played.sort(Comparator.comparingInt((Match m) -> Math.abs(m.homeGoals - m.awayGoals)).reversed()
                .thenComparing(byDateDescending()));

        ObjectNode result = MAPPER.createObjectNode();
        if (comp != null) result.put("competition", comp.key());
        if (season != null) result.put("season", season);
        result.put("matches", matches);
        result.put("totalGoals", totalGoals);
        result.put("averageGoalsPerMatch", matches == 0 ? 0.0 : round(totalGoals / (double) matches));
        result.put("homeWins", homeWins);
        result.put("awayWins", awayWins);
        result.put("draws", draws);
        result.put("homeWinRate", matches == 0 ? 0.0 : round(homeWins / (double) matches));
        result.put("awayWinRate", matches == 0 ? 0.0 : round(awayWins / (double) matches));
        ArrayNode biggest = result.putArray("biggestWins");
        played.stream().filter(m -> m.homeGoals != m.awayGoals).limit(10).forEach(m -> {
            ObjectNode w = biggest.addObject();
            w.put("date", m.date);
            w.put("competition", m.competition.key());
            w.put("homeTeam", m.homeDisplay);
            w.put("awayTeam", m.awayDisplay);
            w.put("score", m.homeGoals + "-" + m.awayGoals);
            w.put("margin", Math.abs(m.homeGoals - m.awayGoals));
        });
        return result;
    }

    // ---- helpers -------------------------------------------------------------

    private boolean matchesVenue(Match m, String teamBase, String venue) {
        String v = venue == null ? "" : venue.toLowerCase(Locale.ROOT);
        return switch (v) {
            case "home" -> m.homeIs(teamBase);
            case "away" -> m.awayIs(teamBase);
            default -> m.involvesBase(teamBase);
        };
    }

    private static String venueLabel(String venue) {
        String v = venue == null ? "" : venue.toLowerCase(Locale.ROOT);
        return switch (v) {
            case "home" -> "home";
            case "away" -> "away";
            default -> "all";
        };
    }

    private Comparator<Match> byDateDescending() {
        return Comparator.comparing((Match m) -> m.date == null ? "" : m.date).reversed();
    }

    private ObjectNode matchNode(Match m) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("date", m.date);
        node.put("competition", m.competition.key());
        node.put("season", m.season);
        node.put("round", m.round);
        node.put("homeTeam", m.homeDisplay);
        node.put("awayTeam", m.awayDisplay);
        node.put("homeGoals", m.homeGoals);
        node.put("awayGoals", m.awayGoals);
        node.put("score", m.homeGoals + "-" + m.awayGoals);
        return node;
    }

    private ObjectNode playerNode(Player p) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("name", p.name);
        node.put("age", p.age);
        node.put("nationality", p.nationality);
        node.put("overall", p.overall);
        node.put("potential", p.potential);
        node.put("club", p.club);
        node.put("position", p.position);
        node.put("jerseyNumber", p.jerseyNumber);
        return node;
    }

    private static String text(JsonNode args, String field) {
        JsonNode v = args == null ? null : args.get(field);
        return (v == null || v.isNull()) ? "" : v.asText();
    }

    private static String key(String raw) {
        return raw.isEmpty() ? "" : TeamNames.matchKey(raw);
    }

    private static Integer optInt(JsonNode args, String field) {
        JsonNode v = args == null ? null : args.get(field);
        if (v == null || v.isNull()) return null;
        if (v.isNumber()) return v.asInt();
        try {
            return Integer.valueOf(v.asText().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static int optInt(JsonNode args, String field, int fallback) {
        Integer v = optInt(args, field);
        return v == null ? fallback : v;
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private static double round(double v) {
        return Math.round(v * 1000.0) / 1000.0;
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new IllegalArgumentException(message);
        }
    }

    /** Mutable accumulator for a league table row. */
    private static final class Standing {
        final String team;
        int played, wins, draws, losses, goalsFor, goalsAgainst;

        Standing(String team) {
            this.team = team;
        }

        void record(int forGoals, int againstGoals) {
            played++;
            goalsFor += forGoals;
            goalsAgainst += againstGoals;
            if (forGoals > againstGoals) wins++;
            else if (forGoals < againstGoals) losses++;
            else draws++;
        }

        int points() {
            return wins * 3 + draws;
        }

        int goalDifference() {
            return goalsFor - goalsAgainst;
        }
    }
}
