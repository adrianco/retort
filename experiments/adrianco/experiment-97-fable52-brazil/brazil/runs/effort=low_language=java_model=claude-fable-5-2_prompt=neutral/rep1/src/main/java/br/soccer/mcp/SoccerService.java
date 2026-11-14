package br.soccer.mcp;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.stream.Collectors;

/**
 * Query layer over {@link DataStore}. Every public query returns human-readable text ready to be
 * sent to an LLM. Invalid input is reported with {@link IllegalArgumentException}.
 */
final class SoccerService {
    /** Criteria for selecting matches; every field is optional. */
    static final class MatchFilter {
        String team, opponent, venue, competition, stage, round, source;
        Integer season;
        LocalDate from, to;
    }

    /** Win/draw/loss and goals tally. */
    static final class Rec {
        int p, w, d, l, gf, ga;

        void add(int goalsFor, int goalsAgainst) {
            p++;
            gf += goalsFor;
            ga += goalsAgainst;
            if (goalsFor > goalsAgainst) w++;
            else if (goalsFor == goalsAgainst) d++;
            else l++;
        }

        int points() { return 3 * w + d; }
        int gd() { return gf - ga; }
        double winRate() { return p == 0 ? 0 : 100.0 * w / p; }
        double ppg() { return p == 0 ? 0 : (double) points() / p; }
    }

    private static final String[][] RIVALRIES = {
        {"Flamengo", "Fluminense", "Fla-Flu"}, {"Flamengo", "Vasco", "Clássico dos Milhões"},
        {"Flamengo", "Botafogo", "Clássico da Rivalidade"}, {"Fluminense", "Vasco", "Clássico dos Gigantes"},
        {"Fluminense", "Botafogo", "Clássico Vovô"}, {"Botafogo", "Vasco", "Clássico da Amizade"},
        {"Corinthians", "Palmeiras", "Derby Paulista"}, {"Corinthians", "São Paulo", "Majestoso"},
        {"Palmeiras", "São Paulo", "Choque-Rei"}, {"Santos", "Corinthians", "Clássico Alvinegro"},
        {"Santos", "Palmeiras", "Clássico da Saudade"}, {"Santos", "São Paulo", "San-São"},
        {"Grêmio", "Internacional", "Gre-Nal"}, {"Atlético-MG", "Cruzeiro", "Clássico Mineiro"},
        {"Bahia", "Vitória", "Ba-Vi"}, {"Sport", "Náutico", "Clássico dos Clássicos"},
        {"Sport", "Santa Cruz", "Clássico das Multidões"}, {"Náutico", "Santa Cruz", "Clássico das Emoções"},
        {"Ceará", "Fortaleza", "Clássico-Rei"}, {"Athletico-PR", "Coritiba", "Atletiba"},
        {"Goiás", "Vila Nova", "Derby do Cerrado"}, {"Avaí", "Figueirense", "Clássico de Florianópolis"},
        {"Remo", "Paysandu", "Re-Pa"},
    };
    private static final List<String> STAGE_ORDER =
            List.of("group stage", "round of 16", "quarterfinals", "semifinals", "final");
    private static final Map<String, Set<String>> POSITION_GROUPS = Map.of(
            "forward", Set.of("ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"),
            "midfielder", Set.of("CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"),
            "defender", Set.of("CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"),
            "goalkeeper", Set.of("GK"));

    private final DataStore ds;
    private final TeamNames teams;
    private final Map<String, String> derbyNames = new HashMap<>();

    SoccerService(DataStore ds) {
        this.ds = ds;
        this.teams = ds.teams;
        for (String[] r : RIVALRIES) derbyNames.put(pairKey(teams.canonical(r[0]), teams.canonical(r[1])), r[2]);
        // A FIFA club is treated as Brazilian when its name maps to a Serie A team from the match
        // files and at least half of its squad is Brazilian (guards against foreign namesakes).
        Set<String> serieA = ds.matches.stream().filter(m -> DataStore.SERIE_A.equals(m.competition))
                .flatMap(m -> java.util.stream.Stream.of(m.home, m.away)).collect(Collectors.toSet());
        Map<String, int[]> squad = new HashMap<>();
        for (Player p : ds.players) {
            if (p.clubTeamKey == null || !serieA.contains(p.clubTeamKey)) continue;
            int[] c = squad.computeIfAbsent(p.club, k -> new int[2]);
            c[0]++;
            if ("Brazil".equals(p.nationality)) c[1]++;
        }
        Set<String> brazilianClubNames = new HashSet<>();
        squad.forEach((club, c) -> { if (c[1] * 2 >= c[0]) brazilianClubNames.add(club); });
        for (Player p : ds.players) {
            if (!brazilianClubNames.contains(p.club)) p.clubTeamKey = null;
        }
    }

    // ------------------------------------------------------------------ resolution helpers

    private static String pairKey(String a, String b) {
        return a.compareTo(b) <= 0 ? a + "|" + b : b + "|" + a;
    }

    String name(String key) { return teams.display(key); }

    /** Resolves a team name to one or more canonical keys, or fails with suggestions. */
    List<String> resolveTeams(String query) {
        if (query == null || query.isBlank()) throw new IllegalArgumentException("Team name must not be empty.");
        List<String> keys = teams.resolve(query);
        if (keys.isEmpty()) {
            throw new IllegalArgumentException("No team matching \"" + query + "\" was found in the match data."
                    + suggestions(query));
        }
        return keys;
    }

    /** Resolves a team name that must identify exactly one club. */
    String resolveTeam(String query) {
        List<String> keys = resolveTeams(query);
        if (keys.size() > 1) {
            throw new IllegalArgumentException("\"" + query + "\" is ambiguous. Did you mean: "
                    + keys.stream().limit(10).map(this::name).collect(Collectors.joining(", ")) + "?");
        }
        return keys.get(0);
    }

    private String suggestions(String query) {
        String f = TeamNames.fold(query);
        if (f.length() < 3) return "";
        String prefix = f.substring(0, 3);
        List<String> s = teams.knownTeams().stream().filter(k -> k.startsWith(prefix)).limit(8)
                .map(this::name).collect(Collectors.toList());
        return s.isEmpty() ? "" : " Similar names: " + String.join(", ", s) + ".";
    }

