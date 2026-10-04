package br.soccer;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/** Answers match, team, player, competition and statistical queries as formatted text. */
public final class QueryService {

    /** Match search criteria; null fields are ignored. */
    public static final class Filter {
        public String team, opponent, venue, competition, stage;
        public Integer season;
        public LocalDate from, to;

        public Filter team(String t) { team = t; return this; }
        public Filter opponent(String t) { opponent = t; return this; }
        public Filter venue(String v) { venue = v; return this; }
        public Filter competition(String c) { competition = c; return this; }
        public Filter stage(String s) { stage = s; return this; }
        public Filter season(Integer s) { season = s; return this; }
        public Filter from(LocalDate d) { from = d; return this; }
        public Filter to(LocalDate d) { to = d; return this; }
    }

    /** Win/draw/loss and goal tally. */
    public static final class Rec {
        public int played, wins, draws, losses, goalsFor, goalsAgainst;

        void add(int gf, int ga) {
            played++;
            goalsFor += gf;
            goalsAgainst += ga;
            if (gf > ga) wins++;
            else if (gf == ga) draws++;
            else losses++;
        }

        public int points() { return wins * 3 + draws; }
        public int goalDiff() { return goalsFor - goalsAgainst; }
        public double winRate() { return played == 0 ? 0 : 100.0 * wins / played; }
    }

    private static final String[][] DERBIES = {
        {"flamengo", "fluminense", "Fla-Flu"}, {"flamengo", "vasco", "Clássico dos Milhões"},
        {"flamengo", "botafogo", "Clássico da Rivalidade"}, {"fluminense", "vasco", "Clássico dos Gigantes"},
        {"fluminense", "botafogo", "Clássico Vovô"}, {"botafogo", "vasco", "Clássico da Amizade"},
        {"corinthians", "palmeiras", "Derby Paulista"}, {"corinthians", "sao paulo", "Majestoso"},
        {"palmeiras", "sao paulo", "Choque-Rei"}, {"corinthians", "santos", "Clássico Alvinegro"},
        {"palmeiras", "santos", "Clássico da Saudade"}, {"santos", "sao paulo", "San-São"},
        {"gremio", "internacional", "Gre-Nal"}, {"atletico mineiro", "cruzeiro", "Clássico Mineiro"},
        {"bahia", "vitoria", "Ba-Vi"}, {"athletico paranaense", "coritiba", "Atletiba"},
        {"sport", "nautico", "Clássico dos Clássicos"}, {"sport", "santa cruz", "Clássico das Multidões"},
        {"ceara", "fortaleza", "Clássico-Rei"}, {"goias", "vila nova", "Derby do Cerrado"},
        {"avai", "figueirense", "Clássico de Florianópolis"}, {"remo", "paysandu", "Re-Pa"},
    };

    private static final Map<String, Set<String>> POSITION_GROUPS = Map.of(
            "forward", Set.of("ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"),
            "midfielder", Set.of("CM", "LCM", "RCM", "CAM", "LAM", "RAM", "CDM", "LDM", "RDM", "LM", "RM"),
            "defender", Set.of("CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"),
            "goalkeeper", Set.of("GK"));

    private final DataStore ds;
    private final Set<String> domesticKeys = new TreeSet<>();
    private final Set<String> brazilianClubs = new TreeSet<>();

    public QueryService(DataStore ds) {
        this.ds = ds;
        for (Match m : ds.matches()) {
            if (!m.competition.equals(DataStore.LIBERTADORES)) {
                domesticKeys.add(m.homeKey);
                domesticKeys.add(m.awayKey);
            }
        }
        // A FIFA club is treated as Brazilian when its name matches a domestic team and most of its
        // squad is Brazilian (this keeps e.g. Portugal's Boavista FC apart from Boavista-RJ).
        Map<String, int[]> squads = new HashMap<>();
        for (Player p : ds.players()) {
            if (p.club().isEmpty()) continue;
            int[] c = squads.computeIfAbsent(p.club(), k -> new int[2]);
            c[0]++;
            if (p.nationality().equals("Brazil")) c[1]++;
        }
        squads.forEach((club, c) -> {
            if (c[1] * 2 >= c[0] && domesticKeys.contains(TeamNames.canonical(club))) brazilianClubs.add(club);
        });
    }

    // ---------------------------------------------------------------- resolution helpers

    /** Canonical keys matching a user-supplied team name: an exact club, else partial matches. */
    public List<String> resolveTeams(String query) {
        if (query == null || query.isBlank()) throw new IllegalArgumentException("A team name is required.");
        String key = TeamNames.canonical(query);
        if (ds.teamKeys().contains(key)) return List.of(key);
        String folded = TeamNames.fold(query);
        List<String> out = new ArrayList<>();
        if (folded.isEmpty()) return out;
        for (String k : ds.teamKeys()) {
            if (k.contains(key) || k.contains(folded)) out.add(k);
        }
        return out;
    }

