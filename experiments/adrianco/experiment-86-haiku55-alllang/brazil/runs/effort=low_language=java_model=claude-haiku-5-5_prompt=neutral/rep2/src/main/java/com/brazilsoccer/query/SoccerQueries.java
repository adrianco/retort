package com.brazilsoccer.query;

import com.brazilsoccer.data.DataRepository;
import com.brazilsoccer.data.Match;
import com.brazilsoccer.data.Player;
import com.brazilsoccer.data.TeamNames;

import java.time.LocalDate;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Stream;

import static java.util.Comparator.nullsLast;

/** Read-only queries over a {@link DataRepository}. Null filter fields mean "no constraint". */
public final class SoccerQueries {

    public enum Venue {
        ANY, HOME, AWAY;

        public static Venue parse(String raw) {
            if (raw == null || raw.isBlank()) {
                return ANY;
            }
            return switch (raw.trim().toLowerCase(Locale.ROOT)) {
                case "home" -> HOME;
                case "away" -> AWAY;
                case "any", "either" -> ANY;
                default -> throw new IllegalArgumentException("venue must be home, away or any, got: " + raw);
            };
        }
    }

    public record MatchFilter(String team, String opponent, String competition, Integer season,
                              LocalDate from, LocalDate to, Venue venue) {
        public MatchFilter {
            venue = venue == null ? Venue.ANY : venue;
        }
    }

    public record PlayerFilter(String name, String nationality, String club, String position, Integer minOverall) {
    }

    /** Head-to-head summary. {@code matches} is newest first and includes fixtures without a score. */
    public record HeadToHead(String teamA, String teamB, List<Match> matches,
                             int winsA, int draws, int winsB, int goalsA, int goalsB) {
    }

    public record LeagueStats(int matches, double avgGoalsPerMatch, double homeWinPct, double drawPct,
                              double awayWinPct, List<Match> biggestWins) {
    }

    private final DataRepository repo;

    public SoccerQueries(DataRepository repo) {
        this.repo = repo;
    }

    /** Matching fixtures, newest first, capped at {@code limit}. */
    public List<Match> findMatches(MatchFilter filter, int limit) {
        return stream(filter)
                .sorted(Comparator.comparing(Match::date).reversed())
                .limit(limit)
                .toList();
    }

    /** Win/draw/loss record for one team, from its home games, away games or both. */
    public TeamTally teamRecord(String team, Integer season, String competition, Venue venue) {
        TeamTally tally = new TeamTally(team);
        stream(new MatchFilter(team, null, competition, season, null, null, venue))
                .filter(Match::hasResult)
                .forEach(m -> {
                    if (venue != Venue.AWAY && TeamNames.matches(m.homeTeam(), team)) {
                        tally.addResult(m.homeGoals(), m.awayGoals());
                    } else if (venue != Venue.HOME && TeamNames.matches(m.awayTeam(), team)) {
                        tally.addResult(m.awayGoals(), m.homeGoals());
                    }
                });
        return tally;
    }

    public HeadToHead headToHead(String teamA, String teamB, int limit) {
        List<Match> all = stream(new MatchFilter(teamA, teamB, null, null, null, null, Venue.ANY))
                .sorted(Comparator.comparing(Match::date).reversed())
                .toList();
        int winsA = 0;
        int draws = 0;
        int winsB = 0;
        int goalsA = 0;
        int goalsB = 0;
        for (Match m : all) {
            if (!m.hasResult()) {
                continue;
            }
            boolean aIsHome = TeamNames.matches(m.homeTeam(), teamA);
            int scoredA = aIsHome ? m.homeGoals() : m.awayGoals();
            int scoredB = aIsHome ? m.awayGoals() : m.homeGoals();
            goalsA += scoredA;
            goalsB += scoredB;
            if (scoredA > scoredB) {
                winsA++;
            } else if (scoredA == scoredB) {
                draws++;
            } else {
                winsB++;
            }
        }
        return new HeadToHead(teamA, teamB, all.stream().limit(limit).toList(),
                winsA, draws, winsB, goalsA, goalsB);
    }

    /** League table for one competition and season, computed from results. */
    public List<TeamTally> standings(String competition, int season) {
        Map<String, TeamTally> tallies = new LinkedHashMap<>();
        stream(new MatchFilter(null, null, competition, season, null, null, Venue.ANY))
                .filter(Match::hasResult)
                .forEach(m -> {
                    tallyFor(tallies, m.homeTeam()).addResult(m.homeGoals(), m.awayGoals());
                    tallyFor(tallies, m.awayTeam()).addResult(m.awayGoals(), m.homeGoals());
                });
        return tallies.values().stream()
                .sorted(Comparator.comparingInt(TeamTally::points)
                        .thenComparingInt(TeamTally::won)
                        .thenComparingInt(TeamTally::goalDifference)
                        .thenComparingInt(TeamTally::goalsFor)
                        .reversed())
                .toList();
    }