    static String resolveCompetition(String q) {
        if (q == null || q.isBlank()) return null;
        String f = TeamNames.fold(q);
        if (f.contains("libertadores")) return DataStore.LIBERTADORES;
        if (f.contains("copa") || f.contains("cup")) return DataStore.COPA_DO_BRASIL;
        if (f.contains("serie b") || f.equals("b")) return DataStore.SERIE_B;
        if (f.contains("serie c") || f.equals("c")) return DataStore.SERIE_C;
        if (f.contains("brasileir") || f.contains("serie a") || f.equals("a") || f.contains("campeonato")
                || f.contains("league")) return DataStore.SERIE_A;
        throw new IllegalArgumentException("Unknown competition \"" + q + "\". Valid: "
                + String.join(", ", DataStore.COMPETITIONS) + ".");
    }

    private static String resolveSource(String q) {
        if (q == null || q.isBlank()) return null;
        String f = TeamNames.fold(q).replace(".csv", "").replace('_', ' ').replace('-', ' ');
        if (f.contains("novo") || f.contains("historical")) return DataStore.F_HISTORICAL;
        if (f.contains("br football") || f.contains("extended")) return DataStore.F_EXTENDED;
        if (f.contains("cup") || f.contains("copa do brasil")) return DataStore.F_CUP;
        if (f.contains("libertadores")) return DataStore.F_LIBERTADORES;
        if (f.contains("brasileirao")) return DataStore.F_BRASILEIRAO;
        throw new IllegalArgumentException("Unknown source \"" + q + "\". Valid: " + DataStore.F_BRASILEIRAO + ", "
                + DataStore.F_CUP + ", " + DataStore.F_LIBERTADORES + ", " + DataStore.F_EXTENDED + ", "
                + DataStore.F_HISTORICAL + ".");
    }

    private static String resolveVenue(String v) {
        if (v == null || v.isBlank()) return "either";
        String f = v.trim().toLowerCase(Locale.ROOT);
        return switch (f) {
            case "home" -> "home";
            case "away" -> "away";
            case "either", "all", "both", "any" -> "either";
            default -> throw new IllegalArgumentException("venue must be one of: home, away, either.");
        };
    }

    /** Selects matches. Duplicate coverage between files is removed unless a source file is named. */
    List<Match> select(MatchFilter f) {
        Set<String> team = f.team == null || f.team.isBlank() ? null : new HashSet<>(resolveTeams(f.team));
        Set<String> opp = f.opponent == null || f.opponent.isBlank() ? null : new HashSet<>(resolveTeams(f.opponent));
        if (team == null && opp != null) { team = opp; opp = null; }
        String venue = resolveVenue(f.venue);
        String comp = resolveCompetition(f.competition);
        String source = resolveSource(f.source);
        String stage = f.stage == null || f.stage.isBlank() ? null : normStage(f.stage);
        String round = f.round == null || f.round.isBlank() ? null : f.round.trim();
        if (f.from != null && f.to != null && f.from.isAfter(f.to)) {
            throw new IllegalArgumentException("date_from must not be after date_to.");
        }
        List<Match> out = new ArrayList<>();
        for (Match m : ds.matches) {
            if (source != null) { if (!m.source.equals(source)) continue; }
            // stage labels live in exactly one file per competition, so searching them cannot double count
            else if (stage != null) { if (m.stage == null) continue; }
            else if (!m.primary) continue;
            if (comp != null && !comp.equals(m.competition)) continue;
            if (f.season != null && m.season != f.season) continue;
            if (stage != null && !stage.equals(m.stage)) continue;
            if (round != null && !round.equals(m.round)) continue;
            if (f.from != null && (m.date == null || m.date.isBefore(f.from))) continue;
            if (f.to != null && (m.date == null || m.date.isAfter(f.to))) continue;
            if (team != null) {
                boolean h = team.contains(m.home), a = team.contains(m.away);
                if (venue.equals("home") ? !h : venue.equals("away") ? !a : !(h || a)) continue;
                if (opp != null && !(h && opp.contains(m.away) || a && opp.contains(m.home))) continue;
            }
            out.add(m);
        }
        return out;
    }

    private static String normStage(String s) {
        String f = TeamNames.fold(s);
        if (f.startsWith("final")) return "final";
        if (f.startsWith("semi")) return "semifinals";
        if (f.startsWith("quarter")) return "quarterfinals";
        if (f.contains("16")) return "round of 16";
        if (f.startsWith("group")) return "group stage";
        throw new IllegalArgumentException("stage must be one of: " + String.join(", ", STAGE_ORDER) + ".");
    }

    private static final Comparator<Match> BY_DATE = Comparator
            .comparing((Match m) -> m.date, Comparator.nullsFirst(Comparator.naturalOrder()))
            .thenComparing(m -> m.home);

    // ------------------------------------------------------------------ formatting helpers

    String line(Match m) { return line(m, false); }

    String line(Match m, boolean withStats) {
        StringBuilder sb = new StringBuilder();
        sb.append(m.date == null ? "(date unknown)" : m.date.toString()).append(": ");
        if (m.played()) {
            sb.append(name(m.home)).append(' ').append(m.homeGoals).append('-').append(m.awayGoals).append(' ')
                    .append(name(m.away));
        } else {
            sb.append(name(m.home)).append(" vs ").append(name(m.away)).append(" [no score recorded]");
        }
        sb.append(" (").append(m.competition).append(' ').append(m.season);
        if (m.stage != null) sb.append(", ").append(m.stage);
        if (m.round != null) sb.append(", Round ").append(m.round);
        if (m.arena != null) sb.append(", ").append(m.arena);
        sb.append(')');
        if (withStats && (m.homeCorners != null || m.homeShots != null)) {
            sb.append(" [");
            List<String> parts = new ArrayList<>();
            if (m.homeCorners != null && m.awayCorners != null) parts.add("corners " + m.homeCorners + "-" + m.awayCorners);
            if (m.homeShots != null && m.awayShots != null) parts.add("shots " + m.homeShots + "-" + m.awayShots);
            if (m.homeAttacks != null && m.awayAttacks != null) parts.add("attacks " + m.homeAttacks + "-" + m.awayAttacks);
            sb.append(String.join(", ", parts)).append(']');
        }
        return sb.toString();
    }

    private static String pct(double v) { return String.format(Locale.ROOT, "%.1f%%", v); }
    private static String f2(double v) { return String.format(Locale.ROOT, "%.2f", v); }
    private static int clamp(Integer limit, int def, int max) {
        if (limit == null) return def;
        if (limit < 1) throw new IllegalArgumentException("limit must be at least 1.");
        return Math.min(limit, max);
    }

