package com.braziliansoccer.mcp.loader;

import com.braziliansoccer.mcp.model.Match;
import com.braziliansoccer.mcp.service.TeamNameNormalizer;
import com.opencsv.CSVReaderHeaderAware;
import com.opencsv.exceptions.CsvValidationException;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class MatchLoader {
    private final String dataDir;
    private final TeamNameNormalizer normalizer = new TeamNameNormalizer();

    public MatchLoader(String dataDir) {
        this.dataDir = dataDir;
    }

    public List<Match> loadAll() {
        List<Match> matches = new ArrayList<>();
        matches.addAll(loadBrasileirao());
        matches.addAll(loadCopa());
        matches.addAll(loadLibertadores());
        matches.addAll(loadBRFootball());
        matches.addAll(loadHistorico());
        return matches;
    }

    private int parseGoals(String s) {
        if (s == null || s.isBlank() || s.equalsIgnoreCase("NaN")) return 0;
        try {
            return (int) Double.parseDouble(s.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private int parseSeason(String s) {
        if (s == null || s.isBlank()) return 0;
        try {
            return (int) Double.parseDouble(s.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private List<Match> loadBrasileirao() {
        List<Match> matches = new ArrayList<>();
        File f = new File(dataDir + "Brasileirao_Matches.csv");
        if (!f.exists()) return matches;
        try (CSVReaderHeaderAware reader = new CSVReaderHeaderAware(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            Map<String, String> row;
            while ((row = reader.readMap()) != null) {
                String home = normalizer.normalize(row.getOrDefault("home_team", ""));
                String away = normalizer.normalize(row.getOrDefault("away_team", ""));
                matches.add(new Match("Brasileirao",
                    row.getOrDefault("datetime", ""), home, away,
                    parseGoals(row.get("home_goal")), parseGoals(row.get("away_goal")),
                    parseSeason(row.get("season")), row.getOrDefault("round", ""), null));
            }
        } catch (Exception e) { System.err.println("Error loading Brasileirao: " + e.getMessage()); }
        return matches;
    }

    private List<Match> loadCopa() {
        List<Match> matches = new ArrayList<>();
        File f = new File(dataDir + "Brazilian_Cup_Matches.csv");
        if (!f.exists()) return matches;
        try (CSVReaderHeaderAware reader = new CSVReaderHeaderAware(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            Map<String, String> row;
            while ((row = reader.readMap()) != null) {
                String home = normalizer.normalize(row.getOrDefault("home_team", ""));
                String away = normalizer.normalize(row.getOrDefault("away_team", ""));
                matches.add(new Match("Copa do Brasil",
                    row.getOrDefault("datetime", ""), home, away,
                    parseGoals(row.get("home_goal")), parseGoals(row.get("away_goal")),
                    parseSeason(row.get("season")), row.getOrDefault("round", ""), null));
            }
        } catch (Exception e) { System.err.println("Error loading Copa: " + e.getMessage()); }
        return matches;
    }

    private List<Match> loadLibertadores() {
        List<Match> matches = new ArrayList<>();
        File f = new File(dataDir + "Libertadores_Matches.csv");
        if (!f.exists()) return matches;
        try (CSVReaderHeaderAware reader = new CSVReaderHeaderAware(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            Map<String, String> row;
            while ((row = reader.readMap()) != null) {
                String home = normalizer.normalize(row.getOrDefault("home_team", ""));
                String away = normalizer.normalize(row.getOrDefault("away_team", ""));
                matches.add(new Match("Libertadores",
                    row.getOrDefault("datetime", ""), home, away,
                    parseGoals(row.get("home_goal")), parseGoals(row.get("away_goal")),
                    parseSeason(row.get("season")), "", row.getOrDefault("stage", null)));
            }
        } catch (Exception e) { System.err.println("Error loading Libertadores: " + e.getMessage()); }
        return matches;
    }

    private List<Match> loadBRFootball() {
        List<Match> matches = new ArrayList<>();
        File f = new File(dataDir + "BR-Football-Dataset.csv");
        if (!f.exists()) return matches;
        try (CSVReaderHeaderAware reader = new CSVReaderHeaderAware(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            Map<String, String> row;
            while ((row = reader.readMap()) != null) {
                String home = normalizer.normalize(row.getOrDefault("home", ""));
                String away = normalizer.normalize(row.getOrDefault("away", ""));
                matches.add(new Match("BR-Football",
                    row.getOrDefault("date", ""), home, away,
                    parseGoals(row.get("home_goal")), parseGoals(row.get("away_goal")),
                    0, "", null));
            }
        } catch (Exception e) { System.err.println("Error loading BR-Football: " + e.getMessage()); }
        return matches;
    }

    private List<Match> loadHistorico() {
        List<Match> matches = new ArrayList<>();
        File f = new File(dataDir + "novo_campeonato_brasileiro.csv");
        if (!f.exists()) return matches;
        try (CSVReaderHeaderAware reader = new CSVReaderHeaderAware(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            Map<String, String> row;
            while ((row = reader.readMap()) != null) {
                String home = normalizer.normalize(row.getOrDefault("Equipe_mandante", ""));
                String away = normalizer.normalize(row.getOrDefault("Equipe_visitante", ""));
                matches.add(new Match("Historico",
                    row.getOrDefault("Data", ""), home, away,
                    parseGoals(row.get("Gols_mandante")), parseGoals(row.get("Gols_visitante")),
                    parseSeason(row.get("Ano")), row.getOrDefault("Rodada", ""), null));
            }
        } catch (Exception e) { System.err.println("Error loading Historico: " + e.getMessage()); }
        return matches;
    }
}
