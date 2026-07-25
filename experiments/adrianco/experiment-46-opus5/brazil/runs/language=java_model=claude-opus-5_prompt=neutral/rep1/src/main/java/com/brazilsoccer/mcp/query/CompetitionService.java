package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;

/**
 * Competition level queries: season tables computed from match results, champions, relegation
 * zones and season summaries.
 *
 * <p>Nothing is hard coded - a table is the aggregation of every match of that edition present in
 * the graph, which is why every answer also reports how many matches it was computed from.
 */
public final class CompetitionService {

    /** One row of a computed season table. */
    public record StandingRow(int position, String teamId, TeamRecord record) {
    }

    /** Outcome of a knockout final, or the league champion. */
    public record TitleInfo(String championTeamId, String runnerUpTeamId, String explanation,
                            List<Match> decidingMatches) {
    }

    /** Aggregated numbers for one competition edition. */
    public record SeasonSummary(Competition competition, int season, int matches, int playedMatches,
                                int teams, double goalsPerMatch, double homeWinRate, double drawRate,
                                double awayWinRate, Optional<TitleInfo> title,
                                List<StandingRow> table, List<Match> biggestWins) {
    }

    private final KnowledgeGraph graph;

    public CompetitionService(KnowledgeGraph graph) {
        this.graph = graph;
    }

    /** Season table ordered by points, wins, goal difference and goals scored. */
    public List<StandingRow> standings(Competition competition, int season, Venue venue) {
        List<Match> matches = graph.matchesOf(competition, season);
        Map<String, List<Match>> byTeam = new LinkedHashMap<>();
        for (Match match : matches) {
            byTeam.computeIfAbsent(match.homeTeamId(), k -> new ArrayList<>()).add(match);
            byTeam.computeIfAbsent(match.awayTeamId(), k -> new ArrayList<>()).add(match);
        }
        List<Map.Entry<String, TeamRecord>> rows = new ArrayList<>();
        byTeam.forEach((teamId, teamMatches) -> rows.add(Map.entry(teamId, TeamRecord.of(teamMatches, teamId, venue))));
        rows.sort(Comparator
                .<Map.Entry<String, TeamRecord>>comparingInt(e -> e.getValue().points()).reversed()
                .thenComparing(Comparator.<Map.Entry<String, TeamRecord>>comparingInt(e -> e.getValue().wins()).reversed())
                .thenComparing(Comparator.<Map.Entry<String, TeamRecord>>comparingInt(e -> e.getValue().goalDifference()).reversed())
                .thenComparing(Comparator.<Map.Entry<String, TeamRecord>>comparingInt(e -> e.getValue().goalsFor()).reversed())
                .thenComparing(e -> graph.nameOf(e.getKey())));
        List<StandingRow> table = new ArrayList<>(rows.size());
        for (int i = 0; i < rows.size(); i++) {
            table.add(new StandingRow(i + 1, rows.get(i).getKey(), rows.get(i).getValue()));
        }
        return table;
    }

    /**
     * Champion of an edition: the top of the table for leagues, the winner of the final for
     * knockout competitions. Empty when the dataset does not contain enough matches to tell.
     */
    public Optional<TitleInfo> champion(Competition competition, int season) {
        List<Match> matches = graph.matchesOf(competition, season);
        if (matches.isEmpty()) {
            return Optional.empty();
        }
        if (competition.isLeague()) {
            List<StandingRow> table = standings(competition, season, Venue.ALL);
            if (table.size() < 8) {
                return Optional.empty();
            }
            int played = (int) matches.stream().filter(Match::isPlayed).count();
            int expected = table.size() * (table.size() - 1);
            String explanation = "league table computed from " + played + " of the "
                    + expected + " matches of a full double round robin";
            String runnerUp = table.size() > 1 ? table.get(1).teamId() : null;
            return Optional.of(new TitleInfo(table.get(0).teamId(), runnerUp, explanation, List.of()));
        }
        return knockoutWinner(competition, season, matches);
    }

