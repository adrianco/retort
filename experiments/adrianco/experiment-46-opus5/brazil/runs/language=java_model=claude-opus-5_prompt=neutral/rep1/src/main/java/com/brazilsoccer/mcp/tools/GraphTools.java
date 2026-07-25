package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.format.Formatters;
import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.model.Competition;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Introspection tool describing the datasets and the shape of the knowledge graph. */
public final class GraphTools {

    private GraphTools() {
    }

    public static List<SoccerTool> create(ToolContext context) {
        return List.of(datasetInfo(context));
    }

    private static SoccerTool datasetInfo(ToolContext context) {
        return new SoccerTool("dataset_info", "Dataset and graph overview",
                "What data is available: source files, licences, competitions and seasons covered, "
                        + "node and edge counts of the knowledge graph. Call this first to know which "
                        + "seasons and competitions can be queried.",
                Schemas.empty(),
                args -> {
                    KnowledgeGraph graph = context.graph();
                    StringBuilder output = new StringBuilder("Brazilian soccer knowledge graph:\n");
                    output.append("- Clubs (nodes): ").append(graph.teamCount()).append('\n');
                    output.append("- Matches (nodes): ").append(graph.matches().size()).append('\n');
                    output.append("- Players (nodes): ").append(graph.players().size()).append('\n');
                    output.append("- Competitions (nodes): ").append(Competition.values().length).append('\n');
                    output.append("- Relationships: ").append(graph.edgeCount())
                            .append(" (HOME_TEAM / AWAY_TEAM / PART_OF / PLAYS_FOR)\n");
                    output.append("- Loaded in ").append(graph.report().loadMillis()).append(" ms\n");

                    output.append("\nCoverage by competition:\n");
                    List<List<String>> coverage = new ArrayList<>();
                    for (Competition competition : Competition.values()) {
                        var seasons = graph.seasons(competition);
                        if (seasons.isEmpty()) {
                            continue;
                        }
                        long matches = graph.matches().stream().filter(m -> m.competition() == competition).count();
                        coverage.add(List.of(competition.displayName(), competition.id(),
                                seasons.first() + "-" + seasons.last(),
                                String.valueOf(seasons.size()), String.valueOf(matches)));
                    }
                    output.append(Formatters.table(
                            List.of("Competition", "Id", "Seasons", "Editions", "Matches"), coverage));

                    output.append("\n\nSource files:\n");
                    List<List<String>> datasets = new ArrayList<>();
                    for (KnowledgeGraph.DatasetInfo info : graph.datasets()) {
                        datasets.add(List.of(info.fileName(), String.valueOf(info.rowsRead()),
                                String.valueOf(info.recordsContributed()), info.license(), info.description()));
                    }
                    output.append(Formatters.table(
                            List.of("File", "Rows", "New records", "Licence", "Content"), datasets));

                    KnowledgeGraph.LoadReport report = graph.report();
                    output.append("\n\nData quality:\n");
                    output.append("- ").append(report.rawMatchRows()).append(" raw match rows were read; ")
                            .append(report.mergedDuplicates())
                            .append(" of them described a fixture already known from another file and were merged ")
                            .append("(the datasets overlap, e.g. Série A 2014-2019 appears in three files).\n");
                    output.append("- ").append(report.scoreConflicts())
                            .append(" merged fixtures had disagreeing scores between sources; the first source wins.\n");
                    output.append("- ").append(report.unresolvedTeams())
                            .append(" rows were dropped because a club name could not be resolved.\n");
                    output.append("- Club names are normalised (accents, state suffixes, 'EC'/'FC' noise), so "
                            + "'Atlético-MG', 'Atletico Mineiro' and 'Atlético Mineiro - MG' are one node, while "
                            + "Atlético-MG, Athletico-PR and Atlético-GO stay separate.\n");
                    output.append("- The player file has no goal scorer data, so top scorer questions cannot be "
                            + "answered; goals are only available per match and per club.");
                    return output.toString();
                });
    }
}
