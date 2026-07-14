package com.example.soccer.query;

import com.example.soccer.data.DataStore;
import com.example.soccer.data.Match;
import com.example.soccer.data.Player;
import com.example.soccer.data.TeamNames;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public final class QueryService {

    private final DataStore store;

    public QueryService(DataStore store) {
        this.store = store;
    }

    public DataStore store() { return store; }

    public List<Match> searchMatches(String teamA, String teamB, Integer season,
                                     String competition, LocalDate from, LocalDate to,
                                     String venue) {
        List<Match> out = new ArrayList<>();
        for (Match m : store.matches()) {
            if (season != null && (m.season() == null || !m.season().equals(season))) continue;
            if (competition != null && !competitionMatches(m.competition(), competition)) continue;
            if (from != null && (m.date() == null || m.date().isBefore(from))) continue;
            if (to != null && (m.date() == null || m.date().isAfter(to))) continue;
            if (teamA != null) {
                boolean home = TeamNames.matches(m.homeTeam(), teamA);
                boolean away = TeamNames.matches(m.awayTeam(), teamA);
                if (teamB != null) {
                    boolean homeB = TeamNames.matches(m.homeTeam(), teamB);
                    boolean awayB = TeamNames.matches(m.awayTeam(), teamB);
                    boolean ok = (home && awayB) || (away && homeB);
                    if (!ok) continue;
                } else {
                    if ("home".equalsIgnoreCase(venue)) {
                        if (!home) continue;
                    } else if ("away".equalsIgnoreCase(venue)) {
                        if (!away) continue;
                    } else {
                        if (!home && !away) continue;
                    }
                }
            }
            out.add(m);
        }
        out.sort(Comparator.comparing(Match::date,
                Comparator.nullsLast(Comparator.naturalOrder())));
        return out;
    }

    private boolean competitionMatches(String comp, String query) {
        if (comp == null) return false;
        String a = comp.toLowerCase();
        String b = query.toLowerCase();
        return a.contains(b) || b.contains(a);
    }

    private String pickStandingsSource(Integer season, String competition) {
        if (competition != null) {
            for (Match m : store.matches()) {
                if (competitionMatches(m.competition(), competition)) return m.competition();
            }
        }
        if (season != null && season >= 2012) return DataStore.COMP_BRASILEIRAO;
        return DataStore.COMP_BRA_HISTORIC;
    }

    public TeamRecord teamRecord(String team, Integer season, String competition, String venue) {
        TeamRecord rec = new TeamRecord(team);
        for (Match m : store.matches()) {
            if (!m.hasScore()) continue;
            if (season != null && (m.season() == null || !m.season().equals(season))) continue;
            if (competition != null && !competitionMatches(m.competition(), competition)) continue;
            boolean home = TeamNames.matches(m.homeTeam(), team);
            boolean away = TeamNames.matches(m.awayTeam(), team);
            if (!home && !away) continue;
            if ("home".equalsIgnoreCase(venue) && !home) continue;
            if ("away".equalsIgnoreCase(venue) && !away) continue;
            rec.matches++;
            int gf = home ? m.homeGoal() : m.awayGoal();
            int ga = home ? m.awayGoal() : m.homeGoal();
            rec.goalsFor += gf;
            rec.goalsAgainst += ga;
            if (gf > ga) rec.wins++;
            else if (gf < ga) rec.losses++;
            else rec.draws++;
        }
        return rec;
    }

    public HeadToHead headToHead(String teamA, String teamB, Integer season, String competition) {
        HeadToHead h = new HeadToHead(teamA, teamB);
        for (Match m : searchMatches(teamA, teamB, season, competition, null, null, null)) {
            h.matches.add(m);
            if (!m.hasScore()) continue;
            boolean aIsHome = TeamNames.matches(m.homeTeam(), teamA);
            int aGoals = aIsHome ? m.homeGoal() : m.awayGoal();
            int bGoals = aIsHome ? m.awayGoal() : m.homeGoal();
            h.goalsA += aGoals;
            h.goalsB += bGoals;
            if (aGoals > bGoals) h.winsA++;
            else if (bGoals > aGoals) h.winsB++;
            else h.draws++;
        }
        return h;
    }

    public List<Standing> standings(Integer season, String competition) {
        Map<String, TeamRecord> rows = new HashMap<>();
        String chosen = pickStandingsSource(season, competition);
        for (Match m : store.matches()) {
            if (!m.hasScore()) continue;
            if (season != null && (m.season() == null || !m.season().equals(season))) continue;
            if (!chosen.equals(m.competition())) continue;
            String home = TeamNames.canonical(m.homeTeam());
            String away = TeamNames.canonical(m.awayTeam());
            TeamRecord rh = rows.computeIfAbsent(home, TeamRecord::new);
            TeamRecord ra = rows.computeIfAbsent(away, TeamRecord::new);
            rh.matches++; ra.matches++;
            rh.goalsFor += m.homeGoal(); rh.goalsAgainst += m.awayGoal();
            ra.goalsFor += m.awayGoal(); ra.goalsAgainst += m.homeGoal();
            if (m.homeGoal() > m.awayGoal()) { rh.wins++; ra.losses++; }
            else if (m.homeGoal() < m.awayGoal()) { ra.wins++; rh.losses++; }
            else { rh.draws++; ra.draws++; }
        }
        List<Standing> out = new ArrayList<>();
        for (TeamRecord rec : rows.values()) {
            out.add(new Standing(rec.team, rec));
        }
        // Brasileirão tiebreaker order: points → wins → goal difference → goals for → team name
        out.sort(Comparator
                .comparingInt((Standing s) -> s.record.points()).reversed()
                .thenComparing((Standing s) -> s.record.wins, Comparator.reverseOrder())
                .thenComparing(s -> s.record.goalDifference(), Comparator.reverseOrder())
                .thenComparing(s -> s.record.goalsFor, Comparator.reverseOrder())
                .thenComparing(s -> s.team));
        return out;
    }

    public List<Match> biggestWins(String competition, Integer minMargin, int limit) {
        int min = minMargin == null ? 0 : minMargin;
        Comparator<Match> byMargin = Comparator.comparingInt(m -> Math.abs(m.homeGoal() - m.awayGoal()));
        Comparator<Match> byGoals = Comparator.comparingInt(Match::totalGoals);
        return store.matches().stream()
                .filter(Match::hasScore)
                .filter(m -> competition == null || competitionMatches(m.competition(), competition))
                .filter(m -> Math.abs(m.homeGoal() - m.awayGoal()) >= min)
                .sorted(byMargin.thenComparing(byGoals).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    public Map<String, Object> matchStats(Integer season, String competition) {
        long count = 0, homeWins = 0, awayWins = 0, draws = 0;
        long totalGoals = 0;
        for (Match m : store.matches()) {
            if (!m.hasScore()) continue;
            if (season != null && (m.season() == null || !m.season().equals(season))) continue;
            if (competition != null && !competitionMatches(m.competition(), competition)) continue;
            count++;
            totalGoals += m.totalGoals();
            switch (m.winnerSide()) {
                case "home" -> homeWins++;
                case "away" -> awayWins++;
                default -> draws++;
            }
        }
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("matches", count);
        stats.put("total_goals", totalGoals);
        stats.put("avg_goals_per_match", count == 0 ? 0.0 : ((double) totalGoals) / count);
        stats.put("home_wins", homeWins);
        stats.put("away_wins", awayWins);
        stats.put("draws", draws);
        stats.put("home_win_rate", count == 0 ? 0.0 : ((double) homeWins) / count);
        return stats;
    }

    public List<Player> searchPlayers(String name, String nationality, String club,
                                      String position, Integer minOverall, int limit) {
        List<Player> out = new ArrayList<>();
        for (Player p : store.players()) {
            if (name != null && (p.name() == null || !p.name().toLowerCase().contains(name.toLowerCase()))) continue;
            if (nationality != null && (p.nationality() == null
                    || !TeamNames.stripAccents(p.nationality()).equalsIgnoreCase(TeamNames.stripAccents(nationality)))) continue;
            if (club != null && (p.club() == null || !p.club().toLowerCase().contains(club.toLowerCase()))) continue;
            if (position != null && (p.position() == null || !p.position().equalsIgnoreCase(position))) continue;
            if (minOverall != null && (p.overall() == null || p.overall() < minOverall)) continue;
            out.add(p);
        }
        out.sort(Comparator.comparing(Player::overall, Comparator.nullsLast(Comparator.reverseOrder())));
        if (limit > 0 && out.size() > limit) {
            return out.subList(0, limit);
        }
        return out;
    }

    public Map<String, Long> competitionCounts() {
        Map<String, Long> counts = new LinkedHashMap<>();
        for (Match m : store.matches()) {
            counts.merge(m.competition(), 1L, Long::sum);
        }
        return counts;
    }

    public static final class HeadToHead {
        public final String teamA;
        public final String teamB;
        public int winsA;
        public int winsB;
        public int draws;
        public int goalsA;
        public int goalsB;
        public final List<Match> matches = new ArrayList<>();

        public HeadToHead(String teamA, String teamB) {
            this.teamA = teamA;
            this.teamB = teamB;
        }
    }

    public static final class Standing {
        public final String team;
        public final TeamRecord record;

        public Standing(String team, TeamRecord record) {
            this.team = team;
            this.record = record;
        }
    }
}
