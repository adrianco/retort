package com.braziliansoccer.mcp.service;

import com.braziliansoccer.mcp.model.Player;
import java.util.*;
import java.util.stream.*;

public class PlayerService {
    private final List<Player> players;

    public PlayerService(List<Player> players) { this.players = players; }

    public List<Player> findByName(String name) {
        return players.stream()
            .filter(p -> p.name().toLowerCase().contains(name.toLowerCase()))
            .collect(Collectors.toList());
    }

    public List<Player> findByNationality(String nationality) {
        return players.stream()
            .filter(p -> p.nationality().equalsIgnoreCase(nationality))
            .collect(Collectors.toList());
    }

    public List<Player> findByClub(String club) {
        return players.stream()
            .filter(p -> p.club().toLowerCase().contains(club.toLowerCase()))
            .collect(Collectors.toList());
    }

    public List<Player> getTopPlayers(int limit) {
        return players.stream()
            .sorted(Comparator.comparingInt(Player::overall).reversed())
            .limit(limit)
            .collect(Collectors.toList());
    }

    public List<Player> getTopPlayersByClub(String club, int limit) {
        return players.stream()
            .filter(p -> p.club().toLowerCase().contains(club.toLowerCase()))
            .sorted(Comparator.comparingInt(Player::overall).reversed())
            .limit(limit)
            .collect(Collectors.toList());
    }
}