    private String oneTeam(String query) {
        List<String> keys = resolveTeams(query);
        if (keys.isEmpty()) throw new IllegalArgumentException("No team found matching \"" + query + "\".");
        if (keys.size() > 1) {
            throw new IllegalArgumentException("Team \"" + query + "\" is ambiguous. Did you mean: "
                    + keys.stream().limit(10).map(TeamNames::display).collect(Collectors.joining(", ")) + "?");
        }
        return keys.get(0);
    }

    /** Maps free text ("serie a", "Brasileirao", "cup", "libertadores") to a competition name. */
    public static String resolveCompetition(String query) {
        if (query == null || query.isBlank()) return null;
        String q = TeamNames.fold(query);
        if (q.contains("libertadores")) return DataStore.LIBERTADORES;
        if (q.contains("copa") || q.contains("cup")) return DataStore.COPA_DO_BRASIL;
        if (q.contains("serie b")) return DataStore.SERIE_B;
        if (q.contains("serie c")) return DataStore.SERIE_C;
        if (q.contains("brasileir") || q.contains("serie a") || q.contains("league")
                || q.contains("campeonato")) return DataStore.SERIE_A;
        throw new IllegalArgumentException("Unknown competition \"" + query + "\". Use one of: Brasileirão "
                + "(Serie A), Serie B, Serie C, Copa do Brasil, Libertadores.");
    }

    private List<Match> filter(Filter f) {
        String comp = resolveCompetition(f.competition);
        String team = f.team == null || f.team.isBlank() ? null : oneTeam(f.team);
        String opp = f.opponent == null || f.opponent.isBlank() ? null : oneTeam(f.opponent);
        if (team == null && opp != null) {
            team = opp;
            opp = null;
        }
        String venue = f.venue == null ? "" : f.venue.toLowerCase(Locale.ROOT).trim();
        if (!venue.isEmpty() && !Set.of("home", "away", "either", "all").contains(venue)) {
            throw new IllegalArgumentException("venue must be one of: home, away, either.");
        }
        String stage = f.stage == null || f.stage.isBlank() ? null : TeamNames.fold(f.stage).replaceAll("s$", "");
        final String t = team, o = opp;
        Predicate<Match> p = m -> {
            if (comp != null && !m.competition.equals(comp)) return false;
            if (f.season != null && m.season != f.season) return false;
            if (f.from != null && m.date.isBefore(f.from)) return false;
            if (f.to != null && m.date.isAfter(f.to)) return false;
            if (t != null) {
                if (!m.involves(t)) return false;
                if (venue.equals("home") && !m.homeKey.equals(t)) return false;
                if (venue.equals("away") && !m.awayKey.equals(t)) return false;
                if (o != null && !m.involves(o)) return false;
            }
            if (stage != null) {
                String ms = m.stage != null ? m.stage : m.round;
                if (ms == null || !TeamNames.fold(ms).replaceAll("s$", "").equals(stage)) return false;
            }
            return true;
        };
        return ds.matches().stream().filter(p)
                .sorted(Comparator.comparing((Match m) -> m.date).reversed())
                .collect(Collectors.toList());
    }

    private static Rec record(List<Match> ms, String team) {
        Rec r = new Rec();
        for (Match m : ms) {
            if (m.homeKey.equals(team)) r.add(m.homeGoals, m.awayGoals);
            else if (m.awayKey.equals(team)) r.add(m.awayGoals, m.homeGoals);
        }
        return r;
    }

    private static String scope(String competition, Integer season) {
        String c = resolveCompetition(competition);
        String s = (season != null ? season + " " : "") + (c != null ? c : "all competitions");
        return s;
    }

    private static String pct(double v) {
        return String.format(Locale.ROOT, "%.1f%%", v);
    }

    private static int limit(Integer limit, int dflt) {
        return limit == null ? dflt : Math.max(1, Math.min(limit, 500));
    }

    // ---------------------------------------------------------------- match queries

    public String searchMatches(Filter f, Integer limit) {
        List<Match> ms = filter(f);
        if (ms.isEmpty()) return "No matches found for the given criteria.";
        int n = limit(limit, 20);
        StringBuilder b = new StringBuilder();
        b.append("Found ").append(ms.size()).append(" match").append(ms.size() == 1 ? "" : "es")
                .append(" (most recent first):\n");
        ms.stream().limit(n).forEach(m -> b.append("- ").append(m.describe()).append('\n'));
        if (ms.size() > n) b.append("... (").append(ms.size() - n).append(" more matches in dataset)\n");
        if (f.team != null && !f.team.isBlank() && f.opponent != null && !f.opponent.isBlank()) {
            b.append('\n').append(h2hLine(ms, oneTeam(f.team), oneTeam(f.opponent)));
        }
        return b.toString().trim();
    }

