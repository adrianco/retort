package com.braziliansoccer.mcp;

import java.io.IOException;
import java.nio.file.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.*;

/** Immutable in-memory projection of all six supplied datasets. */
public final class SoccerRepository {
    private final List<Match> matches;
    private final List<Player> players;
    private SoccerRepository(List<Match> matches, List<Player> players) { this.matches = List.copyOf(matches); this.players = List.copyOf(players); }
    public static SoccerRepository load(Path dataDirectory) throws IOException {
        List<Match> matches = new ArrayList<>();
        matches.addAll(loadStandard(dataDirectory.resolve("Brasileirao_Matches.csv"), "Brasileirão", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round", null));
        matches.addAll(loadStandard(dataDirectory.resolve("Brazilian_Cup_Matches.csv"), "Copa do Brasil", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round", null));
        matches.addAll(loadStandard(dataDirectory.resolve("Libertadores_Matches.csv"), "Libertadores", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season", null, "stage"));
        matches.addAll(loadStandard(dataDirectory.resolve("BR-Football-Dataset.csv"), null, "date", "home", "away", "home_goal", "away_goal", null, null, null));
        for (Map<String,String> row : CsvReader.read(dataDirectory.resolve("novo_campeonato_brasileiro.csv"))) matches.add(new Match("Brasileirão Histórico", date(row.get("Data")), row.get("Equipe_mandante"), row.get("Equipe_visitante"), number(row.get("Gols_mandante")), number(row.get("Gols_visitante")), integer(row.get("Ano")), row.get("Rodada"), null, row.get("Arena")));
        List<Player> players = CsvReader.read(dataDirectory.resolve("fifa_data.csv")).stream().map(r -> new Player(r.get("ID"), r.get("Name"), integer(r.get("Age")), r.get("Nationality"), integer(r.get("Overall")), integer(r.get("Potential")), r.get("Club"), r.get("Position"))).toList();
        return new SoccerRepository(matches, players);
    }
    private static List<Match> loadStandard(Path file, String fixedCompetition, String dateColumn, String home, String away, String hg, String ag, String season, String round, String stage) throws IOException {
        return CsvReader.read(file).stream().map(r -> new Match(fixedCompetition == null ? r.get("tournament") : fixedCompetition, date(r.get(dateColumn)), r.get(home), r.get(away), number(r.get(hg)), number(r.get(ag)), season == null ? year(r.get(dateColumn)) : integer(r.get(season)), round == null ? null : r.get(round), stage == null ? null : r.get(stage), null)).toList();
    }
    static LocalDate date(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String date = raw.trim().replace('T', ' ').split(" ")[0];
        for (DateTimeFormatter formatter : List.of(DateTimeFormatter.ISO_LOCAL_DATE, DateTimeFormatter.ofPattern("d/M/uuuu"))) try { return LocalDate.parse(date, formatter); } catch (RuntimeException ignored) { }
        return null;
    }
    static Integer integer(String raw) { try { return raw == null || raw.isBlank() ? null : (int) Double.parseDouble(raw.trim()); } catch (NumberFormatException e) { return null; } }
    static int number(String raw) { Integer value = integer(raw); return value == null ? 0 : value; }
    static Integer year(String raw) { LocalDate date = date(raw); return date == null ? null : date.getYear(); }
    public List<Match> matches() { return matches; }
    public List<Player> players() { return players; }
    public List<Match> findMatches(MatchFilter filter) {
        return matches.stream().filter(m -> (filter.team() == null || Normalizer.matches(m.homeTeam(), filter.team()) || Normalizer.matches(m.awayTeam(), filter.team()))
                && (filter.opponent() == null || (Normalizer.matches(m.homeTeam(), filter.opponent()) || Normalizer.matches(m.awayTeam(), filter.opponent())))
                && (filter.competition() == null || Normalizer.matches(m.competition(), filter.competition()))
                && (filter.season() == null || filter.season().equals(m.season()))
                && (filter.from() == null || m.date() != null && !m.date().isBefore(filter.from())) && (filter.to() == null || m.date() != null && !m.date().isAfter(filter.to()))
                && (filter.roundOrStage() == null || Normalizer.matches(String.valueOf(m.round()), filter.roundOrStage()) || Normalizer.matches(String.valueOf(m.stage()), filter.roundOrStage())))
                .sorted(Comparator.comparing(Match::date, Comparator.nullsLast(Comparator.reverseOrder()))).limit(Math.max(1, filter.limit())).toList();
    }
    public List<Player> findPlayers(String name, String nationality, String club, String position, int limit) {
        return players.stream().filter(p -> (name == null || Normalizer.matches(p.name(), name)) && (nationality == null || Normalizer.matches(p.nationality(), nationality)) && (club == null || Normalizer.matches(p.club(), club)) && (position == null || Normalizer.matches(p.position(), position))).sorted(Comparator.comparing(Player::overall, Comparator.nullsLast(Comparator.reverseOrder()))).limit(Math.max(1, limit)).toList();
    }
}
