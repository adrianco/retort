package com.braziliansoccer.mcp.tools;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.data.Match;
import com.braziliansoccer.mcp.data.Player;
import com.braziliansoccer.mcp.data.TeamNormalizer;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.*;
import java.util.stream.Collectors;

public class PlayerTools {

    private final DataLoader loader;

    public PlayerTools(DataLoader loader) {
        this.loader = loader;
    }

    /**
     * search_players: Search players by name, nationality, club, position.
     * Params: name (optional), nationality (optional), club (optional), position (optional),
     *         min_overall (optional), max_results (optional, default 20), sort_by (optional: "overall","name")
     */
    public String searchPlayers(JsonNode params) {
        String name = getStr(params, "name");
        String nationality = getStr(params, "nationality");
        String club = getStr(params, "club");
        String position = getStr(params, "position");
        int minOverall = getInt(params, "min_overall");
        int maxResults = params.has("max_results") ? params.get("max_results").asInt(20) : 20;
        String sortBy = getStr(params, "sort_by");

        List<Player> players = loader.getAllPlayers().stream()
            .filter(p -> name.isEmpty() || p.name.toLowerCase().contains(name.toLowerCase()))
            .filter(p -> nationality.isEmpty() || p.nationality.toLowerCase().contains(nationality.toLowerCase()))
            .filter(p -> club.isEmpty() || p.club.toLowerCase().contains(club.toLowerCase()))
            .filter(p -> position.isEmpty() || p.position.toLowerCase().contains(position.toLowerCase()))
            .filter(p -> minOverall == 0 || p.overall >= minOverall)
            .collect(Collectors.toList());

        if (players.isEmpty()) {
            return "No players found for the given criteria.";
        }

        // Sort
        if ("name".equals(sortBy)) {
            players.sort(Comparator.comparing(p -> p.name));
        } else {
            players.sort(Comparator.comparingInt((Player p) -> p.overall).reversed());
        }

        int total = players.size();
        players = players.stream().limit(maxResults).collect(Collectors.toList());

        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(total).append(" player(s)");
        if (!name.isEmpty()) sb.append(" matching name '").append(name).append("'");
        if (!nationality.isEmpty()) sb.append(", nationality '").append(nationality).append("'");
        if (!club.isEmpty()) sb.append(", club '").append(club).append("'");
        if (!position.isEmpty()) sb.append(", position '").append(position).append("'");
        if (total > maxResults) sb.append(" (showing top ").append(maxResults).append(")");
        sb.append(":\n\n");

        for (int i = 0; i < players.size(); i++) {
            Player p = players.get(i);
            sb.append(i + 1).append(". ").append(p.name)
                .append(" | Overall: ").append(p.overall)
                .append(" | Potential: ").append(p.potential)
                .append(" | Position: ").append(p.position)
                .append(" | Club: ").append(p.club)
                .append(" | Nationality: ").append(p.nationality)
                .append(" | Age: ").append(p.age);
            if (!p.value.isEmpty()) sb.append(" | Value: ").append(p.value);
            sb.append("\n");
        }
        return sb.toString().trim();
    }

    /**
     * player_profile: Get detailed profile for a player by name.
     * Params: name (required)
     */
    public String playerProfile(JsonNode params) {
        String name = getStr(params, "name");
        if (name.isEmpty()) return "Error: name parameter is required.";

        List<Player> matches = loader.getAllPlayers().stream()
            .filter(p -> p.name.toLowerCase().contains(name.toLowerCase()))
            .sorted(Comparator.comparingInt((Player p) -> p.overall).reversed())
            .limit(5)
            .collect(Collectors.toList());

        if (matches.isEmpty()) {
            return "No player found matching: " + name;
        }

        StringBuilder sb = new StringBuilder();
        for (Player p : matches) {
            sb.append("=== ").append(p.name).append(" ===\n");
            sb.append("  Nationality: ").append(p.nationality).append("\n");
            sb.append("  Age: ").append(p.age).append("\n");
            sb.append("  Club: ").append(p.club).append("\n");
            sb.append("  Position: ").append(p.position).append("\n");
            sb.append("  Overall: ").append(p.overall)
                .append(" | Potential: ").append(p.potential).append("\n");
            sb.append("  Height: ").append(p.height)
                .append(" | Weight: ").append(p.weight).append("\n");
            sb.append("  Value: ").append(p.value)
                .append(" | Wage: ").append(p.wage).append("\n");
            sb.append("  Preferred Foot: ").append(p.preferredFoot).append("\n");
            sb.append("  Key Stats:\n");
            sb.append("    Pace: ").append(p.pace)
                .append(" | Shooting: ").append(p.shooting)
                .append(" | Passing: ").append(p.passing).append("\n");
            sb.append("    Dribbling: ").append(p.dribbling)
                .append(" | Defending: ").append(p.defending).append("\n");
            sb.append("\n");
        }
        return sb.toString().trim();
    }

