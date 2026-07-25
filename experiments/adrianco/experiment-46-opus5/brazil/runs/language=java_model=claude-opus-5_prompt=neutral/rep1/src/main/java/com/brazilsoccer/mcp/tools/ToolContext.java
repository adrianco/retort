package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.query.CompetitionService;
import com.brazilsoccer.mcp.query.MatchQuery;
import com.brazilsoccer.mcp.query.MatchQueryService;
import com.brazilsoccer.mcp.query.PlayerQueryService;
import com.brazilsoccer.mcp.query.Rivalries;
import com.brazilsoccer.mcp.query.TeamStatsService;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/** Services and shared argument handling available to every tool. */
public final class ToolContext {

    private final KnowledgeGraph graph;
    private final MatchQueryService matchQueries;
    private final TeamStatsService teamStats;
    private final PlayerQueryService playerQueries;
    private final CompetitionService competitions;
    private final Rivalries rivalries;

    public ToolContext(KnowledgeGraph graph) {
        this.graph = graph;
        this.matchQueries = new MatchQueryService(graph);
        this.teamStats = new TeamStatsService(graph, matchQueries);
        this.playerQueries = new PlayerQueryService(graph);
        this.competitions = new CompetitionService(graph);
        this.rivalries = new Rivalries(graph.registry());
    }

    public KnowledgeGraph graph() {
        return graph;
    }

    public MatchQueryService matchQueries() {
        return matchQueries;
    }

    public TeamStatsService teamStats() {
        return teamStats;
    }

    public PlayerQueryService playerQueries() {
        return playerQueries;
    }

    public CompetitionService competitions() {
        return competitions;
    }

    public Rivalries rivalries() {
        return rivalries;
    }

    /** Resolves a club name or fails with a message listing the closest alternatives. */
    public Team requireTeam(String query) {
        List<Team> candidates = graph.registry().search(query);
        if (candidates.isEmpty()) {
            throw new ToolException("No club matching '" + query + "' in the dataset. "
                    + "Try the list_teams tool to discover the available spellings.");
        }
        return candidates.get(0);
    }

    /** Alternative clubs that also matched the query (namesakes from other states). */
    public String ambiguityNote(String query, Team chosen) {
        List<Team> candidates = graph.registry().search(query);
        List<Team> others = candidates.stream()
                .filter(t -> !t.id().equals(chosen.id()))
                .filter(t -> t.matchCount() >= 20 || t.playerCount() > 0)
                .limit(3)
                .toList();
        if (others.isEmpty()) {
            return "";
        }
        return "\nNote: '" + query + "' also matches " + others.stream()
                .map(t -> t.qualifiedName() + " [" + t.id() + "]")
                .collect(Collectors.joining(", ")) + ".";
    }

    public Optional<Competition> competition(String raw) {
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        Optional<Competition> competition = Competition.parse(raw);
        if (competition.isEmpty()) {
            throw new ToolException("Unknown competition '" + raw + "'. Supported values: "
                    + java.util.Arrays.stream(Competition.values()).map(Competition::id)
                    .collect(Collectors.joining(", ")) + ".");
        }
        return competition;
    }

    public Competition requireCompetition(String raw) {
        return competition(raw).orElseThrow(() -> new ToolException(
                "Missing competition. Supported values: " + java.util.Arrays.stream(Competition.values())
                        .map(Competition::id).collect(Collectors.joining(", ")) + "."));
    }

    /** Builds the competition / season / date filters shared by most tools. */
    public MatchQuery baseQuery(ToolArguments args) {
        MatchQuery query = MatchQuery.create();
        competition(args.string("competition")).ifPresent(query::competition);
        query.season(args.integer("season"));
        query.seasonRange(args.integer("season_from"), args.integer("season_to"));
        query.dateRange(args.date("date_from"), args.date("date_to"));
        if (args.has("round")) {
            query.round(args.string("round"));
        }
        return query;
    }

    /** Human readable description of the applied filters, used in tool output headers. */
    public String filterDescription(ToolArguments args) {
        StringBuilder builder = new StringBuilder();
        competition(args.string("competition")).ifPresent(c -> builder.append(" in ").append(c.displayName()));
        if (args.has("season")) {
            builder.append(" (season ").append(args.integer("season")).append(')');
        } else if (args.has("season_from") || args.has("season_to")) {
            builder.append(" (seasons ").append(args.string("season_from", "earliest"))
                    .append('-').append(args.string("season_to", "latest")).append(')');
        }
        if (args.has("date_from") || args.has("date_to")) {
            builder.append(" between ").append(args.string("date_from", "the start of the data"))
                    .append(" and ").append(args.string("date_to", "the end of the data"));
        }
        return builder.toString();
    }
}
