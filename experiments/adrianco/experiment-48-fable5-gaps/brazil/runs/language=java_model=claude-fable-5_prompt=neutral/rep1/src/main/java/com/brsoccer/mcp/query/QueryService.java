package com.brsoccer.mcp.query;

import com.brsoccer.mcp.data.DataStore;
import com.brsoccer.mcp.data.TeamRegistry;
import com.brsoccer.mcp.model.Match;
import com.brsoccer.mcp.model.Player;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Typed query layer over the loaded datasets. */
public class QueryService {

    public record MatchFilter(String team, String opponent, String competition, Integer season,
                              LocalDate from, LocalDate to, String stage) {
        public static MatchFilter empty() {
            return new MatchFilter(null, null, null, null, null, null, null);
        }
    }

    public record HeadToHead(String team1Key, String team2Key, int team1Wins, int team2Wins,
                             int draws, int team1Goals, int team2Goals, List<Match> matches) {}

    public record TeamStats(String teamKey, int played, int wins, int draws, int losses,
                            int goalsFor, int goalsAgainst) {
        public int points() { return wins * 3 + draws; }
        public double winRate() { return played == 0 ? 0 : 100.0 * wins / played; }
    }

    public record StandingRow(String teamKey, int played, int wins, int draws, int losses,
                              int goalsFor, int goalsAgainst) {
        public int points() { return wins * 3 + draws; }
        public int goalDiff() { return goalsFor - goalsAgainst; }
    }

    public record Aggregate(int matches, int totalGoals, double avgGoals,
                            double homeWinPct, double awayWinPct, double drawPct) {}

    public record TeamRank(String teamKey, TeamStats stats, double value) {}

    private final DataStore store;
    private final Map<Integer, Integer> cupFinalRound = new HashMap<>();

    public QueryService(DataStore store) {
        this.store = store;
        Map<Integer, Map<Integer, Integer>> roundCounts = new HashMap<>(); // season -> round -> matches
        for (Match m : store.matches()) {
            if (DataStore.COPA_DO_BRASIL.equals(m.competition) && m.round != null) {
                Integer r = DataStore.parseIntStr(m.round);
                if (r != null) roundCounts.computeIfAbsent(m.season, k -> new HashMap<>()).merge(r, 1, Integer::sum);
            }
        }
        // The final is the last round of a season, but only when that round is a two-leg
        // tie; a season cut off mid-tournament (2021) ends with a full round of matches.
        roundCounts.forEach((season, byRound) -> {
            int max = byRound.keySet().stream().max(Integer::compare).orElse(0);
            if (byRound.getOrDefault(max, 0) <= 2) cupFinalRound.put(season, max);
        });
    }

    public DataStore store() {
        return store;
    }

    public List<Match> findMatches(MatchFilter f) {
        String teamKey = TeamRegistry.canonicalKey(f.team());
        String oppKey = TeamRegistry.canonicalKey(f.opponent());
        String comp = DataStore.canonicalCompetition(f.competition());
        List<Match> out = new ArrayList<>();
        for (Match m : store.matches()) {
            if (comp != null && !m.competition.equals(comp)) continue;
            if (f.season() != null && m.season != f.season()) continue;
            if (f.from() != null && m.date.isBefore(f.from())) continue;
            if (f.to() != null && m.date.isAfter(f.to())) continue;
            if (teamKey != null && !involves(m, teamKey)) continue;
            if (oppKey != null && !involves(m, oppKey)) continue;
            if (teamKey != null && oppKey != null
                && TeamRegistry.keyMatches(m.homeKey, teamKey) == TeamRegistry.keyMatches(m.homeKey, oppKey)) {
                continue; // same side matched both names (e.g. team == opponent)
            }
            if (f.stage() != null && !stageMatches(m, f.stage())) continue;
            out.add(m);
        }
        return out;
    }

    private static boolean involves(Match m, String key) {
        return TeamRegistry.keyMatches(m.homeKey, key) || TeamRegistry.keyMatches(m.awayKey, key);
    }

    private boolean stageMatches(Match m, String stageQuery) {
        String q = TeamRegistry.stripAccents(stageQuery).toLowerCase().trim();
        if (m.stage != null) {
            String s = m.stage.toLowerCase();
            // "final" must not match "semifinals"/"quarterfinals"
            if (q.equals("final") ? s.equals("final") : s.contains(q)) return true;
        }
        if (DataStore.COPA_DO_BRASIL.equals(m.competition) && q.contains("final") && m.round != null) {
            Integer r = DataStore.parseIntStr(m.round);
            Integer max = cupFinalRound.get(m.season);
            return r != null && r.equals(max);
        }
        return false;
    }

