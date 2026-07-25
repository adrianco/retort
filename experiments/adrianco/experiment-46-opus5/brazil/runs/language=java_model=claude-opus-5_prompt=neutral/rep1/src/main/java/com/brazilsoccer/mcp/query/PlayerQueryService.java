package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/**
 * Player lookups over the FIFA dataset.
 *
 * <p>Club filters go through the same {@code TeamRegistry} used by the match data, so
 * "Sport Club do Recife" (player file) and "Sport-PE" (match file) resolve to the same club node
 * and cross-file questions ("how did the club of player X do last season?") can be answered.
 */
public final class PlayerQueryService {

    /** Criteria for {@link #search}; all fields optional. */
    public static final class PlayerQuery {
        private String name;
        private String nationality;
        private String clubTeamId;
        private String clubText;
        private Player.PositionGroup positionGroup;
        private String position;
        private Integer minOverall;
        private Integer maxAge;
        private String sortBy = "overall";
        private int limit = 20;

        public static PlayerQuery create() {
            return new PlayerQuery();
        }

        public PlayerQuery name(String name) {
            this.name = name;
            return this;
        }

        public PlayerQuery nationality(String nationality) {
            this.nationality = nationality;
            return this;
        }

        public PlayerQuery clubTeamId(String clubTeamId) {
            this.clubTeamId = clubTeamId;
            return this;
        }

        public PlayerQuery clubText(String clubText) {
            this.clubText = clubText;
            return this;
        }

        public PlayerQuery positionGroup(Player.PositionGroup group) {
            this.positionGroup = group;
            return this;
        }

        public PlayerQuery position(String position) {
            this.position = position;
            return this;
        }

        public PlayerQuery minOverall(Integer minOverall) {
            this.minOverall = minOverall;
            return this;
        }

        public PlayerQuery maxAge(Integer maxAge) {
            this.maxAge = maxAge;
            return this;
        }

        public PlayerQuery sortBy(String sortBy) {
            this.sortBy = sortBy == null || sortBy.isBlank() ? "overall" : sortBy;
            return this;
        }

        public PlayerQuery limit(int limit) {
            this.limit = limit;
            return this;
        }

        public int limit() {
            return limit;
        }
    }

    /** Aggregated view of the players of one club. */
    public record ClubSummary(String teamId, String clubName, int players, double averageOverall,
                              Optional<Player> bestPlayer) {
    }

    private final KnowledgeGraph graph;

    public PlayerQueryService(KnowledgeGraph graph) {
        this.graph = graph;
    }

    /** Players matching every supplied criterion, best first (sorted by {@code sortBy}). */
    public List<Player> search(PlayerQuery query) {
        List<Player> candidates = candidates(query);
        List<Player> result = new ArrayList<>();
        for (Player player : candidates) {
            if (accepts(player, query)) {
                result.add(player);
            }
        }
        result.sort(comparator(query.sortBy));
        return result;
    }

    private List<Player> candidates(PlayerQuery query) {
        if (query.clubTeamId != null) {
            return graph.playersOfClub(query.clubTeamId);
        }
        if (query.nationality != null && !query.nationality.isBlank()) {
            List<Player> byNationality = graph.playersOfNationality(query.nationality);
            if (!byNationality.isEmpty()) {
                return byNationality;
            }
        }
        return graph.players();
    }

    private boolean accepts(Player player, PlayerQuery query) {
        if (query.name != null && !query.name.isBlank()
                && !TextUtils.containsIgnoringAccents(player.name(), query.name)
                && !matchesAnyToken(player.name(), query.name)) {
            return false;
        }
        if (query.nationality != null && !query.nationality.isBlank()
                && !TextUtils.simplify(player.nationality()).equals(TextUtils.simplify(query.nationality))) {
            return false;
        }
        if (query.clubTeamId != null && !query.clubTeamId.equals(player.clubTeamId())) {
            return false;
        }
        if (query.clubText != null && !query.clubText.isBlank()
                && !TextUtils.containsIgnoringAccents(player.club() == null ? "" : player.club(), query.clubText)) {
            return false;
        }
        if (query.positionGroup != null && query.positionGroup != Player.PositionGroup.UNKNOWN
                && player.positionGroup() != query.positionGroup) {
            return false;
        }
        if (query.position != null && !query.position.isBlank()
                && !query.position.equalsIgnoreCase(player.position() == null ? "" : player.position())) {
            return false;
        }
        if (query.minOverall != null && (player.overall() == null || player.overall() < query.minOverall)) {
            return false;
        }
        if (query.maxAge != null && (player.age() == null || player.age() > query.maxAge)) {
            return false;
        }
        return true;
    }

