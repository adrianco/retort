package com.brazilsoccer.mcp.graph;

import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NavigableSet;
import java.util.Optional;
import java.util.TreeSet;

/**
 * In-memory knowledge graph over the Brazilian soccer datasets.
 *
 * <p>Nodes: {@link Team} (clubs), {@link Match}, {@link Player} and {@link Competition}.
 * Edges: {@code (Team) -[HOME_TEAM|AWAY_TEAM]-> (Match)}, {@code (Match) -[PART_OF]-> (Competition)}
 * and {@code (Player) -[PLAYS_FOR]-> (Team)}. The edges are materialised as adjacency indexes so
 * that every MCP tool answers from pre-computed lists instead of scanning the CSV rows: a team
 * lookup is a hash lookup, and the heaviest aggregation (a full season table) touches a few
 * hundred matches.
 */
public final class KnowledgeGraph {

    /** Provenance of one bundled CSV file. */
    public record DatasetInfo(String fileName, String description, String license, int rowsRead,
                              int recordsContributed) {
    }

    /** Diagnostics collected while merging the overlapping datasets. */
    public record LoadReport(int rawMatchRows, int mergedDuplicates, int scoreConflicts,
                             int unresolvedTeams, long loadMillis) {
    }

    private final TeamRegistry registry;
    private final List<Match> matches;
    private final List<Player> players;
    private final List<DatasetInfo> datasets;
    private final LoadReport report;

    private final Map<String, List<Match>> matchesByTeam = new LinkedHashMap<>();
    private final Map<String, List<Match>> matchesByCompetitionSeason = new LinkedHashMap<>();
    private final Map<Competition, NavigableSet<Integer>> seasonsByCompetition = new EnumMap<>(Competition.class);
    private final Map<String, List<Player>> playersByClub = new LinkedHashMap<>();
    private final Map<String, List<Player>> playersByNationality = new LinkedHashMap<>();

    public KnowledgeGraph(TeamRegistry registry, List<Match> matches, List<Player> players,
                          List<DatasetInfo> datasets, LoadReport report) {
        this.registry = registry;
        this.matches = List.copyOf(matches);
        this.players = List.copyOf(players);
        this.datasets = List.copyOf(datasets);
        this.report = report;
        index();
    }

    private void index() {
        for (Match match : matches) {
            matchesByTeam.computeIfAbsent(match.homeTeamId(), k -> new ArrayList<>()).add(match);
            matchesByTeam.computeIfAbsent(match.awayTeamId(), k -> new ArrayList<>()).add(match);
            matchesByCompetitionSeason
                    .computeIfAbsent(key(match.competition(), match.season()), k -> new ArrayList<>())
                    .add(match);
            seasonsByCompetition
                    .computeIfAbsent(match.competition(), k -> new TreeSet<>())
                    .add(match.season());
            registry.team(match.homeTeamId()).ifPresent(Team::incrementMatchCount);
            registry.team(match.awayTeamId()).ifPresent(Team::incrementMatchCount);
        }
        Comparator<Match> byDate = Comparator
                .comparing(Match::date, Comparator.nullsLast(Comparator.naturalOrder()))
                .thenComparing(Match::id);
        matchesByTeam.values().forEach(list -> list.sort(byDate));
        matchesByCompetitionSeason.values().forEach(list -> list.sort(byDate));

        for (Player player : players) {
            if (player.clubTeamId() != null) {
                playersByClub.computeIfAbsent(player.clubTeamId(), k -> new ArrayList<>()).add(player);
                registry.team(player.clubTeamId()).ifPresent(Team::incrementPlayerCount);
            }
            if (player.nationality() != null) {
                playersByNationality
                        .computeIfAbsent(TextUtils.simplify(player.nationality()), k -> new ArrayList<>())
                        .add(player);
            }
        }
        Comparator<Player> byRating = Comparator
                .comparing(Player::overall, Comparator.nullsLast(Comparator.reverseOrder()))
                .thenComparing(Player::name);
        playersByClub.values().forEach(list -> list.sort(byRating));
        playersByNationality.values().forEach(list -> list.sort(byRating));
    }

    private static String key(Competition competition, int season) {
        return competition.id() + "|" + season;
    }

    public TeamRegistry registry() {
        return registry;
    }

    public List<Match> matches() {
        return matches;
    }

    public List<Player> players() {
        return players;
    }

    public List<DatasetInfo> datasets() {
        return datasets;
    }

    public LoadReport report() {
        return report;
    }

    /** All matches of a club, ordered by date. */
    public List<Match> matchesOf(String teamId) {
        return matchesByTeam.getOrDefault(teamId, List.of());
    }

    /** All matches of one competition edition, ordered by date. */
    public List<Match> matchesOf(Competition competition, int season) {
        return matchesByCompetitionSeason.getOrDefault(key(competition, season), List.of());
    }

    /** Seasons available for a competition. */
    public NavigableSet<Integer> seasons(Competition competition) {
        return seasonsByCompetition.getOrDefault(competition, new TreeSet<>());
    }

    public Map<Competition, NavigableSet<Integer>> coverage() {
        return seasonsByCompetition;
    }

    /** Matches between two clubs (both orientations), ordered by date. */
    public List<Match> headToHead(String teamA, String teamB) {
        return matchesOf(teamA).stream().filter(m -> m.involves(teamB)).toList();
    }

    public List<Player> playersOfClub(String teamId) {
        return playersByClub.getOrDefault(teamId, List.of());
    }

    public List<Player> playersOfNationality(String nationality) {
        return playersByNationality.getOrDefault(TextUtils.simplify(nationality), List.of());
    }

    /** Clubs that have at least one player in the FIFA dataset. */
    public Map<String, List<Player>> clubsWithPlayers() {
        return playersByClub;
    }

    public Optional<Team> team(String id) {
        return registry.team(id);
    }

    /** Display name for a club id, falling back to the id itself. */
    public String nameOf(String teamId) {
        return registry.team(teamId).map(Team::displayName).orElse(teamId);
    }

    public int teamCount() {
        return registry.size();
    }

    /** Number of graph edges (2 per match for the clubs, 1 per match for the competition,
     * 1 per player with a club). */
    public long edgeCount() {
        long playerEdges = players.stream().filter(p -> p.clubTeamId() != null).count();
        return (long) matches.size() * 3 + playerEdges;
    }
}
