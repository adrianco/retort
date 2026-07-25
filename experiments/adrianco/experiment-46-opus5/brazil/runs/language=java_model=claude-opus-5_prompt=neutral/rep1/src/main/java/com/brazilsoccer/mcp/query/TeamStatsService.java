package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Match;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.NavigableSet;
import java.util.Optional;
import java.util.TreeSet;

/** Club oriented aggregations: overall record, home/away split and competition history. */
public final class TeamStatsService {

    /** Everything the {@code team_stats} tool reports about one club. */
    public record TeamProfile(String teamId, int matches, TeamRecord overall, TeamRecord home,
                              TeamRecord away, Map<Competition, TeamRecord> byCompetition,
                              List<Match> recentMatches, Optional<Match> biggestWin,
                              Optional<Match> heaviestDefeat) {
    }

    /** One competition a club took part in. */
    public record CompetitionSpell(Competition competition, NavigableSet<Integer> seasons, TeamRecord record) {
    }

    private final KnowledgeGraph graph;
    private final MatchQueryService matchQueries;

    public TeamStatsService(KnowledgeGraph graph, MatchQueryService matchQueries) {
        this.graph = graph;
        this.matchQueries = matchQueries;
    }

    /** Builds the profile of a club over the matches selected by {@code query}. */
    public TeamProfile profile(String teamId, MatchQuery query) {
        List<Match> matches = matchQueries.findAll(query.team(teamId).venue(Venue.ALL).limit(Integer.MAX_VALUE));
        Map<Competition, TeamRecord> byCompetition = new EnumMap<>(Competition.class);
        for (Competition competition : Competition.values()) {
            List<Match> subset = matches.stream().filter(m -> m.competition() == competition).toList();
            if (!subset.isEmpty()) {
                byCompetition.put(competition, TeamRecord.of(subset, teamId, Venue.ALL));
            }
        }
        Comparator<Match> byMargin = Comparator.comparingInt(m -> m.goalsFor(teamId) - m.goalsAgainst(teamId));
        List<Match> played = matches.stream().filter(Match::isPlayed).toList();
        Optional<Match> biggestWin = played.stream().max(byMargin.thenComparing(Match::totalGoals));
        Optional<Match> worstDefeat = played.stream().min(byMargin.thenComparing(Comparator.comparingInt(Match::totalGoals).reversed()));
        List<Match> recent = new ArrayList<>(matches);
        recent.sort(Comparator.comparing(Match::date, Comparator.nullsFirst(Comparator.naturalOrder())).reversed());
        return new TeamProfile(teamId, matches.size(),
                TeamRecord.of(matches, teamId, Venue.ALL),
                TeamRecord.of(matches, teamId, Venue.HOME),
                TeamRecord.of(matches, teamId, Venue.AWAY),
                byCompetition,
                recent.size() > 10 ? recent.subList(0, 10) : recent,
                biggestWin.filter(m -> m.goalsFor(teamId) > m.goalsAgainst(teamId)),
                worstDefeat.filter(m -> m.goalsFor(teamId) < m.goalsAgainst(teamId)));
    }

    /** Which competitions and seasons a club appears in. */
    public List<CompetitionSpell> competitions(String teamId) {
        List<Match> matches = graph.matchesOf(teamId);
        Map<Competition, List<Match>> byCompetition = new EnumMap<>(Competition.class);
        for (Match match : matches) {
            byCompetition.computeIfAbsent(match.competition(), k -> new ArrayList<>()).add(match);
        }
        List<CompetitionSpell> spells = new ArrayList<>();
        byCompetition.forEach((competition, list) -> {
            NavigableSet<Integer> seasons = new TreeSet<>();
            list.forEach(m -> seasons.add(m.season()));
            spells.add(new CompetitionSpell(competition, seasons, TeamRecord.of(list, teamId, Venue.ALL)));
        });
        spells.sort(Comparator.comparingInt((CompetitionSpell s) -> s.record().played()).reversed());
        return spells;
    }
}