    /** True when any word of the query appears as a word of the player name. */
    private static boolean matchesAnyToken(String playerName, String query) {
        String simplifiedName = TextUtils.simplify(playerName);
        for (String token : TextUtils.simplify(query).split(" ")) {
            if (token.length() >= 3 && (simplifiedName.equals(token)
                    || simplifiedName.startsWith(token + " ")
                    || simplifiedName.contains(" " + token))) {
                return true;
            }
        }
        return false;
    }

    private static Comparator<Player> comparator(String sortBy) {
        return switch (sortBy.toLowerCase(Locale.ROOT)) {
            case "potential" -> Comparator.comparing(Player::potential, Comparator.nullsLast(Comparator.reverseOrder()))
                    .thenComparing(Player::name);
            case "age" -> Comparator.comparing(Player::age, Comparator.nullsLast(Comparator.naturalOrder()))
                    .thenComparing(Player::name);
            case "name" -> Comparator.comparing(Player::name);
            default -> Comparator.comparing(Player::overall, Comparator.nullsLast(Comparator.reverseOrder()))
                    .thenComparing(Player::name);
        };
    }

    /** Best single match for a player name, preferring exact and prefix matches. */
    public Optional<Player> findByName(String name) {
        if (name == null || name.isBlank()) {
            return Optional.empty();
        }
        String needle = TextUtils.simplify(name);
        Player exact = null;
        Player prefix = null;
        Player contains = null;
        for (Player player : graph.players()) {
            String candidate = TextUtils.simplify(player.name());
            if (candidate.equals(needle)) {
                if (exact == null || better(player, exact)) {
                    exact = player;
                }
            } else if (candidate.startsWith(needle)) {
                if (prefix == null || better(player, prefix)) {
                    prefix = player;
                }
            } else if (candidate.contains(needle)) {
                if (contains == null || better(player, contains)) {
                    contains = player;
                }
            }
        }
        return Optional.ofNullable(exact != null ? exact : prefix != null ? prefix : contains);
    }

    private static boolean better(Player a, Player b) {
        int overallA = a.overall() == null ? 0 : a.overall();
        int overallB = b.overall() == null ? 0 : b.overall();
        return overallA > overallB;
    }

    /** Players whose name shares a word with the query - used to suggest alternatives. */
    public List<Player> suggestions(String name, int limit) {
        return search(PlayerQuery.create().name(name).limit(limit)).stream().limit(limit).toList();
    }

    /**
     * Per-club aggregation ("Flamengo: 8 players, avg rating 74"), optionally restricted to one
     * nationality and ordered by squad size then average rating.
     */
    public List<ClubSummary> clubSummaries(String nationality, int minPlayers, int limit) {
        Map<String, List<Player>> byClub = new LinkedHashMap<>();
        for (Player player : graph.players()) {
            if (player.clubTeamId() == null) {
                continue;
            }
            if (nationality != null && !nationality.isBlank()
                    && !TextUtils.simplify(player.nationality()).equals(TextUtils.simplify(nationality))) {
                continue;
            }
            byClub.computeIfAbsent(player.clubTeamId(), k -> new ArrayList<>()).add(player);
        }
        List<ClubSummary> summaries = new ArrayList<>();
        byClub.forEach((teamId, players) -> {
            if (players.size() < minPlayers) {
                return;
            }
            double average = players.stream().filter(p -> p.overall() != null)
                    .mapToInt(Player::overall).average().orElse(0);
            Optional<Player> best = players.stream()
                    .max(Comparator.comparing(Player::overall, Comparator.nullsFirst(Comparator.naturalOrder())));
            String clubName = graph.team(teamId).map(Team::displayName)
                    .orElseGet(() -> players.get(0).club());
            summaries.add(new ClubSummary(teamId, clubName, players.size(), average, best));
        });
        summaries.sort(Comparator.comparingInt(ClubSummary::players).reversed()
                .thenComparing(Comparator.comparingDouble(ClubSummary::averageOverall).reversed())
                .thenComparing(ClubSummary::clubName));
        return summaries.size() <= limit ? summaries : summaries.subList(0, limit);
    }

    /** Clubs of the player dataset that also have match data in the graph. */
    public List<ClubSummary> clubsWithMatchData(String nationality, int limit) {
        return clubSummaries(nationality, 1, Integer.MAX_VALUE).stream()
                .filter(summary -> graph.matchesOf(summary.teamId()).size() > 0)
                .limit(limit)
                .toList();
    }
}
