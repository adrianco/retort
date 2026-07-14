package com.braziliansoccer.mcp.service;

import com.braziliansoccer.mcp.model.Match;
import java.util.*;
import java.util.stream.*;

public class MatchService {
    private final List<Match> matches;
    private final TeamNameNormalizer normalizer = new TeamNameNormalizer();

    public MatchService(List<Match> matches) { this.matches = matches; }

    public List<Match> findByTeam(String team) {
        return matches.stream()
            .filter(m -> normalizer.matches(m.homeTeam(), team) || normalizer.matches(m.awayTeam(), team))
            .collect(Collectors.toList());
    }

    public List<Match> findByTeams(String team1, String team2) {
        return matches.stream()
            .filter(m -> (normalizer.matches(m.homeTeam(), team1) && normalizer.matches(m.awayTeam(), team2)) ||
                         (normalizer.matches(m.homeTeam(), team2) && normalizer.matches(m.awayTeam(), team1)))
            .collect(Collectors.toList());
    }

    public List<Match> findByCompetition(String competition) {
        return matches.stream()
            .filter(m -> m.competition().equalsIgnoreCase(competition))
            .collect(Collectors.toList());
    }

    public List<Match> findBySeason(int season) {
        return matches.stream().filter(m -> m.season() == season).collect(Collectors.toList());
    }

    public List<Match> findBySeasonAndCompetition(int season, String competition) {
        return matches.stream()
            .filter(m -> m.season() == season && m.competition().equalsIgnoreCase(competition))
            .collect(Collectors.toList());
    }
}