    private String describe(MatchFilter f) {
        List<String> parts = new ArrayList<>();
        String comp = resolveCompetition(f.competition);
        if (comp != null) parts.add(comp);
        if (f.season != null) parts.add(String.valueOf(f.season));
        if (f.stage != null && !f.stage.isBlank()) parts.add(normStage(f.stage));
        if (f.round != null && !f.round.isBlank()) parts.add("round " + f.round);
        if (f.from != null) parts.add("from " + f.from);
        if (f.to != null) parts.add("to " + f.to);
        if (f.source != null && !f.source.isBlank()) parts.add("source " + resolveSource(f.source));
        return parts.isEmpty() ? "all competitions and seasons" : String.join(", ", parts);
    }

    private Rec record(List<Match> ms, Set<String> team) {
        Rec r = new Rec();
        for (Match m : ms) {
            if (!m.played()) continue;
            if (team.contains(m.home)) r.add(m.homeGoals, m.awayGoals);
            else if (team.contains(m.away)) r.add(m.awayGoals, m.homeGoals);
        }
        return r;
    }

    private static String recLine(Rec r) {
        return "Matches: " + r.p + ", Wins: " + r.w + ", Draws: " + r.d + ", Losses: " + r.l + ", Goals For: " + r.gf
                + ", Goals Against: " + r.ga + ", Win rate: " + pct(r.winRate());
    }

    // ------------------------------------------------------------------ match queries

    String findMatches(MatchFilter f, Integer limit, boolean oldestFirst, boolean withStats) {
        List<Match> ms = select(f);
        ms.sort(oldestFirst ? BY_DATE : BY_DATE.reversed());
        int max = clamp(limit, 20, 200);
        StringBuilder sb = new StringBuilder();
        String who = f.team == null || f.team.isBlank() ? (f.opponent == null || f.opponent.isBlank() ? "" : teamLabel(f.opponent))
                : teamLabel(f.team) + (f.opponent == null || f.opponent.isBlank() ? "" : " vs " + teamLabel(f.opponent));
        String derby = f.team != null && f.opponent != null && !f.team.isBlank() && !f.opponent.isBlank()
                && teams.resolve(f.team).size() == 1 && teams.resolve(f.opponent).size() == 1
                ? derbyNames.get(pairKey(teams.resolve(f.team).get(0), teams.resolve(f.opponent).get(0))) : null;
        sb.append("Matches").append(who.isEmpty() ? "" : " for " + who).append(derby == null ? "" : " (" + derby + ")")
                .append(" — ").append(describe(f)).append(": ").append(ms.size()).append(" found");
        if (ms.isEmpty()) return sb.append(".\nNo matches in the dataset satisfy these criteria.").toString();
        sb.append(ms.size() > max ? " (showing " + max + (oldestFirst ? " oldest" : " most recent") + ")" : "").append('\n');
        ms.stream().limit(max).forEach(m -> sb.append("- ").append(line(m, withStats)).append('\n'));
        if (ms.size() > max) sb.append("... (").append(ms.size() - max).append(" more matches in dataset)\n");
        if (f.team != null && !f.team.isBlank()) {
            Set<String> t = new HashSet<>(resolveTeams(f.team));
            Rec r = record(ms, t);
            if (f.opponent != null && !f.opponent.isBlank()) {
                sb.append("\nHead-to-head in dataset: ").append(teamLabel(f.team)).append(' ').append(r.w).append(" wins, ")
                        .append(teamLabel(f.opponent)).append(' ').append(r.l).append(" wins, ").append(r.d).append(" draws");
            } else if (r.p > 0) {
                sb.append("\n").append(teamLabel(f.team)).append(" record in these matches — ").append(recLine(r));
            }
        }
        return sb.toString().trim();
    }

    private String teamLabel(String query) {
        List<String> keys = resolveTeams(query);
        return keys.size() == 1 ? name(keys.get(0)) : query.trim();
    }

    String headToHead(String teamA, String teamB, String competition, Integer season, Integer recent) {
        String a = resolveTeam(teamA), b = resolveTeam(teamB);
        if (a.equals(b)) throw new IllegalArgumentException("team_a and team_b resolve to the same club.");
        MatchFilter f = new MatchFilter();
        f.team = teamA; f.opponent = teamB; f.competition = competition; f.season = season;
        List<Match> ms = select(f);
        ms.sort(BY_DATE.reversed());
        String derby = derbyNames.get(pairKey(a, b));
        StringBuilder sb = new StringBuilder();
        sb.append(name(a)).append(" vs ").append(name(b)).append(derby == null ? "" : " (" + derby + ")")
                .append(" — head-to-head, ").append(describe(f)).append('\n');
        List<Match> played = ms.stream().filter(Match::played).collect(Collectors.toList());
        if (played.isEmpty()) return sb.append("No played matches between these teams in the dataset.").toString();
        Rec r = record(played, Set.of(a));
        sb.append("Matches: ").append(r.p).append('\n');
        sb.append(name(a)).append(" wins: ").append(r.w).append(", ").append(name(b)).append(" wins: ").append(r.l)
                .append(", Draws: ").append(r.d).append('\n');
        sb.append("Goals: ").append(name(a)).append(' ').append(r.gf).append(", ").append(name(b)).append(' ').append(r.ga).append('\n');
        Rec home = record(played.stream().filter(m -> m.home.equals(a)).collect(Collectors.toList()), Set.of(a));
        Rec away = record(played.stream().filter(m -> m.away.equals(a)).collect(Collectors.toList()), Set.of(a));
        sb.append(name(a)).append(" at home: ").append(home.w).append("W ").append(home.d).append("D ").append(home.l)
                .append("L; away: ").append(away.w).append("W ").append(away.d).append("D ").append(away.l).append("L\n");
        Map<String, List<Match>> byComp = played.stream().collect(Collectors.groupingBy(m -> m.competition, TreeMap::new, Collectors.toList()));
        if (byComp.size() > 1) {
            sb.append("By competition:\n");
            byComp.forEach((c, list) -> {
                Rec x = record(list, Set.of(a));
                sb.append("- ").append(c).append(": ").append(x.p).append(" matches, ").append(name(a)).append(' ').append(x.w)
                        .append(" wins, ").append(name(b)).append(' ').append(x.l).append(" wins, ").append(x.d).append(" draws\n");
            });
        }
        int n = clamp(recent, 10, 100);
        sb.append("Most recent matches:\n");
        played.stream().limit(n).forEach(m -> sb.append("- ").append(line(m)).append('\n'));
        if (played.size() > n) sb.append("... (").append(played.size() - n).append(" more matches in dataset)\n");
        return sb.toString().trim();
    }

    // ------------------------------------------------------------------ team queries

