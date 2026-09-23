package soccer;

import java.time.LocalDate;
import java.util.*;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/** Query engine behind the MCP tools. All methods return human-readable text. */
public final class SoccerService {
    private final DataStore data;

    /** Traditional rivalries (canonical team keys). */
    static final List<String[]> DERBIES = List.of(
            new String[]{"flamengo", "fluminense", "Fla-Flu"},
            new String[]{"flamengo", "vasco", "Clássico dos Milhões"},
            new String[]{"flamengo", "botafogo", "Clássico da Rivalidade"},
            new String[]{"fluminense", "vasco", "Clássico dos Gigantes"},
            new String[]{"botafogo", "vasco", "Clássico da Amizade"},
            new String[]{"botafogo", "fluminense", "Clássico Vovô"},
            new String[]{"corinthians", "palmeiras", "Derby Paulista"},
            new String[]{"corinthians", "sao paulo", "Majestoso"},
            new String[]{"palmeiras", "sao paulo", "Choque-Rei"},
            new String[]{"santos", "corinthians", "Clássico Alvinegro"},
            new String[]{"santos", "palmeiras", "Clássico da Saudade"},
            new String[]{"santos", "sao paulo", "San-São"},
            new String[]{"gremio", "internacional", "Grenal"},
            new String[]{"atletico-mg", "cruzeiro", "Clássico Mineiro"},
            new String[]{"bahia", "vitoria", "Ba-Vi"},
            new String[]{"atletico-pr", "coritiba", "Atletiba"},
            new String[]{"sport", "santa cruz", "Clássico das Multidões"},
            new String[]{"ceara", "fortaleza", "Clássico-Rei"});

    public SoccerService(DataStore data) { this.data = data; }

    public DataStore data() { return data; }

    // ================= filters =================
    public static String normalizeCompetition(String c) {
        if (c == null || c.isBlank()) return null;
        String k = Teams.stripAccents(c).toLowerCase();
        if (k.contains("libert")) return DataStore.LIBERTADORES;
        if (k.contains("copa") || k.contains("cup")) return DataStore.COPA_DO_BRASIL;
        if (k.contains("serie b")) return "Serie B";
        if (k.contains("serie c")) return "Serie C";
        if (k.contains("brasileir") || k.contains("serie a") || k.contains("league")) return DataStore.BRASILEIRAO;
        return c;
    }

    public List<Match> findMatches(String team, String opponent, String competition, Integer season,
                                   LocalDate from, LocalDate to, String venue) {
        String comp = normalizeCompetition(competition);
        Predicate<Match> p = m -> true;
        if (comp != null) p = p.and(m -> m.competition().equalsIgnoreCase(comp));
        if (season != null) p = p.and(m -> m.season() == season);
        if (from != null) p = p.and(m -> m.date() != null && !m.date().isBefore(from));
        if (to != null) p = p.and(m -> m.date() != null && !m.date().isAfter(to));
        if (team != null && !team.isBlank()) {
            String v = venue == null ? "all" : venue.toLowerCase();
            if (v.equals("home")) p = p.and(m -> Teams.matches(m.home(), team));
            else if (v.equals("away")) p = p.and(m -> Teams.matches(m.away(), team));
            else p = p.and(m -> m.involves(team));
        }
        if (opponent != null && !opponent.isBlank()) {
            p = p.and(m -> (team == null || team.isBlank()) ? m.involves(opponent)
                    : (Teams.matches(m.home(), team) && Teams.matches(m.away(), opponent))
                      || (Teams.matches(m.away(), team) && Teams.matches(m.home(), opponent)));
        }
        return data.matches().stream().filter(p).collect(Collectors.toList());
    }

    // ================= match queries =================
    public String searchMatches(String team, String opponent, String competition, Integer season,
                                String from, String to, String venue, Integer limit) {
        List<Match> ms = new ArrayList<>(findMatches(team, opponent, competition, season,
                DataStore.date(from), DataStore.date(to), venue));
        if (ms.isEmpty()) return "No matches found for the given criteria.";
        Collections.reverse(ms); // most recent first
        int lim = limit == null ? 20 : limit;
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(ms.size()).append(" matches");
        if (team != null && opponent != null && !team.isBlank() && !opponent.isBlank()) {
            String derby = derbyName(Teams.key(team), Teams.key(opponent));
            sb.append(" for ").append(team).append(" vs ").append(opponent);
            if (derby != null) sb.append(" (").append(derby).append(")");
        } else if (team != null && !team.isBlank()) sb.append(" for ").append(team);
        sb.append(":\n");
        ms.stream().limit(lim).forEach(m -> sb.append("- ").append(m.format()).append('\n'));
        if (ms.size() > lim) sb.append("- ... (").append(ms.size() - lim).append(" more matches in dataset)\n");
        if (team != null && opponent != null && !team.isBlank() && !opponent.isBlank())
            sb.append('\n').append(h2hLine(ms, team, opponent));
        return sb.toString().trim();
    }