    private Optional<TitleInfo> knockoutWinner(Competition competition, int season, List<Match> matches) {
        List<Match> finals = matches.stream()
                .filter(Match::isPlayed)
                .filter(m -> isFinalRound(m.round()))
                .toList();
        if (finals.isEmpty()) {
            finals = lastNumberedRound(matches);
        }
        if (finals.isEmpty()) {
            return Optional.empty();
        }
        Set<String> teams = new java.util.LinkedHashSet<>();
        finals.forEach(m -> {
            teams.add(m.homeTeamId());
            teams.add(m.awayTeamId());
        });
        if (teams.size() != 2) {
            return Optional.empty();
        }
        List<String> pair = new ArrayList<>(teams);
        int aggregateA = 0;
        int aggregateB = 0;
        for (Match match : finals) {
            aggregateA += match.goalsFor(pair.get(0));
            aggregateB += match.goalsFor(pair.get(1));
        }
        if (aggregateA == aggregateB) {
            return Optional.of(new TitleInfo(null, null,
                    "the final finished level on aggregate (" + aggregateA + "-" + aggregateB
                            + "); the dataset has no penalty shoot-out data", finals));
        }
        boolean firstWins = aggregateA > aggregateB;
        String explanation = "winner of the " + competition.displayName() + " " + season
                + " final on aggregate " + Math.max(aggregateA, aggregateB) + "-" + Math.min(aggregateA, aggregateB);
        return Optional.of(new TitleInfo(firstWins ? pair.get(0) : pair.get(1),
                firstWins ? pair.get(1) : pair.get(0), explanation, finals));
    }

    private static boolean isFinalRound(String round) {
        if (round == null) {
            return false;
        }
        String simplified = TextUtils.simplify(round);
        return simplified.contains("final") && !simplified.contains("semi") && !simplified.contains("quarter");
    }

    /** Fallback for cups whose rounds are plain numbers: the highest round with a single tie. */
    private static List<Match> lastNumberedRound(List<Match> matches) {
        TreeMap<Integer, List<Match>> byRound = new TreeMap<>();
        for (Match match : matches) {
            if (!match.isPlayed() || match.round() == null) {
                continue;
            }
            try {
                byRound.computeIfAbsent(Integer.parseInt(match.round().trim()), k -> new ArrayList<>()).add(match);
            } catch (NumberFormatException ignored) {
                // non numeric round, handled by isFinalRound
            }
        }
        for (Map.Entry<Integer, List<Match>> entry : byRound.descendingMap().entrySet()) {
            Set<String> teams = new java.util.LinkedHashSet<>();
            entry.getValue().forEach(m -> {
                teams.add(m.homeTeamId());
                teams.add(m.awayTeamId());
            });
            if (teams.size() == 2 && entry.getValue().size() <= 2) {
                return entry.getValue();
            }
        }
        return List.of();
    }

    /**
     * Teams in the relegation zone. Only meaningful for a complete league season, so the caller
     * gets an empty list when the edition looks partial.
     */
    public List<StandingRow> relegationZone(Competition competition, int season, int places) {
        if (!competition.isLeague()) {
            return List.of();
        }
        List<StandingRow> table = standings(competition, season, Venue.ALL);
        if (table.size() < 12) {
            return List.of();
        }
        return table.subList(Math.max(0, table.size() - places), table.size());
    }

    /** Everything worth knowing about one edition. */
    public SeasonSummary summary(Competition competition, int season) {
        List<Match> matches = graph.matchesOf(competition, season);
        List<Match> played = matches.stream().filter(Match::isPlayed).toList();
        int goals = played.stream().mapToInt(Match::totalGoals).sum();
        long homeWins = played.stream().filter(m -> m.homeGoals() > m.awayGoals()).count();
        long draws = played.stream().filter(m -> m.homeGoals().intValue() == m.awayGoals().intValue()).count();
        long awayWins = played.size() - homeWins - draws;
        List<StandingRow> table = standings(competition, season, Venue.ALL);
        List<Match> biggest = played.stream()
                .sorted(Comparator.comparingInt(Match::goalDifference).reversed()
                        .thenComparing(Comparator.comparingInt(Match::totalGoals).reversed()))
                .limit(5)
                .toList();
        double denominator = played.isEmpty() ? 1 : played.size();
        return new SeasonSummary(competition, season, matches.size(), played.size(), table.size(),
                goals / denominator, homeWins / denominator, draws / denominator, awayWins / denominator,
                champion(competition, season), table, biggest);
    }
}