    String teamStats(String team, Integer season, String competition, String venue) {
        String key = resolveTeam(team);
        MatchFilter f = new MatchFilter();
        f.team = team; f.season = season; f.competition = competition; f.venue = venue;
        String v = resolveVenue(venue);
        List<Match> ms = select(f).stream().filter(Match::played).collect(Collectors.toList());
        StringBuilder sb = new StringBuilder();
        sb.append(name(key)).append(v.equals("either") ? "" : " " + v).append(" record (").append(describe(f)).append("):\n");
        if (ms.isEmpty()) return sb.append("No played matches found in the dataset.").toString();
        Set<String> t = Set.of(key);
        Rec r = record(ms, t);
        appendRec(sb, r);
        if (v.equals("either")) {
            Rec h = record(ms.stream().filter(m -> m.home.equals(key)).collect(Collectors.toList()), t);
            Rec a = record(ms.stream().filter(m -> m.away.equals(key)).collect(Collectors.toList()), t);
            sb.append("Home: ").append(shortRec(h)).append('\n').append("Away: ").append(shortRec(a)).append('\n');
        }
        Map<String, List<Match>> byComp = ms.stream().collect(Collectors.groupingBy(m -> m.competition, TreeMap::new, Collectors.toList()));
        if (byComp.size() > 1) {
            sb.append("By competition:\n");
            byComp.forEach((c, list) -> sb.append("- ").append(c).append(": ").append(shortRec(record(list, t))).append('\n'));
        }
        return sb.toString().trim();
    }

    private static void appendRec(StringBuilder sb, Rec r) {
        sb.append("- Matches: ").append(r.p).append('\n');
        sb.append("- Wins: ").append(r.w).append(", Draws: ").append(r.d).append(", Losses: ").append(r.l).append('\n');
        sb.append("- Goals For: ").append(r.gf).append(", Goals Against: ").append(r.ga).append(" (difference ")
                .append(r.gd() >= 0 ? "+" : "").append(r.gd()).append(")\n");
        sb.append("- Win rate: ").append(pct(r.winRate())).append(", Points per game: ").append(f2(r.ppg())).append('\n');
    }

    private static String shortRec(Rec r) {
        return r.p + " matches, " + r.w + "W " + r.d + "D " + r.l + "L, goals " + r.gf + "-" + r.ga + ", win rate "
                + pct(r.winRate());
    }

    String teamProfile(String team) {
        String key = resolveTeam(team);
        MatchFilter f = new MatchFilter();
        f.team = team;
        List<Match> ms = select(f);
        StringBuilder sb = new StringBuilder();
        sb.append(name(key)).append(" — profile from the dataset\n");
        Set<String> t = Set.of(key);
        sb.append("Competitions played:\n");
        Map<String, List<Match>> byComp = ms.stream().collect(Collectors.groupingBy(m -> m.competition, TreeMap::new, Collectors.toList()));
        byComp.forEach((c, list) -> {
            TreeSet<Integer> seasons = list.stream().map(m -> m.season).collect(Collectors.toCollection(TreeSet::new));
            sb.append("- ").append(c).append(": ").append(seasons.size()).append(" seasons (").append(seasons.first())
                    .append('-').append(seasons.last()).append("), ").append(shortRec(record(list, t))).append('\n');
        });
        Rec all = record(ms, t);
        sb.append("Overall: ").append(shortRec(all)).append('\n');
        ms.stream().filter(Match::played).filter(m -> m.date != null).max(BY_DATE)
                .ifPresent(m -> sb.append("Most recent match: ").append(line(m)).append('\n'));
        List<String> rivals = new ArrayList<>();
        derbyNames.forEach((pair, derby) -> {
            String[] p = pair.split("\\|");
            if (p[0].equals(key)) rivals.add(name(p[1]) + " (" + derby + ")");
            else if (p[1].equals(key)) rivals.add(name(p[0]) + " (" + derby + ")");
        });
        if (!rivals.isEmpty()) sb.append("Traditional rivals: ").append(String.join(", ", new TreeSet<>(rivals))).append('\n');
        List<Player> squad = ds.players.stream().filter(p -> key.equals(p.clubTeamKey))
                .sorted(Comparator.comparingInt((Player p) -> -p.overall)).collect(Collectors.toList());
        if (squad.isEmpty()) {
            sb.append("FIFA player data: no players listed for this club.\n");
        } else {
            sb.append("FIFA player data: ").append(squad.size()).append(" players (avg overall ")
                    .append(f2(squad.stream().mapToInt(p -> p.overall).average().orElse(0))).append("). Top rated:\n");
            squad.stream().limit(5).forEach(p -> sb.append("- ").append(playerLine(p)).append('\n'));
        }
        return sb.toString().trim();
    }

    String teamRankings(String metric, String venue, String competition, Integer season, Integer minMatches, Integer limit) {
        String v = resolveVenue(venue);
        String met = metric == null || metric.isBlank() ? "win_rate" : metric.trim().toLowerCase(Locale.ROOT);
        Comparator<Map.Entry<String, Rec>> cmp = switch (met) {
            case "win_rate" -> Comparator.comparingDouble(e -> -e.getValue().winRate());
            case "points_per_game" -> Comparator.comparingDouble(e -> -e.getValue().ppg());
            case "points" -> Comparator.comparingInt(e -> -e.getValue().points());
            case "wins" -> Comparator.comparingInt(e -> -e.getValue().w);
            case "goals_for" -> Comparator.comparingInt(e -> -e.getValue().gf);
            case "goals_against" -> Comparator.comparingInt(e -> e.getValue().ga);
            case "goal_difference" -> Comparator.comparingInt(e -> -e.getValue().gd());
            case "losses" -> Comparator.comparingInt(e -> -e.getValue().l);
            default -> throw new IllegalArgumentException("metric must be one of: win_rate, points_per_game, points, wins, "
                    + "goals_for, goals_against, goal_difference, losses.");
        };
        MatchFilter f = new MatchFilter();
        f.competition = competition; f.season = season;
        Map<String, Rec> recs = new HashMap<>();
        for (Match m : select(f)) {
            if (!m.played()) continue;
            if (!v.equals("away")) recs.computeIfAbsent(m.home, k -> new Rec()).add(m.homeGoals, m.awayGoals);
            if (!v.equals("home")) recs.computeIfAbsent(m.away, k -> new Rec()).add(m.awayGoals, m.homeGoals);
        }
        if (minMatches != null && minMatches < 1) throw new IllegalArgumentException("min_matches must be at least 1.");
        int min = minMatches != null ? minMatches : (season != null ? 5 : 30);
        int max = clamp(limit, 10, 100);
        List<Map.Entry<String, Rec>> list = recs.entrySet().stream().filter(e -> e.getValue().p >= min)
                .sorted(cmp.thenComparing(e -> -e.getValue().points()).thenComparing(Map.Entry::getKey))
                .collect(Collectors.toList());
        StringBuilder sb = new StringBuilder();
        sb.append("Team ranking by ").append(met).append(v.equals("either") ? " (home and away)" : " (" + v + " matches only)")
                .append(" — ").append(describe(f)).append(", minimum ").append(min).append(" matches:\n");
        if (list.isEmpty()) return sb.append("No team has enough matches for these criteria.").toString();
        int i = 1;
        for (Map.Entry<String, Rec> e : list.subList(0, Math.min(max, list.size()))) {
            Rec r = e.getValue();
            sb.append(i++).append(". ").append(name(e.getKey())).append(" - ").append(r.p).append(" matches, ").append(r.w)
                    .append("W ").append(r.d).append("D ").append(r.l).append("L, goals ").append(r.gf).append('-').append(r.ga)
                    .append(", win rate ").append(pct(r.winRate())).append(", ").append(f2(r.ppg())).append(" pts/game\n");
        }
        return sb.toString().trim();
    }