    public String lastMatch(String team, String opponent) {
        List<Match> ms = findMatches(team, opponent, null, null, null, null, null);
        if (ms.isEmpty()) return "No matches found between " + team + " and " + opponent + ".";
        Match m = ms.get(ms.size() - 1);
        return "Most recent match between " + team + " and " + opponent + ":\n- " + m.format()
                + "\nScore: " + Teams.display(m.home()) + " " + m.homeGoals() + ", " + Teams.display(m.away()) + " " + m.awayGoals();
    }

    public String headToHead(String a, String b, String competition) {
        List<Match> ms = findMatches(a, b, competition, null, null, null, null);
        if (ms.isEmpty()) return "No head-to-head matches found between " + a + " and " + b + ".";
        int ga = 0, gb = 0;
        for (Match m : ms) {
            boolean aHome = Teams.matches(m.home(), a);
            ga += aHome ? m.homeGoals() : m.awayGoals();
            gb += aHome ? m.awayGoals() : m.homeGoals();
        }
        StringBuilder sb = new StringBuilder();
        String derby = derbyName(Teams.key(a), Teams.key(b));
        sb.append(a).append(" vs ").append(b).append(derby != null ? " (" + derby + ")" : "").append(" head-to-head:\n");
        sb.append("- Matches: ").append(ms.size()).append('\n');
        sb.append("- ").append(h2hLine(ms, a, b)).append('\n');
        sb.append("- Goals: ").append(a).append(' ').append(ga).append(", ").append(b).append(' ').append(gb).append('\n');
        Map<String, Long> byComp = ms.stream().collect(Collectors.groupingBy(Match::competition, TreeMap::new, Collectors.counting()));
        sb.append("- By competition: ").append(byComp).append('\n');
        sb.append("Recent meetings:\n");
        for (int i = ms.size() - 1; i >= Math.max(0, ms.size() - 5); i--) sb.append("- ").append(ms.get(i).format()).append('\n');
        return sb.toString().trim();
    }

    private String h2hLine(List<Match> ms, String a, String b) {
        int wa = 0, wb = 0, d = 0;
        for (Match m : ms) {
            int diff = m.homeGoals() - m.awayGoals();
            if (diff == 0) { d++; continue; }
            boolean aHome = Teams.matches(m.home(), a);
            if ((diff > 0) == aHome) wa++; else wb++;
        }
        return String.format("Head-to-head in dataset: %s %d wins, %s %d wins, %d draws", a, wa, b, wb, d);
    }

    static String derbyName(String ka, String kb) {
        for (String[] d : DERBIES)
            if ((d[0].equals(ka) && d[1].equals(kb)) || (d[0].equals(kb) && d[1].equals(ka))) return d[2];
        return null;
    }

    public String derbies(Integer season, String competition) {
        List<String> lines = new ArrayList<>();
        for (Match m : findMatches(null, null, competition, season, null, null, null)) {
            String n = derbyName(m.homeKey(), m.awayKey());
            if (n != null) lines.add("- [" + n + "] " + m.format());
        }
        if (lines.isEmpty()) return "No derby matches found" + (season != null ? " in " + season : "") + ".";
        return "Derby matches" + (season != null ? " in " + season : "") + " (" + lines.size() + "):\n" + String.join("\n", lines);
    }