    private static String h2hLine(List<Match> ms, String a, String b) {
        Rec r = record(ms, a);
        return "Head-to-head in dataset: " + TeamNames.display(a) + " " + r.wins + " wins, "
                + TeamNames.display(b) + " " + r.losses + " wins, " + r.draws + " draws (goals "
                + r.goalsFor + "-" + r.goalsAgainst + ")";
    }

    public String headToHead(String teamA, String teamB, String competition, Integer season) {
        String a = oneTeam(teamA), b = oneTeam(teamB);
        if (a.equals(b)) throw new IllegalArgumentException("Please provide two different teams.");
        List<Match> ms = filter(new Filter().team(teamA).opponent(teamB).competition(competition).season(season));
        String title = TeamNames.display(a) + " vs " + TeamNames.display(b) + " (" + scope(competition, season) + ")";
        if (ms.isEmpty()) return title + ": no matches in dataset.";
        StringBuilder sb = new StringBuilder(title).append(":\n");
        sb.append("- Matches: ").append(ms.size()).append('\n');
        sb.append("- ").append(h2hLine(ms, a, b)).append('\n');
        Rec home = record(ms.stream().filter(m -> m.homeKey.equals(a)).toList(), a);
        Rec away = record(ms.stream().filter(m -> m.awayKey.equals(a)).toList(), a);
        sb.append("- ").append(TeamNames.display(a)).append(" at home: ").append(wdl(home)).append('\n');
        sb.append("- ").append(TeamNames.display(a)).append(" away: ").append(wdl(away)).append('\n');
        Map<String, List<Match>> byComp = ms.stream().collect(
                Collectors.groupingBy(m -> m.competition, TreeMap::new, Collectors.toList()));
        if (byComp.size() > 1) {
            byComp.forEach((c, l) -> sb.append("- ").append(c).append(": ").append(wdl(record(l, a))).append('\n'));
        }
        sb.append("Most recent meetings:\n");
        ms.stream().limit(5).forEach(m -> sb.append("- ").append(m.describe()).append('\n'));
        return sb.toString().trim();
    }

    private static String wdl(Rec r) {
        return r.wins + "W " + r.draws + "D " + r.losses + "L in " + r.played + " (goals " + r.goalsFor + "-"
                + r.goalsAgainst + ")";
    }

    // ---------------------------------------------------------------- team queries

    public Rec teamRecord(String team, Integer season, String competition, String venue) {
        String key = oneTeam(team);
        return record(filter(new Filter().team(team).season(season).competition(competition).venue(venue)), key);
    }

    public String teamStats(String team, Integer season, String competition, String venue) {
        String key = oneTeam(team);
        List<Match> ms = filter(new Filter().team(team).season(season).competition(competition).venue(venue));
        String v = venue == null || venue.isBlank() || venue.equalsIgnoreCase("either")
                || venue.equalsIgnoreCase("all") ? "" : venue.toLowerCase(Locale.ROOT) + " ";
        String title = TeamNames.display(key) + " " + v + "record (" + scope(competition, season) + ")";
        if (ms.isEmpty()) return title + ": no matches in dataset.";
        Rec r = record(ms, key);
        StringBuilder b = new StringBuilder(title).append(":\n");
        b.append("- Matches: ").append(r.played).append('\n');
        b.append("- Wins: ").append(r.wins).append(", Draws: ").append(r.draws).append(", Losses: ")
                .append(r.losses).append('\n');
        b.append("- Goals For: ").append(r.goalsFor).append(", Goals Against: ").append(r.goalsAgainst)
                .append(" (difference ").append(String.format("%+d", r.goalDiff())).append(")\n");
        b.append("- Win rate: ").append(pct(r.winRate())).append('\n');
        b.append("- Points (3 per win): ").append(r.points()).append('\n');
        if (v.isEmpty()) {
            Rec h = record(ms.stream().filter(m -> m.homeKey.equals(key)).toList(), key);
            Rec a = record(ms.stream().filter(m -> m.awayKey.equals(key)).toList(), key);
            b.append("- Home: ").append(wdl(h)).append('\n');
            b.append("- Away: ").append(wdl(a)).append('\n');
        }
        Map<String, List<Match>> byComp = ms.stream().collect(
                Collectors.groupingBy(m -> m.competition, TreeMap::new, Collectors.toList()));
        if (byComp.size() > 1) {
            b.append("By competition:\n");
            byComp.forEach((c, l) -> b.append("- ").append(c).append(": ").append(wdl(record(l, key)))
                    .append(", seasons ").append(seasonRange(l)).append('\n'));
        }
        return b.toString().trim();
    }

