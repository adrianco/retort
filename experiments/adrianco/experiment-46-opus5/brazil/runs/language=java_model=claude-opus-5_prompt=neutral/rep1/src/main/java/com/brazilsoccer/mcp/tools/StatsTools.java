package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.format.Formatters;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.query.MatchQuery;
import com.brazilsoccer.mcp.query.StatisticsService;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.query.Venue;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Aggregate statistics: averages, home advantage, leaderboards and record scorelines. */
public final class StatsTools {

    private StatsTools() {
    }

    public static List<SoccerTool> create(ToolContext context) {
        return List.of(statistics(context));
    }

    private static SoccerTool statistics(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .enumeration("metric", "Which statistic to compute",
                        List.of("overview", "biggest_wins", "highest_scoring", "team_ranking"))
                .enumeration("competition", "Competition filter",
                        List.of("serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"))
                .integer("season", "Season filter")
                .integer("season_from", "First season of a range")
                .integer("season_to", "Last season of a range")
                .string("team", "Restrict the statistics to matches of this club")
                .enumeration("venue", "For team_ranking: rank home records, away records or both",
                        List.of("all", "home", "away"))
                .enumeration("rank_by", "For team_ranking: the ranking criterion",
                        List.of("points", "points_per_game", "win_rate", "wins", "goals_scored",
                                "goals_conceded", "goal_difference"))
                .integer("min_matches", "For team_ranking: minimum number of matches (default 10)")
                .integer("limit", "Number of rows to return (default 10, max 100)")
                .build();

        return new SoccerTool("statistics", "Aggregate statistics",
                "Compute aggregated numbers over any slice of the data: average goals per match and "
                        + "home advantage (metric=overview), record scorelines (biggest_wins, "
                        + "highest_scoring) or club leaderboards such as the best home record "
                        + "(metric=team_ranking with rank_by and venue).",
                schema,
                args -> {
                    String metric = args.string("metric", "overview").toLowerCase(Locale.ROOT);
                    int limit = args.positiveInt("limit", 10, 100);
                    MatchQuery query = context.baseQuery(args).limit(Integer.MAX_VALUE);
                    Team team = null;
                    if (args.has("team")) {
                        team = context.requireTeam(args.requireString("team"));
                        query.team(team.id());
                    }
                    List<Match> matches = context.matchQueries().findAll(query);
                    String scope = (team == null ? "all matches" : team.qualifiedName() + " matches")
                            + context.filterDescription(args);
                    if (matches.isEmpty()) {
                        return "No matches found for " + scope + ".";
                    }

                    return switch (metric) {
                        case "biggest_wins" -> "Biggest victories - " + scope + ":\n"
                                + numbered(context, StatisticsService.biggestWins(matches, limit));
                        case "highest_scoring" -> "Highest scoring matches - " + scope + ":\n"
                                + numbered(context, StatisticsService.highestScoring(matches, limit));
                        case "team_ranking" -> teamRanking(context, args, matches, scope, limit);
                        default -> overview(context, matches, scope, limit);
                    };
                });
    }

    private static String overview(ToolContext context, List<Match> matches, String scope, int limit) {
        StatisticsService.Overview overview = StatisticsService.overview(matches);
        StringBuilder output = new StringBuilder("Statistics for ").append(scope).append(":\n");
        output.append("- Matches: ").append(overview.matches())
                .append(" (").append(overview.played()).append(" with a known score)\n");
        output.append("- Total goals: ").append(overview.goals()).append('\n');
        output.append("- Average goals per match: ").append(TextUtils.round(overview.goalsPerMatch(), 2)).append('\n');
        output.append("- Home wins: ").append(overview.homeWins())
                .append(" (").append(TextUtils.percent(overview.homeWins(), overview.played())).append(")\n");
        output.append("- Draws: ").append(overview.draws())
                .append(" (").append(TextUtils.percent(overview.draws(), overview.played())).append(")\n");
        output.append("- Away wins: ").append(overview.awayWins())
                .append(" (").append(TextUtils.percent(overview.awayWins(), overview.played())).append(")\n");
        output.append("- Seasons covered: ").append(MatchTools.seasonRange(matches)).append('\n');
        output.append("- Competitions: ").append(MatchTools.competitionBreakdown(matches)).append('\n');
        output.append("\nBiggest wins:\n").append(numbered(context, StatisticsService.biggestWins(matches, Math.min(limit, 5))));
        return output.toString();
    }

    private static String teamRanking(ToolContext context, ToolArguments args, List<Match> matches,
                                      String scope, int limit) {
        Venue venue = Venue.parse(args.string("venue"));
        StatisticsService.Metric metric = StatisticsService.Metric.parse(args.string("rank_by", "points"));
        int minMatches = args.integer("min_matches", 10);
        List<StatisticsService.TeamRanking> rankings =
                StatisticsService.rank(matches, venue, metric, minMatches, limit);
        if (rankings.isEmpty()) {
            return "No club reached the minimum of " + minMatches + " matches for " + scope + ".";
        }
        List<List<String>> rows = new ArrayList<>();
        int position = 1;
        for (StatisticsService.TeamRanking ranking : rankings) {
            TeamRecord record = ranking.record();
            rows.add(List.of(position++ + ". " + context.graph().nameOf(ranking.teamId()),
                    String.valueOf(record.played()), String.valueOf(record.wins()),
                    String.valueOf(record.draws()), String.valueOf(record.losses()),
                    String.valueOf(record.goalsFor()), String.valueOf(record.goalsAgainst()),
                    String.valueOf(record.points()),
                    TextUtils.round(record.pointsPerGame(), 2),
                    TextUtils.percent(record.wins(), record.played())));
        }
        return "Club ranking by " + metric.name().toLowerCase(Locale.ROOT)
                + " (" + venue.label() + " matches) - " + scope
                + ", minimum " + minMatches + " matches:\n"
                + Formatters.table(List.of("Pos Club", "P", "W", "D", "L", "GF", "GA", "Pts", "PPG", "Win %"), rows);
    }

    private static String numbered(ToolContext context, List<Match> matches) {
        if (matches.isEmpty()) {
            return "  (none)";
        }
        StringBuilder builder = new StringBuilder();
        int index = 1;
        for (Match match : matches) {
            builder.append(index++).append(". ").append(Formatters.matchLine(context.graph(), match)).append('\n');
        }
        return builder.toString().stripTrailing();
    }
}