    public String finals(String competition) {
        String comp = normalizeCompetition(competition == null ? "Copa do Brasil" : competition);
        List<Match> ms = findMatches(null, null, comp, null, null, null, null);
        List<Match> fin;
        if (comp.equals(DataStore.LIBERTADORES)) {
            fin = ms.stream().filter(m -> "final".equalsIgnoreCase(m.round())).toList();
        } else {
            Map<Integer, Integer> maxRound = new HashMap<>();
            for (Match m : ms) { Integer r = DataStore.num(m.round()); if (r != null) maxRound.merge(m.season(), r, Math::max); }
            fin = ms.stream().filter(m -> { Integer r = DataStore.num(m.round()); return r != null && r.equals(maxRound.get(m.season())); }).toList();
            // a final is a one- or two-legged tie; drop seasons whose data stops before the final
            Map<Integer, Long> perSeason = fin.stream().collect(Collectors.groupingBy(Match::season, Collectors.counting()));
            fin = fin.stream().filter(m -> perSeason.get(m.season()) <= 2).toList();
        }
        if (fin.isEmpty()) return "No final matches found for " + comp + ".";
        return comp + " finals in dataset (" + fin.size() + " matches):\n"
                + fin.stream().map(m -> "- " + m.format()).collect(Collectors.joining("\n"));
    }

    public String bracket(String competition, int season) {
        String comp = normalizeCompetition(competition);
        List<Match> ms = findMatches(null, null, comp, season, null, null, null).stream()
                .filter(m -> !"group stage".equalsIgnoreCase(m.round())).toList();
        if (ms.isEmpty()) return "No knockout matches found for " + comp + " " + season + ".";
        Map<String, List<Match>> byRound = new LinkedHashMap<>();
        for (Match m : ms) byRound.computeIfAbsent(m.round(), k -> new ArrayList<>()).add(m);
        StringBuilder sb = new StringBuilder(comp + " " + season + " knockout bracket:\n");
        byRound.forEach((r, l) -> {
            sb.append(r).append(":\n");
            l.forEach(m -> sb.append("  - ").append(m.format()).append('\n'));
        });
        return sb.toString().trim();
    }

    // ================= team queries =================
    public static final class Record {
        public String team; public int played, wins, draws, losses, gf, ga;
        public int points() { return wins * 3 + draws; }
        public int gd() { return gf - ga; }
        public double winRate() { return played == 0 ? 0 : 100.0 * wins / played; }
        void add(int f, int a) { played++; gf += f; ga += a; if (f > a) wins++; else if (f == a) draws++; else losses++; }
    }

    public Record record(String team, Integer season, String competition, String venue) {
        Record r = new Record();
        r.team = team;
        String v = venue == null ? "all" : venue.toLowerCase();
        for (Match m : findMatches(team, null, competition, season, null, null, v)) {
            if (Teams.matches(m.home(), team)) r.add(m.homeGoals(), m.awayGoals());
            else r.add(m.awayGoals(), m.homeGoals());
        }
        return r;
    }

    public String teamStats(String team, Integer season, String competition, String venue) {
        Record r = record(team, season, competition, venue);
        if (r.played == 0) return "No matches found for " + team + ".";
        String v = venue == null || venue.equalsIgnoreCase("all") ? "overall" : venue.toLowerCase();
        String comp = normalizeCompetition(competition);
        StringBuilder sb = new StringBuilder();
        sb.append(team).append(' ').append(v).append(" record");
        List<String> ctx = new ArrayList<>();
        if (season != null) ctx.add(String.valueOf(season));
        if (comp != null) ctx.add(comp);
        if (!ctx.isEmpty()) sb.append(" (").append(String.join(" ", ctx)).append(")");
        sb.append(":\n");
        sb.append(String.format("- Matches: %d%n- Wins: %d, Draws: %d, Losses: %d%n- Goals For: %d, Goals Against: %d%n- Win rate: %.1f%%",
                r.played, r.wins, r.draws, r.losses, r.gf, r.ga, r.winRate()));
        if (comp == null) {
            Map<String, Long> byComp = findMatches(team, null, null, season, null, null, venue).stream()
                    .collect(Collectors.groupingBy(Match::competition, TreeMap::new, Collectors.counting()));
            sb.append("\n- Matches by competition: ").append(byComp);
        }
        return sb.toString();
    }

    public String teamCompetitions(String team) {
        Map<String, TreeSet<Integer>> m = new TreeMap<>();
        for (Match x : findMatches(team, null, null, null, null, null, null))
            m.computeIfAbsent(x.competition(), k -> new TreeSet<>()).add(x.season());
        if (m.isEmpty()) return "No matches found for " + team + ".";
        StringBuilder sb = new StringBuilder(team + " has played in:\n");
        m.forEach((c, s) -> sb.append("- ").append(c).append(": ").append(s.size()).append(" seasons ").append(s).append('\n'));
        return sb.toString().trim();
    }