    private static String seasonRange(List<Match> l) {
        int min = l.stream().mapToInt(m -> m.season).min().orElse(0);
        int max = l.stream().mapToInt(m -> m.season).max().orElse(0);
        return min == max ? String.valueOf(min) : min + "-" + max;
    }

    private Map<String, Rec> table(List<Match> ms, String venue) {
        Map<String, Rec> t = new HashMap<>();
        boolean home = !"away".equalsIgnoreCase(venue), away = !"home".equalsIgnoreCase(venue);
        for (Match m : ms) {
            if (home) t.computeIfAbsent(m.homeKey, k -> new Rec()).add(m.homeGoals, m.awayGoals);
            if (away) t.computeIfAbsent(m.awayKey, k -> new Rec()).add(m.awayGoals, m.homeGoals);
        }
        return t;
    }

    private static final Comparator<Map.Entry<String, Rec>> STANDING_ORDER =
            Comparator.comparingInt((Map.Entry<String, Rec> e) -> -e.getValue().points())
                    .thenComparingInt(e -> -e.getValue().wins)
                    .thenComparingInt(e -> -e.getValue().goalDiff())
                    .thenComparingInt(e -> -e.getValue().goalsFor)
                    .thenComparing(Map.Entry::getKey);

    /** League table as ordered (team key -> record); empty when there is no data. */
    public LinkedHashMap<String, Rec> standingsTable(int season, String competition) {
        String comp = competition == null || competition.isBlank() ? DataStore.SERIE_A : competition;
        List<Match> ms = filter(new Filter().season(season).competition(comp));
        Map<String, Rec> all = table(ms, null);
        // The extended dataset mislabels a few stray fixtures as league games; a "team" with only
        // a handful of matches next to a full season is not a participant.
        int max = all.values().stream().mapToInt(r -> r.played).max().orElse(0);
        Predicate<String> member = k -> all.get(k).played * 4 >= max;
        Map<String, Rec> t = table(ms.stream().filter(m -> member.test(m.homeKey) && member.test(m.awayKey)).toList(), null);
        LinkedHashMap<String, Rec> out = new LinkedHashMap<>();
        t.entrySet().stream().sorted(STANDING_ORDER).forEach(e -> out.put(e.getKey(), e.getValue()));
        return out;
    }

    public String standings(Integer season, String competition) {
        if (season == null) throw new IllegalArgumentException("A season (year) is required.");
        String comp = resolveCompetition(competition);
        if (comp == null) comp = DataStore.SERIE_A;
        if (comp.equals(DataStore.COPA_DO_BRASIL) || comp.equals(DataStore.LIBERTADORES)) {
            return comp + " is a knockout competition; use the knockout_stages tool for season " + season
                    + ". Aggregate table of all its matches:\n" + renderTable(standingsTable(season, comp), 0, false);
        }
        LinkedHashMap<String, Rec> t = standingsTable(season, comp);
        if (t.isEmpty()) return "No " + comp + " matches in dataset for season " + season + ".";
        int teams = t.size();
        int expected = 2 * (teams - 1);
        boolean complete = comp.equals(DataStore.SERIE_A)
                && t.values().stream().allMatch(r -> r.played == expected);
        int relegated = !complete ? 0 : season == 2003 ? 2 : 4;
        StringBuilder b = new StringBuilder();
        b.append(season).append(' ').append(comp).append(complete ? " Final Standings" : " Standings")
                .append(" (calculated from matches):\n");
        b.append(renderTable(t, relegated, complete));
        if (!complete) {
            b.append("\nNote: the dataset does not contain every match of this season, so the table is partial.");
        } else {
            b.append("\nNote: calculated with 3 points per win, ordered by points, wins, goal difference, goals"
                    + " scored. Official tables may differ where points were deducted by sporting tribunals.");
        }
        return b.toString();
    }

    private static String renderTable(LinkedHashMap<String, Rec> t, int relegated, boolean champion) {
        StringBuilder b = new StringBuilder();
        int i = 0;
        for (Map.Entry<String, Rec> e : t.entrySet()) {
            i++;
            Rec r = e.getValue();
            b.append(i).append(". ").append(TeamNames.display(e.getKey())).append(" - ").append(r.points())
                    .append(" pts (").append(r.wins).append("W, ").append(r.draws).append("D, ")
                    .append(r.losses).append("L, GF ").append(r.goalsFor).append(", GA ")
                    .append(r.goalsAgainst).append(", P ").append(r.played).append(')');
            if (champion && i == 1) b.append(" - Champion");
            if (relegated > 0 && i > t.size() - relegated) b.append(" - Relegated");
            b.append('\n');
        }
        return b.toString().trim();
    }