    /** Teams ranked by win rate for the given venue, ignoring teams with fewer than {@code minMatches} games. */
    public List<TeamTally> rankTeams(String competition, Integer season, Venue venue, int minMatches, int limit) {
        Map<String, TeamTally> tallies = new LinkedHashMap<>();
        stream(new MatchFilter(null, null, competition, season, null, null, Venue.ANY))
                .filter(Match::hasResult)
                .forEach(m -> {
                    if (venue != Venue.AWAY) {
                        tallyFor(tallies, m.homeTeam()).addResult(m.homeGoals(), m.awayGoals());
                    }
                    if (venue != Venue.HOME) {
                        tallyFor(tallies, m.awayTeam()).addResult(m.awayGoals(), m.homeGoals());
                    }
                });
        return tallies.values().stream()
                .filter(t -> t.played() >= minMatches)
                .sorted(Comparator.comparingDouble(TeamTally::winRate)
                        .thenComparingInt(TeamTally::won)
                        .reversed())
                .limit(limit)
                .toList();
    }

    public LeagueStats leagueStats(String competition, Integer season) {
        List<Match> played = stream(new MatchFilter(null, null, competition, season, null, null, Venue.ANY))
                .filter(Match::hasResult)
                .toList();
        int n = played.size();
        if (n == 0) {
            return new LeagueStats(0, 0, 0, 0, 0, List.of());
        }
        long goals = 0;
        long homeWins = 0;
        long draws = 0;
        long awayWins = 0;
        for (Match m : played) {
            goals += m.homeGoals() + m.awayGoals();
            if (m.homeGoals() > m.awayGoals()) {
                homeWins++;
            } else if (m.homeGoals().equals(m.awayGoals())) {
                draws++;
            } else {
                awayWins++;
            }
        }
        List<Match> biggestWins = played.stream()
                .filter(m -> !m.homeGoals().equals(m.awayGoals()))
                .sorted(Comparator.comparingInt((Match m) -> Math.abs(m.homeGoals() - m.awayGoals())).reversed())
                .limit(5)
                .toList();
        return new LeagueStats(n, (double) goals / n, 100.0 * homeWins / n, 100.0 * draws / n,
                100.0 * awayWins / n, biggestWins);
    }

    public List<Player> searchPlayers(PlayerFilter filter, int limit) {
        return repo.players().stream()
                .filter(p -> filter.name() == null
                        || TeamNames.normalize(p.name()).contains(TeamNames.normalize(filter.name())))
                .filter(p -> filter.nationality() == null
                        || TeamNames.normalize(p.nationality()).equals(TeamNames.normalize(filter.nationality())))
                .filter(p -> filter.club() == null || TeamNames.matches(p.club(), filter.club()))
                .filter(p -> filter.position() == null || filter.position().equalsIgnoreCase(p.position()))
                .filter(p -> filter.minOverall() == null
                        || (p.overall() != null && p.overall() >= filter.minOverall()))
                .sorted(Comparator.comparing(Player::overall, nullsLast(Comparator.reverseOrder())))
                .limit(limit)
                .toList();
    }

    private Stream<Match> stream(MatchFilter f) {
        return repo.matches().stream().filter(m -> matchesFilter(m, f));
    }

    private static boolean matchesFilter(Match m, MatchFilter f) {
        if (f.competition() != null
                && !TeamNames.normalize(m.competition()).contains(TeamNames.normalize(f.competition()))) {
            return false;
        }
        if (f.season() != null && m.season() != f.season()) {
            return false;
        }
        if (f.from() != null && m.date().isBefore(f.from())) {
            return false;
        }
        if (f.to() != null && m.date().isAfter(f.to())) {
            return false;
        }
        boolean asHome = f.team() == null || (f.venue() != Venue.AWAY && TeamNames.matches(m.homeTeam(), f.team()));
        boolean asAway = f.team() == null || (f.venue() != Venue.HOME && TeamNames.matches(m.awayTeam(), f.team()));
        if (!asHome && !asAway) {
            return false;
        }
        if (f.opponent() == null) {
            return true;
        }
        if (f.team() == null) {
            return TeamNames.matches(m.homeTeam(), f.opponent()) || TeamNames.matches(m.awayTeam(), f.opponent());
        }
        return (asHome && TeamNames.matches(m.awayTeam(), f.opponent()))
                || (asAway && TeamNames.matches(m.homeTeam(), f.opponent()));
    }

    private static TeamTally tallyFor(Map<String, TeamTally> tallies, String teamName) {
        return tallies.computeIfAbsent(TeamNames.key(teamName),
                k -> new TeamTally(TeamNames.displayName(teamName)));
    }
}