    // ================= competition queries =================
    public List<Record> standingsTable(int season, String competition) {
        String comp = normalizeCompetition(competition == null ? DataStore.BRASILEIRAO : competition);
        Map<String, Record> table = new HashMap<>();
        for (Match m : findMatches(null, null, comp, season, null, null, null)) {
            Record h = table.computeIfAbsent(m.homeKey(), k -> newRecord(m.home()));
            Record a = table.computeIfAbsent(m.awayKey(), k -> newRecord(m.away()));
            h.add(m.homeGoals(), m.awayGoals());
            a.add(m.awayGoals(), m.homeGoals());
        }
        List<Record> list = new ArrayList<>(table.values());
        list.sort(Comparator.comparingInt(Record::points).reversed()
                .thenComparing(Comparator.comparingInt((Record r) -> r.wins).reversed())
                .thenComparing(Comparator.comparingInt(Record::gd).reversed())
                .thenComparing(Comparator.comparingInt((Record r) -> r.gf).reversed()));
        return list;
    }

    private static Record newRecord(String raw) { Record r = new Record(); r.team = Teams.display(raw); return r; }

    public String standings(int season, String competition, Integer top) {
        List<Record> t = standingsTable(season, competition);
        String comp = normalizeCompetition(competition == null ? DataStore.BRASILEIRAO : competition);
        if (t.isEmpty()) return "No " + comp + " matches found for season " + season + ".";
        StringBuilder sb = new StringBuilder(season + " " + comp + " Final Standings (calculated from matches):\n");
        int n = top == null ? t.size() : Math.min(top, t.size());
        for (int i = 0; i < n; i++) {
            Record r = t.get(i);
            sb.append(String.format("%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)%s%n", i + 1, r.team, r.points(),
                    r.wins, r.draws, r.losses, r.gf, r.ga, r.gd(), i == 0 ? " - Champion" :
                            (comp.equals(DataStore.BRASILEIRAO) && t.size() >= 16 && i >= t.size() - 4 ? " - Relegated" : "")));
        }
        return sb.toString().trim();
    }

    public String champion(int season, String competition) {
        String comp = normalizeCompetition(competition == null ? DataStore.BRASILEIRAO : competition);
        if (!comp.equals(DataStore.BRASILEIRAO) && !comp.startsWith("Serie")) {
            String f = finals(comp);
            return f.lines().filter(l -> l.contains(" " + season)).collect(Collectors.joining("\n", comp + " " + season + " final:\n", ""));
        }
        List<Record> t = standingsTable(season, comp);
        if (t.isEmpty()) return "No " + comp + " data for " + season + ".";
        Record r = t.get(0);
        return String.format("%s won the %d %s with %d points (%dW, %dD, %dL), calculated from match results.",
                r.team, season, comp, r.points(), r.wins, r.draws, r.losses);
    }

    public String relegated(int season) {
        List<Record> t = standingsTable(season, DataStore.BRASILEIRAO);
        if (t.size() < 16) return "Insufficient Brasileirão data for " + season + ".";
        List<Record> bottom = t.subList(t.size() - 4, t.size());
        StringBuilder sb = new StringBuilder("Teams relegated from the " + season + " Brasileirão (bottom 4, calculated):\n");
        for (int i = 0; i < bottom.size(); i++) {
            Record r = bottom.get(i);
            sb.append(String.format("%d. %s - %d pts%n", t.size() - 3 + i, r.team, r.points()));
        }
        return sb.toString().trim();
    }

    public String topScoringTeams(Integer season, String competition, Integer limit) {
        String comp = normalizeCompetition(competition);
        Map<String, int[]> goals = new HashMap<>();
        Map<String, String> names = new HashMap<>();
        for (Match m : findMatches(null, null, comp, season, null, null, null)) {
            goals.computeIfAbsent(m.homeKey(), k -> new int[2])[0] += m.homeGoals();
            goals.get(m.homeKey())[1]++;
            goals.computeIfAbsent(m.awayKey(), k -> new int[2])[0] += m.awayGoals();
            goals.get(m.awayKey())[1]++;
            names.putIfAbsent(m.homeKey(), Teams.display(m.home()));
            names.putIfAbsent(m.awayKey(), Teams.display(m.away()));
        }
        if (goals.isEmpty()) return "No matches found.";
        List<Map.Entry<String, int[]>> l = new ArrayList<>(goals.entrySet());
        l.sort((x, y) -> y.getValue()[0] - x.getValue()[0]);
        StringBuilder sb = new StringBuilder("Top scoring teams" + (comp != null ? " in " + comp : "") + (season != null ? " " + season : "") + ":\n");
        int lim = limit == null ? 10 : limit;
        for (int i = 0; i < Math.min(lim, l.size()); i++) {
            var e = l.get(i);
            sb.append(String.format("%d. %s - %d goals in %d matches (%.2f per match)%n", i + 1, names.get(e.getKey()),
                    e.getValue()[0], e.getValue()[1], e.getValue()[0] / (double) e.getValue()[1]));
        }
        return sb.toString().trim();
    }