    public String teamRankings(String metric, String venue, String competition, Integer season,
                               Integer minMatches, Integer limit) {
        String mt = metric == null || metric.isBlank() ? "win_rate" : metric.toLowerCase(Locale.ROOT).trim();
        Map<String, Comparator<Rec>> metrics = new LinkedHashMap<>();
        metrics.put("win_rate", Comparator.comparingDouble(Rec::winRate).reversed());
        metrics.put("points", Comparator.comparingInt(Rec::points).reversed());
        metrics.put("points_per_match", Comparator.comparingDouble((Rec r) -> (double) r.points() / r.played).reversed());
        metrics.put("wins", Comparator.comparingInt((Rec r) -> r.wins).reversed());
        metrics.put("goals_for", Comparator.comparingInt((Rec r) -> r.goalsFor).reversed());
        metrics.put("goals_against", Comparator.comparingInt((Rec r) -> r.goalsAgainst));
        metrics.put("goal_difference", Comparator.comparingInt(Rec::goalDiff).reversed());
        Comparator<Rec> cmp = metrics.get(mt);
        if (cmp == null) throw new IllegalArgumentException("metric must be one of: " + metrics.keySet());
        String v = venue == null || venue.isBlank() ? "all" : venue.toLowerCase(Locale.ROOT).trim();
        if (!Set.of("home", "away", "all", "either").contains(v)) {
            throw new IllegalArgumentException("venue must be one of: home, away, all.");
        }
        List<Match> ms = filter(new Filter().competition(competition).season(season));
        int min = minMatches != null ? Math.max(1, minMatches) : season != null ? 5 : 20;
        List<Map.Entry<String, Rec>> rows = table(ms, v).entrySet().stream()
                .filter(e -> e.getValue().played >= min)
                .sorted(Map.Entry.<String, Rec>comparingByValue(cmp).thenComparing(STANDING_ORDER))
                .limit(limit(limit, 10)).toList();
        if (rows.isEmpty()) return "No teams with at least " + min + " matches for the given criteria.";
        StringBuilder b = new StringBuilder();
        b.append("Team ranking by ").append(mt).append(" - ").append(v.equals("either") ? "all" : v)
                .append(" matches, ").append(scope(competition, season)).append(" (min ").append(min)
                .append(" matches):\n");
        int i = 0;
        for (Map.Entry<String, Rec> e : rows) {
            Rec r = e.getValue();
            b.append(++i).append(". ").append(TeamNames.display(e.getKey())).append(" - ")
                    .append(r.wins).append("W ").append(r.draws).append("D ").append(r.losses).append("L in ")
                    .append(r.played).append(", win rate ").append(pct(r.winRate())).append(", goals ")
                    .append(r.goalsFor).append('-').append(r.goalsAgainst).append(", ").append(r.points())
                    .append(" pts\n");
        }
        return b.toString().trim();
    }

    // ---------------------------------------------------------------- statistics

    public String biggestWins(String competition, Integer season, String team, Integer limit) {
        List<Match> ms = new ArrayList<>(filter(new Filter().competition(competition).season(season).team(team)));
        if (ms.isEmpty()) return "No matches found for the given criteria.";
        ms.sort(Comparator.comparingInt(Match::margin).reversed()
                .thenComparing(m -> -(m.homeGoals + m.awayGoals))
                .thenComparing((Match m) -> m.date, Comparator.reverseOrder()));
        StringBuilder b = new StringBuilder("Biggest victories (" + scope(competition, season) + "):\n");
        int i = 0;
        for (Match m : ms.subList(0, Math.min(ms.size(), limit(limit, 10)))) {
            b.append(++i).append(". ").append(m.describe()).append('\n');
        }
        return b.toString().trim();
    }

    /** Aggregate figures for a set of matches: [matches, goals, home wins, draws, away wins]. */
    public int[] aggregate(String competition, Integer season) {
        int[] a = new int[5];
        for (Match m : filter(new Filter().competition(competition).season(season))) {
            a[0]++;
            a[1] += m.homeGoals + m.awayGoals;
            a[m.homeGoals > m.awayGoals ? 2 : m.homeGoals == m.awayGoals ? 3 : 4]++;
        }
        return a;
    }