    /**
     * team_players: Get players at a specific club with match history cross-reference.
     * Params: club (required), min_overall (optional), sort_by (optional)
     */
    public String teamPlayers(JsonNode params) {
        String club = getStr(params, "club");
        if (club.isEmpty()) return "Error: club parameter is required.";
        int minOverall = getInt(params, "min_overall");

        List<Player> players = loader.getAllPlayers().stream()
            .filter(p -> p.club.toLowerCase().contains(club.toLowerCase()))
            .filter(p -> minOverall == 0 || p.overall >= minOverall)
            .sorted(Comparator.comparingInt((Player p) -> p.overall).reversed())
            .collect(Collectors.toList());

        if (players.isEmpty()) {
            return "No players found at club: " + club;
        }

        // Count matches for the club
        long matchCount = loader.getAllMatches().stream()
            .filter(m -> TeamNormalizer.matches(m.homeTeam, club) || TeamNormalizer.matches(m.awayTeam, club))
            .count();

        StringBuilder sb = new StringBuilder();
        sb.append("Players at ").append(club).append(" (").append(players.size()).append(" players");
        if (matchCount > 0) sb.append(", ").append(matchCount).append(" matches in dataset");
        sb.append("):\n\n");

        // Group by position
        Map<String, List<Player>> byPos = new LinkedHashMap<>();
        for (Player p : players) {
            String pos = p.position.isEmpty() ? "Unknown" : p.position;
            byPos.computeIfAbsent(pos, k -> new ArrayList<>()).add(p);
        }

        for (Map.Entry<String, List<Player>> e : byPos.entrySet()) {
            sb.append("[").append(e.getKey()).append("]\n");
            for (Player p : e.getValue()) {
                sb.append("  ").append(p.name)
                    .append(" (Overall: ").append(p.overall)
                    .append(", Pot: ").append(p.potential)
                    .append(", Age: ").append(p.age)
                    .append(", ").append(p.nationality).append(")\n");
            }
        }

        double avgRating = players.stream().mapToInt(p -> p.overall).average().orElse(0);
        sb.append("\nAverage overall rating: ").append(String.format("%.1f", avgRating)).append("\n");
        return sb.toString().trim();
    }

    /**
     * top_players_by_nationality: List top players from a country.
     * Params: nationality (required), limit (optional)
     */
    public String topPlayersByNationality(JsonNode params) {
        String nationality = getStr(params, "nationality");
        if (nationality.isEmpty()) return "Error: nationality parameter is required.";
        int limit = params.has("limit") ? params.get("limit").asInt(20) : 20;

        List<Player> players = loader.getAllPlayers().stream()
            .filter(p -> p.nationality.toLowerCase().contains(nationality.toLowerCase()))
            .sorted(Comparator.comparingInt((Player p) -> p.overall).reversed())
            .limit(limit)
            .collect(Collectors.toList());

        long total = loader.getAllPlayers().stream()
            .filter(p -> p.nationality.toLowerCase().contains(nationality.toLowerCase()))
            .count();

        if (players.isEmpty()) {
            return "No players found with nationality: " + nationality;
        }

        StringBuilder sb = new StringBuilder();
        sb.append("Top ").append(players.size()).append(" players from ")
            .append(nationality).append(" (").append(total).append(" total in dataset):\n\n");

        for (int i = 0; i < players.size(); i++) {
            Player p = players.get(i);
            sb.append(i + 1).append(". ").append(p.name)
                .append(" (Overall: ").append(p.overall)
                .append(", Position: ").append(p.position)
                .append(", Club: ").append(p.club)
                .append(", Age: ").append(p.age).append(")\n");
        }
        return sb.toString().trim();
    }

    private String getStr(JsonNode n, String key) {
        return n != null && n.has(key) && !n.get(key).isNull() ? n.get(key).asText("").trim() : "";
    }

    private int getInt(JsonNode n, String key) {
        return n != null && n.has(key) && !n.get(key).isNull() ? n.get(key).asInt(0) : 0;
    }
}
