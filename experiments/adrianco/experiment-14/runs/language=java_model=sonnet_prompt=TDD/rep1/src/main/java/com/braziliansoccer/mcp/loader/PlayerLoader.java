package com.braziliansoccer.mcp.loader;

import com.braziliansoccer.mcp.model.Player;
import com.opencsv.CSVReaderHeaderAware;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class PlayerLoader {
    private final String dataDir;

    public PlayerLoader(String dataDir) {
        this.dataDir = dataDir;
    }

    public List<Player> loadAll() {
        List<Player> players = new ArrayList<>();
        File f = new File(dataDir + "fifa_data.csv");
        if (!f.exists()) return players;
        try {
            // Read entire file to strip BOM
            byte[] bytes = java.nio.file.Files.readAllBytes(f.toPath());
            String content = new String(bytes, StandardCharsets.UTF_8);
            if (content.startsWith("﻿")) content = content.substring(1);

            try (CSVReaderHeaderAware reader = new CSVReaderHeaderAware(new StringReader(content))) {
                Map<String, String> row;
                while ((row = reader.readMap()) != null) {
                    try {
                        String id = row.getOrDefault("ID", "");
                        String name = row.getOrDefault("Name", "");
                        int age = parseInt(row.get("Age"));
                        String nationality = row.getOrDefault("Nationality", "");
                        int overall = parseInt(row.get("Overall"));
                        int potential = parseInt(row.get("Potential"));
                        String club = row.getOrDefault("Club", "");
                        String position = row.getOrDefault("Position", "");
                        players.add(new Player(id, name, age, nationality, club, position, overall, potential));
                    } catch (Exception e) { /* skip bad rows */ }
                }
            }
        } catch (Exception e) { System.err.println("Error loading players: " + e.getMessage()); }
        return players;
    }

    private int parseInt(String s) {
        if (s == null || s.isBlank()) return 0;
        try { return Integer.parseInt(s.trim()); } catch (NumberFormatException e) { return 0; }
    }
}