    private String aggregateLines(String competition, Integer season) {
        List<Match> ms = filter(new Filter().competition(competition).season(season));
        int[] a = aggregate(competition, season);
        StringBuilder b = new StringBuilder();
        b.append("- Matches: ").append(a[0]).append('\n');
        b.append("- Total goals: ").append(a[1]).append('\n');
        b.append(String.format(Locale.ROOT, "- Average goals per match: %.2f%n", (double) a[1] / a[0]));
        b.append("- Home win rate: ").append(pct(100.0 * a[2] / a[0])).append('\n');
        b.append("- Draw rate: ").append(pct(100.0 * a[3] / a[0])).append('\n');
        b.append("- Away win rate: ").append(pct(100.0 * a[4] / a[0])).append('\n');
        List<Match> withCorners = ms.stream().filter(m -> m.homeCorners != null && m.awayCorners != null).toList();
        if (!withCorners.isEmpty()) {
            double c = withCorners.stream().mapToInt(m -> m.homeCorners + m.awayCorners).average().orElse(0);
            b.append(String.format(Locale.ROOT, "- Average corners per match: %.2f (%d matches with data)%n",
                    c, withCorners.size()));
        }
        List<Match> withShots = ms.stream().filter(m -> m.homeShots != null && m.awayShots != null).toList();
        if (!withShots.isEmpty()) {
            double s = withShots.stream().mapToInt(m -> m.homeShots + m.awayShots).average().orElse(0);
            b.append(String.format(Locale.ROOT, "- Average shots per match: %.2f (%d matches with data)%n",
                    s, withShots.size()));
        }
        return b.toString();
    }

    public String matchStatistics(String competition, Integer season) {
        if (aggregate(competition, season)[0] == 0) return "No matches found for the given criteria.";
        StringBuilder b = new StringBuilder("Match statistics (" + scope(competition, season) + "):\n");
        b.append(aggregateLines(competition, season));
        if (season == null) {
            Map<Integer, int[]> bySeason = new TreeMap<>();
            for (Match m : filter(new Filter().competition(competition))) {
                int[] x = bySeason.computeIfAbsent(m.season, k -> new int[2]);
                x[0]++;
                x[1] += m.homeGoals + m.awayGoals;
            }
            b.append("Goals per match by season:\n");
            bySeason.forEach((s, x) -> b.append(String.format(Locale.ROOT, "- %d: %.2f (%d matches)%n",
                    s, (double) x[1] / x[0], x[0])));
        }
        return b.toString().trim();
    }

    public String compareSeasons(Integer seasonA, Integer seasonB, String competition) {
        if (seasonA == null || seasonB == null) throw new IllegalArgumentException("Two seasons are required.");
        String comp = resolveCompetition(competition);
        if (comp == null) comp = DataStore.SERIE_A;
        StringBuilder b = new StringBuilder("Season comparison - " + comp + ":\n");
        for (int s : new int[] {seasonA, seasonB}) {
            b.append('\n').append(s).append(":\n");
            if (aggregate(comp, s)[0] == 0) {
                b.append("- No matches in dataset\n");
                continue;
            }
            b.append(aggregateLines(comp, s));
            LinkedHashMap<String, Rec> t = standingsTable(s, comp);
            Map.Entry<String, Rec> top = t.entrySet().iterator().next();
            b.append("- Top of table: ").append(TeamNames.display(top.getKey())).append(" (")
                    .append(top.getValue().points()).append(" pts)\n");
            Map.Entry<String, Rec> best = t.entrySet().stream()
                    .max(Comparator.comparingInt(e -> e.getValue().goalsFor)).get();
            b.append("- Most goals scored: ").append(TeamNames.display(best.getKey())).append(" (")
                    .append(best.getValue().goalsFor).append(")\n");
        }
        return b.toString().trim();
    }

    public String derbies(Integer season, String competition, String team, Integer limit) {
        Map<String, String> names = new HashMap<>();
        for (String[] d : DERBIES) {
            names.put(d[0] + "|" + d[1], d[2]);
            names.put(d[1] + "|" + d[0], d[2]);
        }
        List<Match> ms = filter(new Filter().season(season).competition(competition).team(team)).stream()
                .filter(m -> names.containsKey(m.homeKey + "|" + m.awayKey)).toList();
        if (ms.isEmpty()) return "No derby matches found for the given criteria.";
        int n = limit(limit, 50);
        StringBuilder b = new StringBuilder("Derby matches (" + scope(competition, season) + "): "
                + ms.size() + " found\n");
        ms.stream().limit(n).forEach(m -> b.append("- ").append(names.get(m.homeKey + "|" + m.awayKey))
                .append(" - ").append(m.describe()).append('\n'));
        if (ms.size() > n) b.append("... (").append(ms.size() - n).append(" more matches in dataset)\n");
        return b.toString().trim();
    }

    // ---------------------------------------------------------------- competition queries