    // ================= statistics =================
    public String competitionStats(String competition, Integer season) {
        List<Match> ms = findMatches(null, null, competition, season, null, null, null);
        if (ms.isEmpty()) return "No matches found.";
        long hw = ms.stream().filter(m -> m.homeGoals() > m.awayGoals()).count();
        long aw = ms.stream().filter(m -> m.homeGoals() < m.awayGoals()).count();
        long goals = ms.stream().mapToLong(Match::totalGoals).sum();
        String comp = normalizeCompetition(competition);
        return String.format("Statistics for %s%s:%n- Matches: %d%n- Total goals: %d%n- Average goals per match: %.2f%n"
                        + "- Home win rate: %.1f%%%n- Away win rate: %.1f%%%n- Draw rate: %.1f%%",
                comp == null ? "all competitions" : comp, season == null ? "" : " " + season, ms.size(), goals,
                goals / (double) ms.size(), 100.0 * hw / ms.size(), 100.0 * aw / ms.size(),
                100.0 * (ms.size() - hw - aw) / ms.size());
    }

    public String biggestWins(String competition, Integer season, Integer limit) {
        List<Match> ms = new ArrayList<>(findMatches(null, null, competition, season, null, null, null));
        ms.sort(Comparator.comparingInt((Match m) -> Math.abs(m.homeGoals() - m.awayGoals())).reversed()
                .thenComparing(Comparator.comparingInt(Match::totalGoals).reversed()));
        if (ms.isEmpty()) return "No matches found.";
        int lim = limit == null ? 10 : limit;
        StringBuilder sb = new StringBuilder("Biggest victories" + (competition != null ? " in " + normalizeCompetition(competition) : "") + ":\n");
        for (int i = 0; i < Math.min(lim, ms.size()); i++) sb.append(i + 1).append(". ").append(ms.get(i).format()).append('\n');
        return sb.toString().trim();
    }

    public String bestRecords(String competition, Integer season, String venue, Integer minMatches, Integer limit) {
        String v = venue == null ? "all" : venue.toLowerCase();
        Map<String, Record> recs = new HashMap<>();
        for (Match m : findMatches(null, null, competition, season, null, null, null)) {
            if (!v.equals("away")) recs.computeIfAbsent(m.homeKey(), k -> newRecord(m.home())).add(m.homeGoals(), m.awayGoals());
            if (!v.equals("home")) recs.computeIfAbsent(m.awayKey(), k -> newRecord(m.away())).add(m.awayGoals(), m.homeGoals());
        }
        int min = minMatches == null ? 10 : minMatches;
        List<Record> l = recs.values().stream().filter(r -> r.played >= min)
                .sorted(Comparator.comparingDouble(Record::winRate).reversed()).toList();
        if (l.isEmpty()) return "No teams with at least " + min + " matches.";
        int lim = limit == null ? 10 : limit;
        StringBuilder sb = new StringBuilder("Best " + (v.equals("all") ? "overall" : v) + " records"
                + (competition != null ? " in " + normalizeCompetition(competition) : "") + (season != null ? " " + season : "")
                + " (min " + min + " matches):\n");
        for (int i = 0; i < Math.min(lim, l.size()); i++) {
            Record r = l.get(i);
            sb.append(String.format("%d. %s - Win rate %.1f%% (%dW %dD %dL in %d, GF %d GA %d)%n", i + 1, r.team,
                    r.winRate(), r.wins, r.draws, r.losses, r.played, r.gf, r.ga));
        }
        return sb.toString().trim();
    }

    public String compareSeasons(String competition, List<Integer> seasons) {
        StringBuilder sb = new StringBuilder();
        for (int s : seasons) {
            sb.append(competitionStats(competition == null ? DataStore.BRASILEIRAO : competition, s)).append('\n');
            List<Record> t = standingsTable(s, competition == null ? DataStore.BRASILEIRAO : competition);
            if (!t.isEmpty()) sb.append("- Champion (calculated): ").append(t.get(0).team).append(" (").append(t.get(0).points()).append(" pts)\n");
            sb.append('\n');
        }
        return sb.toString().trim();
    }