    public HeadToHead headToHead(String team1, String team2) {
        String k1 = TeamRegistry.canonicalKey(team1);
        String k2 = TeamRegistry.canonicalKey(team2);
        List<Match> ms = findMatches(new MatchFilter(team1, team2, null, null, null, null, null));
        int w1 = 0, w2 = 0, d = 0, g1 = 0, g2 = 0;
        for (Match m : ms) {
            boolean t1Home = TeamRegistry.keyMatches(m.homeKey, k1);
            int t1Goals = t1Home ? m.homeGoals : m.awayGoals;
            int t2Goals = t1Home ? m.awayGoals : m.homeGoals;
            g1 += t1Goals;
            g2 += t2Goals;
            if (t1Goals > t2Goals) w1++;
            else if (t2Goals > t1Goals) w2++;
            else d++;
        }
        return new HeadToHead(k1, k2, w1, w2, d, g1, g2, ms);
    }

    /** venue: "home", "away", or null/"all" for both. */
    public TeamStats teamStats(String team, Integer season, String competition, String venue) {
        String key = TeamRegistry.canonicalKey(team);
        List<Match> ms = findMatches(new MatchFilter(team, null, competition, season, null, null, null));
        int p = 0, w = 0, d = 0, l = 0, gf = 0, ga = 0;
        for (Match m : ms) {
            boolean home = TeamRegistry.keyMatches(m.homeKey, key);
            if ("home".equalsIgnoreCase(venue) && !home) continue;
            if ("away".equalsIgnoreCase(venue) && home) continue;
            int f = home ? m.homeGoals : m.awayGoals;
            int a = home ? m.awayGoals : m.homeGoals;
            p++;
            gf += f;
            ga += a;
            if (f > a) w++;
            else if (f < a) l++;
            else d++;
        }
        return new TeamStats(key, p, w, d, l, gf, ga);
    }

    public List<StandingRow> standings(int season, String competition) {
        String comp = DataStore.canonicalCompetition(competition);
        if (comp == null) comp = DataStore.SERIE_A;
        Map<String, int[]> table = new TreeMap<>(); // key -> p,w,d,l,gf,ga
        for (Match m : store.matches()) {
            if (m.season != season || !m.competition.equals(comp)) continue;
            if (DataStore.LIBERTADORES.equals(comp) && m.stage != null && !m.stage.contains("group")) continue;
            int[] h = table.computeIfAbsent(m.homeKey, k -> new int[6]);
            int[] a = table.computeIfAbsent(m.awayKey, k -> new int[6]);
            h[0]++; a[0]++;
            h[4] += m.homeGoals; h[5] += m.awayGoals;
            a[4] += m.awayGoals; a[5] += m.homeGoals;
            if (m.homeGoals > m.awayGoals) { h[1]++; a[3]++; }
            else if (m.homeGoals < m.awayGoals) { a[1]++; h[3]++; }
            else { h[2]++; a[2]++; }
        }
        List<StandingRow> rows = new ArrayList<>();
        table.forEach((k, v) -> rows.add(new StandingRow(k, v[0], v[1], v[2], v[3], v[4], v[5])));
        rows.sort(Comparator.comparingInt(StandingRow::points).reversed()
            .thenComparing(Comparator.comparingInt(StandingRow::wins).reversed())
            .thenComparing(Comparator.comparingInt(StandingRow::goalDiff).reversed())
            .thenComparing(Comparator.comparingInt(StandingRow::goalsFor).reversed()));
        return rows;
    }