    public String knockoutStages(String competition, Integer season) {
        if (season == null) throw new IllegalArgumentException("A season (year) is required.");
        String comp = resolveCompetition(competition);
        if (comp == null) comp = DataStore.LIBERTADORES;
        List<Match> ms = new ArrayList<>(filter(new Filter().competition(comp).season(season)));
        if (ms.isEmpty()) return "No " + comp + " matches in dataset for season " + season + ".";
        ms.sort(Comparator.comparing(m -> m.date));
        Map<String, List<Match>> stages = new LinkedHashMap<>();
        for (Match m : ms) {
            String s = m.stage != null ? m.stage : m.round != null ? "round " + m.round : "stage not recorded";
            if (s.equals("group stage")) continue;
            stages.computeIfAbsent(s, k -> new ArrayList<>()).add(m);
        }
        StringBuilder b = new StringBuilder(season + " " + comp + " knockout rounds:\n");
        stages.forEach((s, l) -> {
            b.append('\n').append(Character.toUpperCase(s.charAt(0))).append(s.substring(1)).append(":\n");
            // Pair up the two legs of each tie and report the aggregate score.
            Map<String, List<Match>> ties = new LinkedHashMap<>();
            for (Match m : l) {
                String k = m.homeKey.compareTo(m.awayKey) < 0 ? m.homeKey + "|" + m.awayKey : m.awayKey + "|" + m.homeKey;
                ties.computeIfAbsent(k, x -> new ArrayList<>()).add(m);
            }
            ties.forEach((k, legs) -> {
                for (Match m : legs) {
                    b.append("- ").append(m.date).append(": ").append(m.home()).append(' ').append(m.homeGoals)
                            .append('-').append(m.awayGoals).append(' ').append(m.away()).append('\n');
                }
                if (legs.size() == 2) {
                    String x = legs.get(0).homeKey, y = legs.get(0).awayKey;
                    Rec r = record(legs, x);
                    b.append("  Aggregate: ").append(TeamNames.display(x)).append(' ').append(r.goalsFor)
                            .append('-').append(r.goalsAgainst).append(' ').append(TeamNames.display(y)).append('\n');
                }
            });
        });
        int groups = (int) ms.stream().filter(m -> "group stage".equals(m.stage)).count();
        if (groups > 0) b.append("\n(").append(groups).append(" group stage matches omitted)");
        return b.toString().trim();
    }

    // ---------------------------------------------------------------- player queries

    public List<Player> findPlayers(String name, String nationality, String club, String position,
                                    Integer minOverall) {
        String n = TeamNames.fold(name), nat = TeamNames.fold(nationality), c = TeamNames.fold(club);
        if (nat.equals("brazilian") || nat.equals("brasil") || nat.equals("brasileiro")) nat = "brazil";
        String clubKey = c.isEmpty() ? "" : TeamNames.canonical(club);
        Set<String> positions = null;
        if (position != null && !position.isBlank()) {
            String p = position.trim().toLowerCase(Locale.ROOT).replaceAll("s$", "");
            if (p.equals("striker") || p.equals("attacker")) p = "forward";
            if (p.equals("keeper") || p.equals("goalie")) p = "goalkeeper";
            positions = POSITION_GROUPS.getOrDefault(p, Set.of(position.trim().toUpperCase(Locale.ROOT)));
        }
        List<Player> out = new ArrayList<>();
        for (Player p : ds.players()) {
            if (!n.isEmpty() && !TeamNames.fold(p.name()).contains(n)) continue;
            if (!nat.isEmpty() && !TeamNames.fold(p.nationality()).equals(nat)) continue;
            if (!c.isEmpty() && !(TeamNames.fold(p.club()).contains(c)
                    || !p.club().isEmpty() && TeamNames.canonical(p.club()).equals(clubKey))) continue;
            if (positions != null && !positions.contains(p.position())) continue;
            if (minOverall != null && p.overall() < minOverall) continue;
            out.add(p);
        }
        out.sort(Comparator.comparingInt(Player::overall).reversed().thenComparing(Player::name));
        return out;
    }

    public String searchPlayers(String name, String nationality, String club, String position,
                                Integer minOverall, Integer limit) {
        List<Player> ps = findPlayers(name, nationality, club, position, minOverall);
        if (ps.isEmpty()) {
            return "No players found for the given criteria. Note: the FIFA dataset only includes licensed clubs;"
                    + " use players_by_club to see which Brazilian clubs are covered.";
        }
        int n = limit(limit, 20);
        StringBuilder b = new StringBuilder("Found " + ps.size() + " player" + (ps.size() == 1 ? "" : "s")
                + " (highest rated first):\n");
        int i = 0;
        for (Player p : ps.subList(0, Math.min(n, ps.size()))) {
            b.append(++i).append(". ").append(p.summary()).append(", Nationality: ").append(p.nationality())
                    .append(", Age: ").append(p.age()).append('\n');
        }
        if (ps.size() > n) b.append("... (").append(ps.size() - n).append(" more players in dataset)\n");
        return b.toString().trim();
    }

