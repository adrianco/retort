package com.soccer.mcp.service;

import com.soccer.mcp.model.Player;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Service for player queries.
 */
public class PlayerService {

    private final List<Player> players;

    public PlayerService(List<Player> players) {
        this.players = players;
    }

    /**
     * Find players by various filters.
     */
    public List<Player> findPlayers(String name, String nationality, String club,
                                     String position, Integer minOverall, int limit) {
        return players.stream()
                .filter(p -> matchesName(p, name))
                .filter(p -> matchesNationality(p, nationality))
                .filter(p -> matchesClub(p, club))
                .filter(p -> matchesPosition(p, position))
                .filter(p -> minOverall == null || p.getOverall() >= minOverall)
                .sorted((a, b) -> Integer.compare(b.getOverall(), a.getOverall()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    private boolean matchesName(Player p, String name) {
        if (name == null) return true;
        return p.getName() != null && p.getName().toLowerCase().contains(name.toLowerCase());
    }

    private boolean matchesNationality(Player p, String nationality) {
        if (nationality == null) return true;
        return p.getNationality() != null && p.getNationality().toLowerCase().contains(nationality.toLowerCase());
    }

    private boolean matchesClub(Player p, String club) {
        if (club == null) return true;
        return p.getClub() != null && p.getClub().toLowerCase().contains(club.toLowerCase());
    }

    private boolean matchesPosition(Player p, String position) {
        if (position == null) return true;
        return p.getPosition() != null && p.getPosition().toLowerCase().contains(position.toLowerCase());
    }
}
