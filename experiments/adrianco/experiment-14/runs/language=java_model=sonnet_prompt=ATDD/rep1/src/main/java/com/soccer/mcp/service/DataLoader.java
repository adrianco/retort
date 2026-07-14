package com.soccer.mcp.service;

import com.soccer.mcp.model.Match;
import com.soccer.mcp.model.Player;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.io.input.BOMInputStream;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Logger;

/**
 * Loads all CSV data files and returns unified Match and Player lists.
 */
public class DataLoader {

    private static final Logger LOG = Logger.getLogger(DataLoader.class.getName());

    private static final DateTimeFormatter FMT_ISO = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final DateTimeFormatter FMT_ISO_DATETIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final DateTimeFormatter FMT_BR = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    private final String dataPath;
    private final TeamNameNormalizer normalizer;

    public DataLoader(String dataPath) {
        this.dataPath = dataPath;
        this.normalizer = new TeamNameNormalizer();
    }

    public List<Match> loadAllMatches() {
        List<Match> all = new ArrayList<>();
        all.addAll(loadBrasileirao());
        all.addAll(loadNovoCampeonato());
        all.addAll(loadBrazilianCup());
        all.addAll(loadLibertadores());
        all.addAll(loadBRFootballDataset());
        return all;
    }

    public List<Player> loadPlayers() {
        return loadFifaData();
    }