    public String playerDetails(String name) {
        if (name == null || name.isBlank()) throw new IllegalArgumentException("A player name is required.");
        List<Player> ps = findPlayers(name, null, null, null, null);
        if (ps.isEmpty()) return "No player found matching \"" + name + "\".";
        String folded = TeamNames.fold(name);
        Player p = ps.stream().filter(x -> TeamNames.fold(x.name()).equals(folded)).findFirst().orElse(ps.get(0));
        StringBuilder b = new StringBuilder();
        b.append(p.name()).append(" (FIFA ID ").append(p.id()).append("):\n");
        b.append("- Age: ").append(p.age()).append(", Nationality: ").append(p.nationality()).append('\n');
        b.append("- Club: ").append(p.club().isEmpty() ? "Free agent" : p.club()).append(", Position: ")
                .append(p.position()).append(", Jersey: ").append(p.jersey()).append('\n');
        b.append("- Overall: ").append(p.overall()).append(", Potential: ").append(p.potential()).append('\n');
        b.append("- Height: ").append(p.height()).append(", Weight: ").append(p.weight())
                .append(", Preferred foot: ").append(p.foot()).append('\n');
        b.append("- Value: ").append(p.value()).append(", Wage: ").append(p.wage()).append('\n');
        b.append("- Skills: ").append(p.skills().entrySet().stream()
                .map(e -> e.getKey() + " " + e.getValue()).collect(Collectors.joining(", "))).append('\n');
        if (ps.size() > 1) {
            b.append("Other matches: ").append(ps.stream().filter(x -> x != p).limit(5)
                    .map(x -> x.name() + " (" + x.club() + ", " + x.overall() + ")")
                    .collect(Collectors.joining("; "))).append('\n');
        }
        return b.toString().trim();
    }

    public String playersByClub(String nationality, Boolean brazilianClubsOnly, Integer limit) {
        String nat = nationality == null || nationality.isBlank() ? "Brazil" : nationality;
        boolean only = brazilianClubsOnly == null || brazilianClubsOnly;
        Map<String, List<Player>> byClub = findPlayers(null, nat, null, null, null).stream()
                .filter(p -> !p.club().isEmpty() && (!only || brazilianClubs.contains(p.club())))
                .collect(Collectors.groupingBy(Player::club));
        if (byClub.isEmpty()) return "No players found for the given criteria.";
        StringBuilder b = new StringBuilder(nat + " players" + (only ? " at Brazilian clubs" : " by club") + ":\n");
        byClub.entrySet().stream()
                .sorted(Comparator.comparingInt((Map.Entry<String, List<Player>> e) -> -e.getValue().size())
                        .thenComparing(Map.Entry::getKey))
                .limit(limit(limit, 30))
                .forEach(e -> b.append(String.format(Locale.ROOT, "- %s: %d players (avg rating: %.1f, best: %s %d)%n",
                        e.getKey(), e.getValue().size(),
                        e.getValue().stream().mapToInt(Player::overall).average().orElse(0),
                        e.getValue().get(0).name(), e.getValue().get(0).overall())));
        return b.toString().trim();
    }

    /** Cross-file view of a club: its match record plus its squad in the FIFA data. */
    public String clubProfile(String team) {
        String key = oneTeam(team);
        StringBuilder b = new StringBuilder(teamStats(team, null, null, null));
        List<Player> squad = ds.players().stream()
                .filter(p -> brazilianClubs.contains(p.club()) && TeamNames.canonical(p.club()).equals(key))
                .sorted(Comparator.comparingInt(Player::overall).reversed()).toList();
        b.append("\n\nFIFA squad for ").append(TeamNames.display(key)).append(":\n");
        if (squad.isEmpty()) {
            b.append("- No players for this club in the FIFA dataset (the club is not licensed in it).");
        } else {
            b.append(String.format(Locale.ROOT, "- %d players, average overall %.1f%n", squad.size(),
                    squad.stream().mapToInt(Player::overall).average().orElse(0)));
            squad.stream().limit(10).forEach(p -> b.append("- ").append(p.summary()).append('\n'));
        }
        return b.toString().trim();
    }

    // ---------------------------------------------------------------- metadata

    public String datasetInfo() {
        StringBuilder b = new StringBuilder("Loaded data:\n");
        ds.fileStats().forEach((f, c) -> b.append("- ").append(f).append(": ").append(c[0])
                .append(" rows, ").append(c[1]).append(" usable\n"));
        b.append("Unique matches after merging duplicate fixtures across files: ").append(ds.matches().size())
                .append('\n');
        Map<String, List<Match>> byComp = ds.matches().stream().collect(
                Collectors.groupingBy(m -> m.competition, TreeMap::new, Collectors.toList()));
        byComp.forEach((c, l) -> b.append("- ").append(c).append(": ").append(l.size()).append(" matches, seasons ")
                .append(seasonRange(l)).append('\n'));
        b.append("Teams: ").append(ds.teamKeys().size()).append(", Players: ").append(ds.players().size());
        return b.toString();
    }
}
