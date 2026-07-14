package com.brsoccer.mcp.service;

import com.brsoccer.mcp.data.TeamNameNormalizer;
import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;

import java.time.LocalDate;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

public class MatchService {

    private final List<Match> matches;

    public MatchService(List<Match> matches) {
        this.matches = matches;
    }

    public List<Match> all() {
        return matches;
    }

    public List<Match> findByTeam(String team) {
        String norm = TeamNameNormalizer.normalize(team);
        return matches.stream()
            .filter(m -> norm != null && (norm.equals(m.getHomeTeamNormalized()) || norm.equals(m.getAwayTeamNormalized())))
            .sorted(Comparator.comparing(Match::getDate, Comparator.nullsLast(Comparator.naturalOrder())))
            .collect(Collectors.toList());
    }

    public List<Match> findBetween(String teamA, String teamB) {
        String a = TeamNameNormalizer.normalize(teamA);
        String b = TeamNameNormalizer.normalize(teamB);
        return matches.stream()
            .filter(m -> {
                String h = m.getHomeTeamNormalized(), w = m.getAwayTeamNormalized();
                return (a.equals(h) && b.equals(w)) || (a.equals(w) && b.equals(h));
            })
            .sorted(Comparator.comparing(Match::getDate, Comparator.nullsLast(Comparator.naturalOrder())))
            .collect(Collectors.toList());
    }

    public List<Match> findByCompetition(Competition c) {
        return matches.stream()
            .filter(m -> m.getCompetition() == c)
            .collect(Collectors.toList());
    }

    public List<Match> findBySeason(int season) {
        return matches.stream()
            .filter(m -> m.getSeason() != null && m.getSeason() == season)
            .collect(Collectors.toList());
    }

    public List<Match> findInRange(LocalDate from, LocalDate to) {
        return matches.stream()
            .filter(m -> m.getDate() != null
                && !m.getDate().isBefore(from)
                && !m.getDate().isAfter(to))
            .collect(Collectors.toList());
    }

    public List<Match> filter(String team, Competition competition, Integer season) {
        String norm = team == null ? null : TeamNameNormalizer.normalize(team);
        return matches.stream()
            .filter(m -> norm == null || norm.equals(m.getHomeTeamNormalized()) || norm.equals(m.getAwayTeamNormalized()))
            .filter(m -> competition == null || m.getCompetition() == competition)
            .filter(m -> season == null || (m.getSeason() != null && m.getSeason().equals(season)))
            .sorted(Comparator.comparing(Match::getDate, Comparator.nullsLast(Comparator.naturalOrder())))
            .collect(Collectors.toList());
    }
}