    String derbies(Integer season, String competition, String team, Integer limit) {
        MatchFilter f = new MatchFilter();
        f.season = season; f.competition = competition; f.team = team;
        List<Match> ms = select(f).stream().filter(m -> derbyNames.containsKey(pairKey(m.home, m.away)))
                .sorted(BY_DATE.reversed()).collect(Collectors.toList());
        int max = clamp(limit, 50, 200);
        StringBuilder sb = new StringBuilder();
        sb.append("Derbies (matches between traditional rivals)").append(team == null || team.isBlank() ? "" : " involving " + teamLabel(team))
                .append(" — ").append(describe(f)).append(": ").append(ms.size()).append(" found\n");
        if (ms.isEmpty()) return sb.append("No derby matches in the dataset satisfy these criteria.").toString();
        ms.stream().limit(max).forEach(m -> sb.append("- ").append(derbyNames.get(pairKey(m.home, m.away))).append(" — ")
                .append(line(m)).append('\n'));
        if (ms.size() > max) sb.append("... (").append(ms.size() - max).append(" more matches in dataset)\n");
        return sb.toString().trim();
    }

    // ------------------------------------------------------------------ competition queries

    /** Sorted league table rows for a competition season (primary source only). */
    List<Map.Entry<String, Rec>> table(String competition, int season) {
        Map<String, Rec> recs = new HashMap<>();
        for (Match m : ds.matches) {
            if (!m.primary || !m.played() || m.season != season || !m.competition.equals(competition)) continue;
            recs.computeIfAbsent(m.home, k -> new Rec()).add(m.homeGoals, m.awayGoals);
            recs.computeIfAbsent(m.away, k -> new Rec()).add(m.awayGoals, m.homeGoals);
        }
        return recs.entrySet().stream().sorted(Comparator
                .comparingInt((Map.Entry<String, Rec> e) -> -e.getValue().points())
                .thenComparingInt(e -> -e.getValue().w)
                .thenComparingInt(e -> -e.getValue().gd())
                .thenComparingInt(e -> -e.getValue().gf)
                .thenComparing(Map.Entry::getKey)).collect(Collectors.toList());
    }

    private static boolean isLeague(String comp) {
        return DataStore.SERIE_A.equals(comp) || DataStore.SERIE_B.equals(comp) || DataStore.SERIE_C.equals(comp);
    }

    String standings(String competition, Integer season, Integer limit) {
        String comp = competition == null || competition.isBlank() ? DataStore.SERIE_A : resolveCompetition(competition);
        if (season == null) throw new IllegalArgumentException("season is required. " + seasonsAvailable(comp));
        if (!isLeague(comp)) {
            throw new IllegalArgumentException(comp + " is a knockout competition; use competition_bracket instead of standings.");
        }
        List<Map.Entry<String, Rec>> rows = table(comp, season);
        if (rows.isEmpty()) return "No " + comp + " matches for season " + season + " in the dataset. " + seasonsAvailable(comp);
        int n = rows.size();
        int played = rows.stream().mapToInt(e -> e.getValue().p).sum() / 2;
        boolean complete = played == n * (n - 1) && DataStore.SERIE_A.equals(comp);
        int relegated = !complete ? 0 : season == 2003 ? 2 : 4;
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(' ').append(comp).append(complete ? " Final Standings" : " Standings")
                .append(" (calculated from ").append(played).append(" matches in the dataset):\n");
        int max = clamp(limit, 100, 100);
        for (int i = 0; i < Math.min(n, max); i++) {
            Rec r = rows.get(i).getValue();
            sb.append(i + 1).append(". ").append(name(rows.get(i).getKey())).append(" - ").append(r.points()).append(" pts (")
                    .append(r.w).append("W, ").append(r.d).append("D, ").append(r.l).append("L), goals ").append(r.gf).append('-')
                    .append(r.ga).append(" (").append(r.gd() >= 0 ? "+" : "").append(r.gd()).append(')');
            if (i == 0) sb.append(complete ? " - Champion" : " - Leader");
            else if (i >= n - relegated) sb.append(" - Relegated");
            sb.append('\n');
        }
        if (complete) {
            sb.append("Note: computed purely from match results (3 pts per win; ties broken by wins, goal difference, goals scored). "
                    + "Points deductions or court rulings are not in the data, so official final positions can differ.");
        } else {
            sb.append("Note: the dataset does not hold a complete double round-robin for this season, so this table is "
                    + "partial and no champion or relegation is inferred.");
        }
        return sb.toString().trim();
    }

    private String seasonsAvailable(String comp) {
        TreeSet<Integer> s = ds.matches.stream().filter(m -> m.competition.equals(comp)).map(m -> m.season)
                .collect(Collectors.toCollection(TreeSet::new));
        return s.isEmpty() ? "" : "Seasons available for " + comp + ": " + s.first() + "-" + s.last() + ".";
    }