    public List<Player> searchPlayers(String name, String nationality, String club, String position,
                                      Integer minOverall, String sortBy, int limit) {
        String nameQ = name == null ? null : TeamRegistry.stripAccents(name).toLowerCase().trim();
        String natQ = nationality == null ? null : TeamRegistry.stripAccents(nationality).toLowerCase().trim();
        String clubQ = club == null ? null : TeamRegistry.stripAccents(club).toLowerCase().trim();
        String posQ = position == null ? null : position.toLowerCase().trim();
        List<Player> out = new ArrayList<>();
        for (Player p : store.players()) {
            if (nameQ != null && !TeamRegistry.stripAccents(p.name).toLowerCase().contains(nameQ)) continue;
            if (natQ != null && (p.nationality == null
                || !TeamRegistry.stripAccents(p.nationality).toLowerCase().contains(natQ))) continue;
            if (clubQ != null && (p.club == null
                || !TeamRegistry.stripAccents(p.club).toLowerCase().contains(clubQ))) continue;
            if (posQ != null && (p.position == null || !p.position.toLowerCase().equals(posQ))) continue;
            if (minOverall != null && (p.overall == null || p.overall < minOverall)) continue;
            out.add(p);
        }
        Comparator<Player> cmp = switch (sortBy == null ? "overall" : sortBy.toLowerCase()) {
            case "potential" -> Comparator.comparing(p -> p.potential == null ? -1 : -p.potential);
            case "age" -> Comparator.comparing(p -> p.age == null ? Integer.MAX_VALUE : p.age);
            case "name" -> Comparator.comparing(p -> p.name);
            default -> Comparator.comparing(p -> p.overall == null ? -1 : -p.overall);
        };
        out.sort(cmp);
        return limit > 0 && out.size() > limit ? out.subList(0, limit) : out;
    }

    public Aggregate aggregate(String competition, Integer season) {
        String comp = DataStore.canonicalCompetition(competition);
        int n = 0, goals = 0, hw = 0, aw = 0, dr = 0;
        for (Match m : store.matches()) {
            if (comp != null && !m.competition.equals(comp)) continue;
            if (season != null && m.season != season) continue;
            n++;
            goals += m.totalGoals();
            if (m.homeGoals > m.awayGoals) hw++;
            else if (m.homeGoals < m.awayGoals) aw++;
            else dr++;
        }
        return new Aggregate(n, goals,
            n == 0 ? 0 : (double) goals / n,
            n == 0 ? 0 : 100.0 * hw / n,
            n == 0 ? 0 : 100.0 * aw / n,
            n == 0 ? 0 : 100.0 * dr / n);
    }

    public List<Match> biggestWins(String competition, Integer season, int limit) {
        String comp = DataStore.canonicalCompetition(competition);
        List<Match> out = new ArrayList<>();
        for (Match m : store.matches()) {
            if (comp != null && !m.competition.equals(comp)) continue;
            if (season != null && m.season != season) continue;
            if (m.margin() > 0) out.add(m);
        }
        out.sort(Comparator.comparingInt(Match::margin).reversed()
            .thenComparing(Comparator.comparingInt(Match::totalGoals).reversed()));
        return out.size() > limit ? out.subList(0, limit) : out;
    }

    /** metric: points | wins | win_rate | goals_scored | goals_conceded. */
    public List<TeamRank> rankings(String metric, String venue, Integer season, String competition,
                                   int minMatches, int limit) {
        String comp = DataStore.canonicalCompetition(competition);
        Map<String, int[]> table = new TreeMap<>();
        for (Match m : store.matches()) {
            if (comp != null && !m.competition.equals(comp)) continue;
            if (season != null && m.season != season) continue;
            tally(table, m.homeKey, m.homeGoals, m.awayGoals, true, venue);
            tally(table, m.awayKey, m.awayGoals, m.homeGoals, false, venue);
        }
        String met = metric == null ? "win_rate" : metric.toLowerCase();
        List<TeamRank> out = new ArrayList<>();
        table.forEach((k, v) -> {
            TeamStats s = new TeamStats(k, v[0], v[1], v[2], v[3], v[4], v[5]);
            if (s.played() < minMatches) return;
            double val = switch (met) {
                case "points" -> s.points();
                case "wins" -> s.wins();
                case "goals_scored" -> s.goalsFor();
                case "goals_conceded" -> s.goalsAgainst();
                default -> s.winRate();
            };
            out.add(new TeamRank(k, s, val));
        });
        boolean ascending = met.equals("goals_conceded");
        out.sort(ascending
            ? Comparator.comparingDouble(TeamRank::value)
            : Comparator.comparingDouble(TeamRank::value).reversed());
        return out.size() > limit ? out.subList(0, limit) : out;
    }

    private static void tally(Map<String, int[]> table, String key, int gf, int ga,
                              boolean isHome, String venue) {
        if ("home".equalsIgnoreCase(venue) && !isHome) return;
        if ("away".equalsIgnoreCase(venue) && isHome) return;
        int[] v = table.computeIfAbsent(key, k -> new int[6]);
        v[0]++;
        v[4] += gf;
        v[5] += ga;
        if (gf > ga) v[1]++;
        else if (gf < ga) v[3]++;
        else v[2]++;
    }
}