    // ================= players =================
    public List<Player> findPlayers(String name, String nationality, String club, String position, Integer minOverall) {
        return data.players().stream()
                .filter(p -> name == null || name.isBlank() || fold(p.name()).contains(fold(name)))
                .filter(p -> nationality == null || nationality.isBlank() || fold(p.nationality()).equals(fold(nationality)))
                .filter(p -> club == null || club.isBlank() || fold(p.club()).contains(fold(club)))
                .filter(p -> position == null || position.isBlank() || positionMatches(p.position(), position))
                .filter(p -> minOverall == null || p.overall() >= minOverall)
                .sorted(Comparator.comparingInt(Player::overall).reversed())
                .collect(Collectors.toList());
    }

    static final Map<String, Set<String>> POSITION_GROUPS = Map.of(
            "forward", Set.of("ST", "CF", "LS", "RS", "LW", "RW", "LF", "RF"),
            "midfielder", Set.of("CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"),
            "defender", Set.of("CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"),
            "goalkeeper", Set.of("GK"));

    static boolean positionMatches(String pos, String query) {
        String q = query.toLowerCase().replaceAll("s$", "");
        for (var e : POSITION_GROUPS.entrySet()) if (e.getKey().startsWith(q)) return e.getValue().contains(pos);
        if (q.equals("striker") || q.equals("attacker")) return POSITION_GROUPS.get("forward").contains(pos);
        return pos.equalsIgnoreCase(query);
    }

    private static String fold(String s) { return s == null ? "" : Teams.stripAccents(s).toLowerCase(); }

    public String searchPlayers(String name, String nationality, String club, String position, Integer minOverall, Integer limit) {
        List<Player> ps = findPlayers(name, nationality, club, position, minOverall);
        if (ps.isEmpty()) return "No players found matching the criteria.";
        int lim = limit == null ? 20 : limit;
        StringBuilder sb = new StringBuilder("Found " + ps.size() + " players:\n");
        for (int i = 0; i < Math.min(lim, ps.size()); i++) sb.append(i + 1).append(". ").append(ps.get(i).format()).append('\n');
        if (ps.size() > lim) sb.append("... (").append(ps.size() - lim).append(" more)\n");
        return sb.toString().trim();
    }

    public String playersByClub(String nationality, Integer limit) {
        String nat = nationality == null ? "Brazil" : nationality;
        Map<String, List<Player>> byClub = findPlayers(null, nat, null, null, null).stream()
                .filter(p -> !p.club().isBlank()).collect(Collectors.groupingBy(Player::club));
        if (byClub.isEmpty()) return "No players found with nationality " + nat + ".";
        List<Map.Entry<String, List<Player>>> l = new ArrayList<>(byClub.entrySet());
        l.sort((a, b) -> b.getValue().size() != a.getValue().size() ? b.getValue().size() - a.getValue().size() : a.getKey().compareTo(b.getKey()));
        int lim = limit == null ? 15 : limit;
        StringBuilder sb = new StringBuilder(nat + " players by club:\n");
        for (int i = 0; i < Math.min(lim, l.size()); i++) {
            var e = l.get(i);
            double avg = e.getValue().stream().mapToInt(Player::overall).average().orElse(0);
            sb.append(String.format("- %s: %d players (avg rating: %.0f)%n", e.getKey(), e.getValue().size(), avg));
        }
        return sb.toString().trim();
    }

    /** Cross-file query: FIFA players at a club plus that club's match record. */
    public String clubProfile(String club) {
        StringBuilder sb = new StringBuilder("Club profile: " + club + "\n\n");
        sb.append(searchPlayers(null, null, club, null, null, 10)).append("\n\n");
        sb.append(teamStats(club, null, null, null)).append("\n\n");
        sb.append(teamCompetitions(club));
        return sb.toString();
    }

    public String datasetInfo() {
        StringBuilder sb = new StringBuilder("Loaded datasets:\n");
        data.rowsPerFile().forEach((f, n) -> sb.append("- ").append(f).append(": ").append(n).append(" rows\n"));
        Map<String, Long> byComp = data.matches().stream().collect(Collectors.groupingBy(Match::competition, TreeMap::new, Collectors.counting()));
        sb.append("Deduplicated matches by competition: ").append(byComp).append('\n');
        sb.append("Players: ").append(data.players().size());
        return sb.toString();
    }
}
