package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.model.Match;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Aggregated statistics over any set of matches (the caller filters first with
 * {@link MatchQueryService}, so the same code serves "all Brasileirão matches", "Palmeiras away
 * matches in 2023" and everything in between).
 */
public final class StatisticsService {

    /** Global numbers for a set of matches. */
    public record Overview(int matches, int played, int goals, double goalsPerMatch,
                           long homeWins, long draws, long awayWins) {

        public double homeWinRate() {
            return played == 0 ? 0 : (double) homeWins / played;
        }

        public double drawRate() {
            return played == 0 ? 0 : (double) draws / played;
        }

        public double awayWinRate() {
            return played == 0 ? 0 : (double) awayWins / played;
        }
    }

    /** One club in a leaderboard. */
    public record TeamRanking(String teamId, TeamRecord record) {
    }

    /** Ranking criteria supported by {@link #rank}. */
    public enum Metric {
        POINTS, POINTS_PER_GAME, WIN_RATE, WINS, GOALS_SCORED, GOALS_CONCEDED, GOAL_DIFFERENCE;

        public static Metric parse(String raw) {
            if (raw == null || raw.isBlank()) {
                return POINTS;
            }
            return switch (raw.trim().toLowerCase(Locale.ROOT).replace('-', '_').replace(' ', '_')) {
                case "points", "pts" -> POINTS;
                case "points_per_game", "ppg" -> POINTS_PER_GAME;
                case "win_rate", "winrate", "wins_percentage" -> WIN_RATE;
                case "wins" -> WINS;
                case "goals", "goals_scored", "goals_for", "most_goals" -> GOALS_SCORED;
                case "goals_conceded", "goals_against", "defence", "defense" -> GOALS_CONCEDED;
                case "goal_difference", "gd" -> GOAL_DIFFERENCE;
                default -> POINTS;
            };
        }
    }

    private StatisticsService() {
    }

    public static Overview overview(List<Match> matches) {
        int played = 0;
        int goals = 0;
        long homeWins = 0;
        long draws = 0;
        long awayWins = 0;
        for (Match match : matches) {
            if (!match.isPlayed()) {
                continue;
            }
            played++;
            goals += match.totalGoals();
            if (match.homeGoals() > match.awayGoals()) {
                homeWins++;
            } else if (match.homeGoals().intValue() == match.awayGoals().intValue()) {
                draws++;
            } else {
                awayWins++;
            }
        }
        double perMatch = played == 0 ? 0 : (double) goals / played;
        return new Overview(matches.size(), played, goals, perMatch, homeWins, draws, awayWins);
    }

    /** Per-club leaderboard built from the given matches. */
    public static List<TeamRanking> rank(List<Match> matches, Venue venue, Metric metric,
                                         int minMatches, int limit) {
        Map<String, List<Match>> byTeam = new LinkedHashMap<>();
        for (Match match : matches) {
            if (!match.isPlayed()) {
                continue;
            }
            if (venue != Venue.AWAY) {
                byTeam.computeIfAbsent(match.homeTeamId(), k -> new ArrayList<>()).add(match);
            }
            if (venue != Venue.HOME) {
                byTeam.computeIfAbsent(match.awayTeamId(), k -> new ArrayList<>()).add(match);
            }
        }
        List<TeamRanking> rankings = new ArrayList<>();
        byTeam.forEach((teamId, teamMatches) -> {
            TeamRecord record = TeamRecord.of(teamMatches, teamId, venue);
            if (record.played() >= minMatches) {
                rankings.add(new TeamRanking(teamId, record));
            }
        });
        rankings.sort(comparator(metric));
        return rankings.size() <= limit ? rankings : rankings.subList(0, limit);
    }

    private static Comparator<TeamRanking> comparator(Metric metric) {
        Comparator<TeamRanking> comparator = switch (metric) {
            case POINTS -> Comparator.comparingInt(r -> r.record().points());
            case POINTS_PER_GAME -> Comparator.comparingDouble(r -> r.record().pointsPerGame());
            case WIN_RATE -> Comparator.comparingDouble(r -> r.record().winRate());
            case WINS -> Comparator.comparingInt(r -> r.record().wins());
            case GOALS_SCORED -> Comparator.comparingInt(r -> r.record().goalsFor());
            case GOAL_DIFFERENCE -> Comparator.comparingInt(r -> r.record().goalDifference());
            case GOALS_CONCEDED -> Comparator.<TeamRanking>comparingInt(r -> r.record().goalsAgainst()).reversed();
        };
        return comparator.reversed()
                .thenComparing(Comparator.<TeamRanking>comparingInt(r -> r.record().played()).reversed())
                .thenComparing(TeamRanking::teamId);
    }

    /** Matches ordered by winning margin (then total goals). */
    public static List<Match> biggestWins(List<Match> matches, int limit) {
        return matches.stream()
                .filter(Match::isPlayed)
                .filter(m -> m.goalDifference() > 0)
                .sorted(Comparator.comparingInt(Match::goalDifference).reversed()
                        .thenComparing(Comparator.comparingInt(Match::totalGoals).reversed())
                        .thenComparing(Match::id))
                .limit(limit)
                .toList();
    }

    /** Matches ordered by total goals scored. */
    public static List<Match> highestScoring(List<Match> matches, int limit) {
        return matches.stream()
                .filter(Match::isPlayed)
                .sorted(Comparator.comparingInt(Match::totalGoals).reversed()
                        .thenComparing(Comparator.comparingInt(Match::goalDifference).reversed())
                        .thenComparing(Match::id))
                .limit(limit)
                .toList();
    }
}