    // ---- Brasileirao_Matches.csv ----
    // headers: datetime, home_team, home_team_state, away_team, away_team_state, home_goal, away_goal, season, round
    private List<Match> loadBrasileirao() {
        List<Match> matches = new ArrayList<>();
        File file = new File(dataPath, "Brasileirao_Matches.csv");
        if (!file.exists()) {
            LOG.warning("File not found: " + file);
            return matches;
        }
        try (Reader reader = new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder()
                     .setHeader()
                     .setSkipHeaderRecord(true)
                     .setIgnoreHeaderCase(true)
                     .setTrim(true)
                     .build()
                     .parse(reader)) {
            for (CSVRecord record : parser) {
                try {
                    String dateStr = getField(record, "datetime");
                    LocalDate date = parseDate(dateStr);
                    String homeTeam = normalizer.normalize(getField(record, "home_team"));
                    String awayTeam = normalizer.normalize(getField(record, "away_team"));
                    int homeGoal = parseIntSafe(getField(record, "home_goal"));
                    int awayGoal = parseIntSafe(getField(record, "away_goal"));
                    int season = parseIntSafe(getField(record, "season"));
                    String round = getField(record, "round");
                    matches.add(new Match("brasileirao", date, homeTeam, awayTeam,
                            homeGoal, awayGoal, season, round, null, null));
                } catch (Exception e) {
                    LOG.fine("Skipping Brasileirao record: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            LOG.warning("Error loading Brasileirao: " + e.getMessage());
        }
        LOG.info("Loaded " + matches.size() + " Brasileirao matches");
        return matches;
    }

    // ---- novo_campeonato_brasileiro.csv ----
    // headers: ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,
    //          Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
    // Note: Brasileirao_Matches.csv covers 2012-2022, so we only load 2003-2011 from this file
    // to avoid duplicates.
    private static final int BRASILEIRAO_MATCHES_START_YEAR = 2012;

    private List<Match> loadNovoCampeonato() {
        List<Match> matches = new ArrayList<>();
        File file = new File(dataPath, "novo_campeonato_brasileiro.csv");
        if (!file.exists()) {
            LOG.warning("File not found: " + file);
            return matches;
        }
        try (Reader reader = new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder()
                     .setHeader()
                     .setSkipHeaderRecord(true)
                     .setIgnoreHeaderCase(true)
                     .setTrim(true)
                     .build()
                     .parse(reader)) {
            for (CSVRecord record : parser) {
                try {
                    int season = parseIntSafe(getField(record, "Ano"));
                    // Only load seasons not covered by Brasileirao_Matches.csv
                    if (season >= BRASILEIRAO_MATCHES_START_YEAR) continue;
                    String dateStr = getField(record, "Data");
                    LocalDate date = parseDate(dateStr);
                    String homeTeam = normalizer.normalize(getField(record, "Equipe_mandante"));
                    String awayTeam = normalizer.normalize(getField(record, "Equipe_visitante"));
                    int homeGoal = parseIntSafe(getField(record, "Gols_mandante"));
                    int awayGoal = parseIntSafe(getField(record, "Gols_visitante"));
                    String round = getField(record, "Rodada");
                    String arena = getField(record, "Arena");
                    matches.add(new Match("brasileirao", date, homeTeam, awayTeam,
                            homeGoal, awayGoal, season, round, null, arena));
                } catch (Exception e) {
                    LOG.fine("Skipping NovoCampeonato record: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            LOG.warning("Error loading NovoCampeonato: " + e.getMessage());
        }
        LOG.info("Loaded " + matches.size() + " NovoCampeonato matches (2003-2011 only)");
        return matches;
    }

    // ---- Brazilian_Cup_Matches.csv ----
    // headers: round,datetime,home_team,away_team,home_goal,away_goal,season
    private List<Match> loadBrazilianCup() {
        List<Match> matches = new ArrayList<>();
        File file = new File(dataPath, "Brazilian_Cup_Matches.csv");
        if (!file.exists()) {
            LOG.warning("File not found: " + file);
            return matches;
        }
        try (Reader reader = new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder()
                     .setHeader()
                     .setSkipHeaderRecord(true)
                     .setIgnoreHeaderCase(true)
                     .setTrim(true)
                     .build()
                     .parse(reader)) {
            for (CSVRecord record : parser) {
                try {
                    String dateStr = getField(record, "datetime");
                    LocalDate date = parseDate(dateStr);
                    String homeTeam = normalizer.normalize(getField(record, "home_team"));
                    String awayTeam = normalizer.normalize(getField(record, "away_team"));
                    int homeGoal = parseIntSafe(getField(record, "home_goal"));
                    int awayGoal = parseIntSafe(getField(record, "away_goal"));
                    int season = parseIntSafe(getField(record, "season"));
                    String round = getField(record, "round");
                    matches.add(new Match("copa_do_brasil", date, homeTeam, awayTeam,
                            homeGoal, awayGoal, season, round, null, null));
                } catch (Exception e) {
                    LOG.fine("Skipping BrazilianCup record: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            LOG.warning("Error loading BrazilianCup: " + e.getMessage());
        }
        LOG.info("Loaded " + matches.size() + " BrazilianCup matches");
        return matches;
    }

    // ---- Libertadores_Matches.csv ----
    // headers: datetime,home_team,away_team,home_goal,away_goal,season,stage
    private List<Match> loadLibertadores() {
        List<Match> matches = new ArrayList<>();
        File file = new File(dataPath, "Libertadores_Matches.csv");
        if (!file.exists()) {
            LOG.warning("File not found: " + file);
            return matches;
        }
        try (Reader reader = new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder()
                     .setHeader()
                     .setSkipHeaderRecord(true)
                     .setIgnoreHeaderCase(true)
                     .setTrim(true)
                     .build()
                     .parse(reader)) {
            for (CSVRecord record : parser) {
                try {
                    String dateStr = getField(record, "datetime");
                    LocalDate date = parseDate(dateStr);
                    String homeTeam = normalizer.normalize(getField(record, "home_team"));
                    String awayTeam = normalizer.normalize(getField(record, "away_team"));
                    int homeGoal = parseIntSafe(getField(record, "home_goal"));
                    int awayGoal = parseIntSafe(getField(record, "away_goal"));
                    int season = parseIntSafe(getField(record, "season"));
                    String stage = getField(record, "stage");
                    matches.add(new Match("libertadores", date, homeTeam, awayTeam,
                            homeGoal, awayGoal, season, null, stage, null));
                } catch (Exception e) {
                    LOG.fine("Skipping Libertadores record: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            LOG.warning("Error loading Libertadores: " + e.getMessage());
        }
        LOG.info("Loaded " + matches.size() + " Libertadores matches");
        return matches;
    }

    // ---- BR-Football-Dataset.csv ----
    // headers: tournament,home,home_goal,away_goal,away,home_corner,away_corner,...,date,...
    private List<Match> loadBRFootballDataset() {
        List<Match> matches = new ArrayList<>();
        File file = new File(dataPath, "BR-Football-Dataset.csv");
        if (!file.exists()) {
            LOG.warning("File not found: " + file);
            return matches;
        }
        try (Reader reader = new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder()
                     .setHeader()
                     .setSkipHeaderRecord(true)
                     .setIgnoreHeaderCase(true)
                     .setTrim(true)
                     .build()
                     .parse(reader)) {
            for (CSVRecord record : parser) {
                try {
                    String tournament = getField(record, "tournament");
                    String competition = mapTournamentName(tournament);
                    String dateStr = getField(record, "date");
                    LocalDate date = parseDate(dateStr);
                    String homeTeam = normalizer.normalize(getField(record, "home"));
                    String awayTeam = normalizer.normalize(getField(record, "away"));
                    int homeGoal = parseDoubleSafe(getField(record, "home_goal"));
                    int awayGoal = parseDoubleSafe(getField(record, "away_goal"));
                    Integer season = date != null ? date.getYear() : null;
                    matches.add(new Match(competition, date, homeTeam, awayTeam,
                            homeGoal, awayGoal, season, null, null, null));
                } catch (Exception e) {
                    LOG.fine("Skipping BR-Football record: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            LOG.warning("Error loading BR-Football-Dataset: " + e.getMessage());
        }
        LOG.info("Loaded " + matches.size() + " BR-Football-Dataset matches");
        return matches;
    }

    private String mapTournamentName(String tournament) {
        if (tournament == null) return "unknown";
        String lower = tournament.toLowerCase().trim();
        if (lower.contains("brasileiro") || lower.contains("brasileirao")) return "brasileirao";
        // Note: "Serie A" from BR-Football-Dataset is mapped to br_serie_a (not brasileirao)
        // to avoid duplicating data from Brasileirao_Matches.csv
        if (lower.equals("serie a")) return "br_serie_a";
        if (lower.equals("serie b")) return "brasileirao_b";
        if (lower.equals("serie c")) return "brasileirao_c";
        if (lower.contains("copa do brasil") || lower.contains("copa brasil")) return "copa_do_brasil";
        if (lower.contains("libertadores")) return "libertadores";
        return lower.replace(" ", "_");
    }

    // ---- fifa_data.csv ----
    // BOM file, first column is empty index, then: ID,Name,Age,...
    private List<Player> loadFifaData() {
        List<Player> players = new ArrayList<>();
        File file = new File(dataPath, "fifa_data.csv");
        if (!file.exists()) {
            LOG.warning("File not found: " + file);
            return players;
        }
        try (BOMInputStream bis = new BOMInputStream(new FileInputStream(file));
             Reader reader = new InputStreamReader(bis, StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder()
                     .setHeader()
                     .setSkipHeaderRecord(true)
                     .setIgnoreHeaderCase(true)
                     .setTrim(true)
                     .setAllowMissingColumnNames(true)
                     .build()
                     .parse(reader)) {
            for (CSVRecord record : parser) {
                try {
                    String name = getField(record, "Name");
                    if (name == null || name.isEmpty()) continue;
                    int age = parseIntSafe(getField(record, "Age"));
                    String nationality = getField(record, "Nationality");
                    int overall = parseIntSafe(getField(record, "Overall"));
                    int potential = parseIntSafe(getField(record, "Potential"));
                    String club = getField(record, "Club");
                    String position = getField(record, "Position");
                    players.add(new Player(name, age, nationality, overall, potential, club, position));
                } catch (Exception e) {
                    LOG.fine("Skipping FIFA record: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            LOG.warning("Error loading FIFA data: " + e.getMessage());
        }
        LOG.info("Loaded " + players.size() + " players");
        return players;
    }

    private String getField(CSVRecord record, String name) {
        try {
            String val = record.get(name);
            return val != null ? val.trim() : "";
        } catch (Exception e) {
            return "";
        }
    }

    private LocalDate parseDate(String dateStr) {
        if (dateStr == null || dateStr.isEmpty()) return null;
        // Try ISO datetime first: 2012-05-19 18:30:00
        try {
            return LocalDate.parse(dateStr.substring(0, 10), FMT_ISO);
        } catch (Exception ignored) {}
        // Try Brazilian format: 29/03/2003
        try {
            return LocalDate.parse(dateStr, FMT_BR);
        } catch (DateTimeParseException ignored) {}
        // Try ISO date: 2023-09-24
        try {
            return LocalDate.parse(dateStr, FMT_ISO);
        } catch (DateTimeParseException ignored) {}
        return null;
    }

    private int parseIntSafe(String s) {
        if (s == null || s.isEmpty()) return 0;
        try {
            return Integer.parseInt(s.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private int parseDoubleSafe(String s) {
        if (s == null || s.isEmpty()) return 0;
        try {
            return (int) Double.parseDouble(s.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }
}