    String bracket(String competition, Integer season, boolean includeGroupStage) {
        String comp = competition == null || competition.isBlank() ? DataStore.LIBERTADORES : resolveCompetition(competition);
        if (season == null) throw new IllegalArgumentException("season is required. " + seasonsAvailable(comp));
        if (isLeague(comp)) throw new IllegalArgumentException(comp + " is a league; use standings instead of competition_bracket.");
        List<Match> staged = ds.matches.stream().filter(m -> m.competition.equals(comp) && m.season == season && m.stage != null)
                .sorted(BY_DATE).collect(Collectors.toList());
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(' ').append(comp).append(" knockout bracket (from the dataset):\n");
        if (staged.isEmpty()) {
            List<Match> all = ds.matches.stream().filter(m -> m.primary && m.competition.equals(comp) && m.season == season)
                    .sorted(BY_DATE).collect(Collectors.toList());
            if (all.isEmpty()) return "No " + comp + " matches for season " + season + " in the dataset. " + seasonsAvailable(comp);
            sb.append("Stage information is not available for this season; the last matches played were:\n");
            all.stream().skip(Math.max(0, all.size() - 15)).forEach(m -> sb.append("- ").append(line(m)).append('\n'));
            return sb.toString().trim();
        }
        for (String stage : STAGE_ORDER) {
            List<Match> ms = staged.stream().filter(m -> stage.equals(m.stage)).collect(Collectors.toList());
            if (ms.isEmpty()) continue;
            if (stage.equals("group stage") && !includeGroupStage) {
                sb.append("\nGroup stage: ").append(ms.size()).append(" matches (set include_group_stage=true to list them)\n");
                continue;
            }
            sb.append('\n').append(Character.toUpperCase(stage.charAt(0))).append(stage.substring(1)).append(":\n");
            Map<String, List<Match>> ties = new LinkedHashMap<>();
            for (Match m : ms) ties.computeIfAbsent(pairKey(m.home, m.away), k -> new ArrayList<>()).add(m);
            if (stage.equals("group stage")) {
                ms.forEach(m -> sb.append("- ").append(line(m)).append('\n'));
                continue;
            }
            for (List<Match> tie : ties.values()) {
                String a = tie.get(0).home, b = tie.get(0).away;
                int ga = 0, gb = 0;
                boolean allPlayed = true;
                List<String> legs = new ArrayList<>();
                for (Match m : tie) {
                    if (!m.played()) { allPlayed = false; legs.add(m.date + " not played/recorded"); continue; }
                    ga += m.home.equals(a) ? m.homeGoals : m.awayGoals;
                    gb += m.home.equals(b) ? m.homeGoals : m.awayGoals;
                    legs.add(m.date + " " + name(m.home) + " " + m.homeGoals + "-" + m.awayGoals + " " + name(m.away));
                }
                sb.append("- ").append(name(a)).append(" vs ").append(name(b));
                if (allPlayed) {
                    sb.append(": aggregate ").append(ga).append('-').append(gb);
                    sb.append(ga == gb ? " (level on aggregate; decided by away goals or penalties, not in data)"
                            : " — " + name(ga > gb ? a : b) + " advance" + (stage.equals("final") ? " as champions" : ""));
                }
                sb.append(" [").append(String.join("; ", legs)).append("]\n");
            }
        }
        return sb.toString().trim();
    }

    // ------------------------------------------------------------------ statistics

    private static final class Agg {
        int n, goals, homeWins, draws, awayWins, corners, cornerMatches;
        Match highest;
    }

    private Agg aggregate(List<Match> ms) {
        Agg a = new Agg();
        for (Match m : ms) {
            if (!m.played()) continue;
            a.n++;
            a.goals += m.totalGoals();
            if (m.homeGoals > m.awayGoals) a.homeWins++;
            else if (m.homeGoals.equals(m.awayGoals)) a.draws++;
            else a.awayWins++;
            if (m.homeCorners != null && m.awayCorners != null) { a.corners += m.homeCorners + m.awayCorners; a.cornerMatches++; }
            if (a.highest == null || m.totalGoals() > a.highest.totalGoals()) a.highest = m;
        }
        return a;
    }

    private void appendAgg(StringBuilder sb, Agg a) {
        sb.append("- Matches played: ").append(a.n).append('\n');
        sb.append("- Total goals: ").append(a.goals).append('\n');
        sb.append("- Average goals per match: ").append(f2((double) a.goals / a.n)).append('\n');
        sb.append("- Home win rate: ").append(pct(100.0 * a.homeWins / a.n)).append(" (").append(a.homeWins).append(")\n");
        sb.append("- Draw rate: ").append(pct(100.0 * a.draws / a.n)).append(" (").append(a.draws).append(")\n");
        sb.append("- Away win rate: ").append(pct(100.0 * a.awayWins / a.n)).append(" (").append(a.awayWins).append(")\n");
        if (a.cornerMatches > 0) {
            sb.append("- Average corners per match: ").append(f2((double) a.corners / a.cornerMatches)).append(" (")
                    .append(a.cornerMatches).append(" matches with corner data)\n");
        }
        sb.append("- Highest-scoring match: ").append(line(a.highest)).append('\n');
    }

    String leagueStats(MatchFilter f) {
        List<Match> ms = select(f);
        Agg a = aggregate(ms);
        StringBuilder sb = new StringBuilder();
        sb.append("Match statistics").append(f.team == null || f.team.isBlank() ? "" : " for matches involving " + teamLabel(f.team))
                .append(" — ").append(describe(f)).append(":\n");
        if (a.n == 0) return sb.append("No played matches in the dataset satisfy these criteria.").toString();
        appendAgg(sb, a);
        if (f.season == null) {
            Map<Integer, List<Match>> bySeason = ms.stream().filter(Match::played)
                    .collect(Collectors.groupingBy(m -> m.season, TreeMap::new, Collectors.toList()));
            if (bySeason.size() > 1) {
                sb.append("Goals per match by season: ");
                sb.append(bySeason.entrySet().stream().map(e -> e.getKey() + ": "
                        + f2(e.getValue().stream().mapToInt(Match::totalGoals).average().orElse(0))).collect(Collectors.joining(", ")));
            }
        }
        return sb.toString().trim();
    }

