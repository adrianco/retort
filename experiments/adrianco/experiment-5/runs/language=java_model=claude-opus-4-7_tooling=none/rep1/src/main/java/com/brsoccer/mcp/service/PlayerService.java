package com.brsoccer.mcp.service;

import com.brsoccer.mcp.data.TeamNameNormalizer;
import com.brsoccer.mcp.model.Player;

import java.text.Normalizer;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

public class PlayerService {

    private final List<Player> players;

    public PlayerService(List<Player> players) {
        this.players = players;
    }

    public List<Player> all() { return players; }

    public List<Player> searchByName(String query) {
        String q = stripDiacritics(query).toLowerCase();
        return players.stream()
            .filter(p -> p.getName() != null && stripDiacritics(p.getName()).toLowerCase().contains(q))
            .sorted(Comparator.comparing(Player::getOverall, Comparator.nullsLast(Comparator.reverseOrder())))
            .collect(Collectors.toList());
    }

    public List<Player> byNationality(String nationality) {
        String q = stripDiacritics(nationality).toLowerCase();
        return players.stream()
            .filter(p -> p.getNationality() != null && stripDiacritics(p.getNationality()).toLowerCase().equals(q))
            .sorted(Comparator.comparing(Player::getOverall, Comparator.nullsLast(Comparator.reverseOrder())))
            .collect(Collectors.toList());
    }

    public List<Player> byClub(String club) {
        String norm = TeamNameNormalizer.normalize(club);
        return players.stream()
            .filter(p -> p.getClubNormalized() != null && p.getClubNormalized().equals(norm))
            .sorted(Comparator.comparing(Player::getOverall, Comparator.nullsLast(Comparator.reverseOrder())))
            .collect(Collectors.toList());
    }

    public List<Player> byPosition(String position) {
        if (position == null) return List.of();
        String p = position.trim().toUpperCase();
        return players.stream()
            .filter(pl -> pl.getPosition() != null && pl.getPosition().equalsIgnoreCase(p))
            .sorted(Comparator.comparing(Player::getOverall, Comparator.nullsLast(Comparator.reverseOrder())))
            .collect(Collectors.toList());
    }

    public List<Player> topRated(int limit) {
        return players.stream()
            .sorted(Comparator.comparing(Player::getOverall, Comparator.nullsLast(Comparator.reverseOrder())))
            .limit(limit)
            .collect(Collectors.toList());
    }

    private static String stripDiacritics(String s) {
        if (s == null) return "";
        return Normalizer.normalize(s, Normalizer.Form.NFD)
                         .replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
    }
}
