package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Match lookups over the knowledge graph.
 *
 * <p>Queries always start from the narrowest available adjacency index (club, then competition
 * season, then the full match list) so that a typical lookup inspects a few hundred edges.
 */
public final class MatchQueryService {

    private final KnowledgeGraph graph;

    public MatchQueryService(KnowledgeGraph graph) {
        this.graph = graph;
    }

    /** Head-to-head record between two clubs, from {@code teamA}'s point of view. */
    public record HeadToHead(String teamAId, String teamBId, List<Match> matches, TeamRecord recordForA) {
        public int draws() {
            return recordForA.draws();
        }
    }

    /** All matches matching the criteria (before the limit is applied). */
    public List<Match> findAll(MatchQuery query) {
        List<Match> candidates = candidates(query);
        List<Match> result = new ArrayList<>();
        for (Match match : candidates) {
            if (matches(match, query)) {
                result.add(match);
            }
        }
        result.sort(byDate(query.newestFirst()));
        return result;
    }

    /** Matching matches, truncated to {@code query.limit()}. */
    public List<Match> find(MatchQuery query) {
        List<Match> all = findAll(query);
        return all.size() <= query.limit() ? all : all.subList(0, query.limit());
    }

    public HeadToHead headToHead(String teamAId, String teamBId, MatchQuery filters) {
        MatchQuery query = filters.team(teamAId).opponent(teamBId).limit(Integer.MAX_VALUE);
        List<Match> matches = findAll(query);
        return new HeadToHead(teamAId, teamBId, matches, TeamRecord.of(matches, teamAId, Venue.ALL));
    }

    private List<Match> candidates(MatchQuery query) {
        if (query.teamId() != null) {
            return graph.matchesOf(query.teamId());
        }
        if (query.homeTeamId() != null) {
            return graph.matchesOf(query.homeTeamId());
        }
        if (query.awayTeamId() != null) {
            return graph.matchesOf(query.awayTeamId());
        }
        if (query.competition() != null && query.season() != null) {
            return graph.matchesOf(query.competition(), query.season());
        }
        return graph.matches();
    }

    private boolean matches(Match match, MatchQuery query) {
        if (query.competition() != null && match.competition() != query.competition()) {
            return false;
        }
        if (query.season() != null && match.season() != query.season()) {
            return false;
        }
        if (query.seasonFrom() != null && match.season() < query.seasonFrom()) {
            return false;
        }
        if (query.seasonTo() != null && match.season() > query.seasonTo()) {
            return false;
        }
        if (query.teamId() != null && !match.involves(query.teamId())) {
            return false;
        }
        if (query.opponentId() != null && !match.involves(query.opponentId())) {
            return false;
        }
        if (query.homeTeamId() != null && !match.homeTeamId().equals(query.homeTeamId())) {
            return false;
        }
        if (query.awayTeamId() != null && !match.awayTeamId().equals(query.awayTeamId())) {
            return false;
        }
        if (query.venue() != Venue.ALL && query.teamId() != null) {
            boolean home = match.isHome(query.teamId());
            if ((query.venue() == Venue.HOME) != home) {
                return false;
            }
        }
        if (query.dateFrom() != null && (match.date() == null || match.date().isBefore(query.dateFrom()))) {
            return false;
        }
        if (query.dateTo() != null && (match.date() == null || match.date().isAfter(query.dateTo()))) {
            return false;
        }
        if (query.round() != null) {
            String round = match.round();
            if (round == null || !TextUtils.containsIgnoringAccents(round, query.round())) {
                return false;
            }
        }
        return true;
    }

    private static Comparator<Match> byDate(boolean newestFirst) {
        Comparator<Match> comparator = Comparator
                .comparing(Match::date, Comparator.nullsLast(Comparator.naturalOrder()))
                .thenComparing(Match::id);
        return newestFirst ? comparator.reversed() : comparator;
    }
}