    String compareSeasons(String competition, Integer seasonA, Integer seasonB) {
        if (seasonA == null || seasonB == null) throw new IllegalArgumentException("season_a and season_b are required.");
        String comp = competition == null || competition.isBlank() ? DataStore.SERIE_A : resolveCompetition(competition);
        StringBuilder sb = new StringBuilder();
        sb.append(comp).append(": ").append(seasonA).append(" vs ").append(seasonB).append('\n');
        for (int season : new int[] {seasonA, seasonB}) {
            MatchFilter f = new MatchFilter();
            f.competition = comp; f.season = season;
            Agg a = aggregate(select(f));
            sb.append('\n').append(season).append(":\n");
            if (a.n == 0) { sb.append("- No played matches in the dataset. ").append(seasonsAvailable(comp)).append('\n'); continue; }
            appendAgg(sb, a);
            if (isLeague(comp)) {
                List<Map.Entry<String, Rec>> t = table(comp, season);
                Rec top = t.get(0).getValue();
                sb.append("- Top of the table: ").append(name(t.get(0).getKey())).append(" (").append(top.points()).append(" pts, ")
                        .append(top.w).append("W ").append(top.d).append("D ").append(top.l).append("L)\n");
                Map.Entry<String, Rec> best = t.stream().max(Comparator.comparingInt(e -> e.getValue().gf)).get();
                sb.append("- Most goals scored: ").append(name(best.getKey())).append(" (").append(best.getValue().gf).append(")\n");
            }
        }
        return sb.toString().trim();
    }

    String biggestWins(MatchFilter f, Integer limit) {
        int max = clamp(limit, 10, 100);
        List<Match> ms = select(f).stream().filter(Match::played).filter(m -> m.margin() > 0)
                .sorted(Comparator.comparingInt((Match m) -> -m.margin()).thenComparingInt(m -> -m.totalGoals())
                        .thenComparing(BY_DATE.reversed())).limit(max).collect(Collectors.toList());
        StringBuilder sb = new StringBuilder();
        sb.append("Biggest victories").append(f.team == null || f.team.isBlank() ? "" : " in matches involving " + teamLabel(f.team))
                .append(" — ").append(describe(f)).append(":\n");
        if (ms.isEmpty()) return sb.append("No decisive matches in the dataset satisfy these criteria.").toString();
        int i = 1;
        for (Match m : ms) sb.append(i++).append(". ").append(line(m)).append('\n');
        return sb.toString().trim();
    }

    // ------------------------------------------------------------------ player queries

    String playerLine(Player p) {
        return p.name + " - Overall: " + p.overall + ", Potential: " + p.potential + ", Position: "
                + (p.position.isBlank() ? "n/a" : p.position) + ", Club: " + (p.club.isBlank() ? "(no club)" : p.club)
                + ", Nationality: " + p.nationality + ", Age: " + p.age;
    }

    private static boolean nameMatches(String folded, String query) {
        for (String tok : TeamNames.fold(query).split(" ")) if (!folded.contains(tok)) return false;
        return true;
    }

    private Set<String> positions(String q) {
        String f = TeamNames.fold(q);
        if (f.endsWith("s")) f = f.substring(0, f.length() - 1);
        if (f.equals("striker") || f.equals("attacker")) f = "forward";
        if (f.equals("keeper") || f.equals("goalie")) f = "goalkeeper";
        if (f.equals("midfield")) f = "midfielder";
        if (f.equals("defence") || f.equals("defense") || f.equals("back")) f = "defender";
        Set<String> g = POSITION_GROUPS.get(f);
        return g != null ? g : Set.of(q.trim().toUpperCase(Locale.ROOT));
    }

    List<Player> selectPlayers(String name, String nationality, String club, String position, Integer minOverall,
            Integer maxAge, boolean brazilianClubsOnly) {
        Set<String> pos = position == null || position.isBlank() ? null : positions(position);
        String nat = nationality == null || nationality.isBlank() ? null : TeamNames.fold(nationality);
        if (nat != null && (nat.equals("brazilian") || nat.equals("brasil") || nat.equals("brasileiro"))) nat = "brazil";
        String clubFold = club == null || club.isBlank() ? null : TeamNames.fold(club);
        String clubKey = clubFold == null ? null : teams.canonical(club);
        List<Player> out = new ArrayList<>();
        for (Player p : ds.players) {
            if (name != null && !name.isBlank() && !nameMatches(TeamNames.fold(p.name), name)) continue;
            if (nat != null && !TeamNames.fold(p.nationality).equals(nat)) continue;
            if (clubFold != null && !(TeamNames.fold(p.club).contains(clubFold) || clubKey.equals(p.clubTeamKey))) continue;
            if (pos != null && !pos.contains(p.position)) continue;
            if (minOverall != null && p.overall < minOverall) continue;
            if (maxAge != null && p.age > maxAge) continue;
            if (brazilianClubsOnly && p.clubTeamKey == null) continue;
            out.add(p);
        }
        return out;
    }

    String searchPlayers(String name, String nationality, String club, String position, Integer minOverall,
            Integer maxAge, boolean brazilianClubsOnly, String sortBy, Integer limit) {
        List<Player> ps = selectPlayers(name, nationality, club, position, minOverall, maxAge, brazilianClubsOnly);
        String sort = sortBy == null || sortBy.isBlank() ? "overall" : sortBy.trim().toLowerCase(Locale.ROOT);
        Comparator<Player> cmp = switch (sort) {
            case "overall" -> Comparator.comparingInt(p -> -p.overall);
            case "potential" -> Comparator.comparingInt(p -> -p.potential);
            case "age" -> Comparator.comparingInt(p -> p.age);
            case "name" -> Comparator.comparing(p -> p.name);
            default -> throw new IllegalArgumentException("sort_by must be one of: overall, potential, age, name.");
        };
        ps.sort(cmp.thenComparing(p -> p.name));
        int max = clamp(limit, 20, 200);
        List<String> crit = new ArrayList<>();
        if (name != null && !name.isBlank()) crit.add("name \"" + name.trim() + "\"");
        if (nationality != null && !nationality.isBlank()) crit.add("nationality " + nationality.trim());
        if (club != null && !club.isBlank()) crit.add("club " + club.trim());
        if (position != null && !position.isBlank()) crit.add("position " + position.trim());
        if (minOverall != null) crit.add("overall >= " + minOverall);
        if (maxAge != null) crit.add("age <= " + maxAge);
        if (brazilianClubsOnly) crit.add("Brazilian clubs only");
        StringBuilder sb = new StringBuilder();
        sb.append("Players (").append(crit.isEmpty() ? "all" : String.join(", ", crit)).append("), sorted by ").append(sort)
                .append(": ").append(ps.size()).append(" found");
        if (ps.isEmpty()) {
            sb.append(".\nNo players in the FIFA dataset satisfy these criteria.");
            if (club != null && !club.isBlank()) {
                sb.append(" Brazilian clubs present in the FIFA data: ").append(brazilianClubList()).append('.');
            }
            return sb.toString();
        }
        sb.append(ps.size() > max ? " (showing top " + max + ")" : "").append('\n');
        int i = 1;
        for (Player p : ps.subList(0, Math.min(max, ps.size()))) sb.append(i++).append(". ").append(playerLine(p)).append('\n');
        if (ps.size() > max) sb.append("... (").append(ps.size() - max).append(" more players in dataset)\n");
        return sb.toString().trim();
    }

    private String brazilianClubList() {
        return ds.players.stream().filter(p -> p.clubTeamKey != null).map(p -> p.club).distinct().sorted()
                .collect(Collectors.joining(", "));
    }

    String playerDetails(String name, Long id) {
        List<Player> ps;
        if (id != null) ps = ds.players.stream().filter(p -> p.id == id).collect(Collectors.toList());
        else if (name != null && !name.isBlank()) {
            ps = selectPlayers(name, null, null, null, null, null, false);
            String f = TeamNames.fold(name);
            ps.sort(Comparator.comparing((Player p) -> !TeamNames.fold(p.name).equals(f)).thenComparingInt(p -> -p.overall));
        } else throw new IllegalArgumentException("Provide a player name or id.");
        if (ps.isEmpty()) return "No player matching " + (id != null ? "id " + id : "\"" + name + "\"") + " in the FIFA dataset.";
        Player p = ps.get(0);
        StringBuilder sb = new StringBuilder();
        sb.append(p.name).append(" (FIFA id ").append(p.id).append(")\n");
        sb.append("- Nationality: ").append(p.nationality).append(", Age: ").append(p.age).append('\n');
        sb.append("- Club: ").append(p.club.isBlank() ? "(no club)" : p.club).append(", Position: ")
                .append(p.position.isBlank() ? "n/a" : p.position).append(", Jersey: ").append(p.jersey.isBlank() ? "n/a" : p.jersey).append('\n');
        sb.append("- Overall: ").append(p.overall).append(", Potential: ").append(p.potential).append('\n');
        sb.append("- Height: ").append(p.height).append(", Weight: ").append(p.weight).append(", Preferred foot: ").append(p.preferredFoot).append('\n');
        sb.append("- Value: ").append(p.value).append(", Wage: ").append(p.wage).append('\n');
        List<String> attrs = new ArrayList<>();
        for (String a : List.of("Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling", "BallControl",
                "Acceleration", "SprintSpeed", "ShotPower", "Stamina", "Strength", "LongShots", "Vision", "Penalties",
                "StandingTackle", "GKReflexes")) {
            String v = p.raw.get(a);
            if (v != null && !v.isBlank()) attrs.add(a + " " + v);
        }
        if (!attrs.isEmpty()) sb.append("- Attributes: ").append(String.join(", ", attrs)).append('\n');
        if (p.clubTeamKey != null) {
            List<Match> ms = ds.matches.stream().filter(m -> m.primary && m.involves(p.clubTeamKey)).collect(Collectors.toList());
            sb.append("- Club in match data: ").append(name(p.clubTeamKey)).append(" — ")
                    .append(shortRec(record(ms, Set.of(p.clubTeamKey)))).append(" (use team_profile for details)\n");
        }
        if (ps.size() > 1) {
            sb.append("Other matching players: ").append(ps.stream().skip(1).limit(10)
                    .map(o -> o.name + " (" + o.overall + ", " + (o.club.isBlank() ? "no club" : o.club) + ")")
                    .collect(Collectors.joining("; ")));
            if (ps.size() > 11) sb.append("; ... ").append(ps.size() - 11).append(" more");
        }
        return sb.toString().trim();
    }

    String playersByClub(String nationality, boolean brazilianClubsOnly, Integer limit) {
        List<Player> ps = selectPlayers(null, nationality, null, null, null, null, brazilianClubsOnly);
        Map<String, List<Player>> byClub = ps.stream().filter(p -> !p.club.isBlank()).collect(Collectors.groupingBy(p -> p.club));
        int max = clamp(limit, 25, 200);
        StringBuilder sb = new StringBuilder();
        sb.append(nationality == null || nationality.isBlank() ? "Players" : nationality.trim() + " players").append(" by club")
                .append(brazilianClubsOnly ? " (Brazilian clubs only)" : "").append(": ").append(byClub.size()).append(" clubs\n");
        if (byClub.isEmpty()) return sb.append("No players in the FIFA dataset satisfy these criteria.").toString();
        byClub.entrySet().stream().sorted(Comparator.comparingInt((Map.Entry<String, List<Player>> e) -> -e.getValue().size())
                .thenComparing(Map.Entry::getKey)).limit(max).forEach(e -> {
            List<Player> l = e.getValue();
            Player best = l.stream().max(Comparator.comparingInt(p -> p.overall)).get();
            sb.append("- ").append(e.getKey()).append(": ").append(l.size()).append(" players (avg rating: ")
                    .append(String.format(Locale.ROOT, "%.1f", l.stream().mapToInt(p -> p.overall).average().orElse(0)))
                    .append("), best: ").append(best.name).append(" (").append(best.overall).append(")\n");
        });
        if (byClub.size() > max) sb.append("... (").append(byClub.size() - max).append(" more clubs)\n");
        return sb.toString().trim();
    }

    // ------------------------------------------------------------------ dataset info

    String datasetInfo() {
        StringBuilder sb = new StringBuilder("Brazilian soccer dataset:\n");
        ds.rowCounts.forEach((file, n) -> sb.append("- ").append(file).append(": ").append(n)
                .append(file.equals(DataStore.F_FIFA) ? " players" : " matches").append('\n'));
        sb.append("Competitions (after removing duplicate coverage between files):\n");
        for (String c : DataStore.COMPETITIONS) {
            List<Match> ms = ds.matches.stream().filter(m -> m.primary && m.competition.equals(c)).collect(Collectors.toList());
            if (ms.isEmpty()) continue;
            TreeSet<Integer> s = ms.stream().map(m -> m.season).collect(Collectors.toCollection(TreeSet::new));
            sb.append("- ").append(c).append(": ").append(ms.size()).append(" matches, seasons ").append(s.first()).append('-')
                    .append(s.last()).append('\n');
        }
        sb.append("Teams: ").append(teams.knownTeams().size()).append(" distinct clubs after name normalisation\n");
        sb.append("Players: ").append(ds.players.size()).append(" (").append(ds.players.stream()
                .filter(p -> "Brazil".equals(p.nationality)).count()).append(" Brazilian); Brazilian clubs in FIFA data: ")
                .append(brazilianClubList()).append('\n');
        sb.append("Notes: goal scorers are not in the data, so top-scorer questions cannot be answered; standings are "
                + "calculated from results; corner/shot statistics exist only in ").append(DataStore.F_EXTENDED).append('.');
        return sb.toString();
    }
}
