package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.format.Formatters;
import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.query.CompetitionService;
import com.brazilsoccer.mcp.query.StatisticsService;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.query.Venue;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Tools answering competition oriented questions: tables, champions, relegation, comparisons. */
public final class CompetitionTools {

    private static final List<String> COMPETITION_IDS =
            List.of("serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores");

    private CompetitionTools() {
    }

    public static List<SoccerTool> create(ToolContext context) {
        return List.of(standings(context), competitionSummary(context), compareSeasons(context));
    }

    private static SoccerTool standings(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .enumeration("competition", "Competition (default serie_a)", COMPETITION_IDS)
                .integer("season", "Season year, e.g. 2019")
                .enumeration("venue", "Build the table from all, home only or away only matches",
                        List.of("all", "home", "away"))
                .integer("limit", "Number of rows to return (default all)")
                .require("season")
                .build();

        return new SoccerTool("standings", "Season table",
                "League table for one season, computed from the match results in the dataset: "
                        + "points, wins, draws, losses, goals for/against and goal difference.",
                schema,
                args -> {
                    Competition competition = context.competition(args.string("competition", "serie_a"))
                            .orElse(Competition.SERIE_A);
                    int season = requireSeason(context, competition, args.integer("season"));
                    Venue venue = Venue.parse(args.string("venue"));
                    List<CompetitionService.StandingRow> table =
                            context.competitions().standings(competition, season, venue);
                    if (table.isEmpty()) {
                        return "No matches for " + competition.displayName() + " " + season + ".";
                    }
                    int limit = args.integer("limit", table.size());
                    List<Match> matches = context.graph().matchesOf(competition, season);
                    long played = matches.stream().filter(Match::isPlayed).count();

                    List<List<String>> rows = new ArrayList<>();
                    for (CompetitionService.StandingRow row : table.stream().limit(limit).toList()) {
                        TeamRecord record = row.record();
                        rows.add(List.of(
                                row.position() + ". " + context.graph().nameOf(row.teamId()),
                                String.valueOf(record.played()), String.valueOf(record.wins()),
                                String.valueOf(record.draws()), String.valueOf(record.losses()),
                                String.valueOf(record.goalsFor()), String.valueOf(record.goalsAgainst()),
                                String.format("%+d", record.goalDifference()),
                                String.valueOf(record.points())));
                    }
                    StringBuilder output = new StringBuilder();
                    output.append(season).append(' ').append(competition.displayName());
                    output.append(venue == Venue.ALL ? " table" : " " + venue.label() + "-only table");
                    output.append(" (calculated from ").append(played).append(" matches in the dataset):\n");
                    output.append(Formatters.table(
                            List.of("Pos Club", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"), rows));
                    if (venue == Venue.ALL && competition.isLeague()) {
                        output.append("\n\nChampion: ").append(context.graph().nameOf(table.get(0).teamId()))
                                .append(" (").append(table.get(0).record().points()).append(" pts)");
                        List<CompetitionService.StandingRow> relegated =
                                context.competitions().relegationZone(competition, season, 4);
                        if (!relegated.isEmpty()) {
                            output.append("\nBottom four (relegation zone): ")
                                    .append(String.join(", ", relegated.stream()
                                            .map(r -> r.position() + ". " + context.graph().nameOf(r.teamId())
                                                    + " (" + r.record().points() + " pts)").toList()));
                        }
                        int expected = table.size() * (table.size() - 1);
                        if (played < expected) {
                            output.append("\nNote: the dataset holds ").append(played).append(" of the ")
                                    .append(expected).append(" matches of a full season, so the table may be partial.");
                        }
                    }
                    return output.toString();
                });
    }

    private static SoccerTool competitionSummary(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .enumeration("competition", "Competition (default serie_a)", COMPETITION_IDS)
                .integer("season", "Season year")
                .require("season")
                .build();

        return new SoccerTool("competition_summary", "Competition season summary",
                "Champion (or final result for knockout competitions), relegation zone, goals per "
                        + "match, home advantage and the biggest wins of one competition season.",
                schema,
                args -> {
                    Competition competition = context.competition(args.string("competition", "serie_a"))
                            .orElse(Competition.SERIE_A);
                    int season = requireSeason(context, competition, args.integer("season"));
                    CompetitionService.SeasonSummary summary = context.competitions().summary(competition, season);
                    if (summary.matches() == 0) {
                        return "No matches for " + competition.displayName() + " " + season + ".";
                    }
                    StringBuilder output = new StringBuilder();
                    output.append(season).append(' ').append(competition.displayName()).append(" summary:\n");
                    output.append("- Matches in dataset: ").append(summary.matches())
                            .append(" (").append(summary.playedMatches()).append(" with a known score)\n");
                    output.append("- Clubs: ").append(summary.teams()).append('\n');
                    output.append("- Goals per match: ").append(TextUtils.round(summary.goalsPerMatch(), 2)).append('\n');
                    output.append("- Home wins: ").append(TextUtils.percent(summary.homeWinRate(), 1))
                            .append(", draws: ").append(TextUtils.percent(summary.drawRate(), 1))
                            .append(", away wins: ").append(TextUtils.percent(summary.awayWinRate(), 1)).append('\n');

                    Optional<CompetitionService.TitleInfo> title = summary.title();
                    if (title.isPresent() && title.get().championTeamId() != null) {
                        output.append("- Champion: ").append(context.graph().nameOf(title.get().championTeamId()));
                        if (title.get().runnerUpTeamId() != null) {
                            output.append(" (runner-up: ")
                                    .append(context.graph().nameOf(title.get().runnerUpTeamId())).append(')');
                        }
                        output.append("\n  ").append(title.get().explanation()).append('\n');
                        if (!title.get().decidingMatches().isEmpty()) {
                            output.append(Formatters.matchList(context.graph(), title.get().decidingMatches(),
                                    title.get().decidingMatches().size())).append('\n');
                        }
                    } else if (title.isPresent()) {
                        output.append("- Champion: undetermined - ").append(title.get().explanation()).append('\n');
                    } else {
                        output.append("- Champion: cannot be determined from the matches in the dataset\n");
                    }

                    if (competition.isLeague() && !summary.table().isEmpty()) {
                        output.append("\nTop 5:\n");
                        summary.table().stream().limit(5).forEach(row -> output.append("  ")
                                .append(row.position()).append(". ")
                                .append(context.graph().nameOf(row.teamId())).append(" - ")
                                .append(row.record().points()).append(" pts (")
                                .append(row.record().wins()).append("W, ")
                                .append(row.record().draws()).append("D, ")
                                .append(row.record().losses()).append("L)\n"));
                        List<CompetitionService.StandingRow> relegated =
                                context.competitions().relegationZone(competition, season, 4);
                        if (!relegated.isEmpty()) {
                            output.append("Relegation zone (bottom four): ")
                                    .append(String.join(", ", relegated.stream()
                                            .map(r -> context.graph().nameOf(r.teamId())).toList()))
                                    .append('\n');
                        }
                    }
                    output.append("\nBiggest wins:\n")
                            .append(Formatters.matchList(context.graph(), summary.biggestWins(), summary.biggestWins().size()));
                    return output.toString();
                });
    }

    private static SoccerTool compareSeasons(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .enumeration("competition", "Competition (default serie_a)", COMPETITION_IDS)
                .integerArray("seasons", "Seasons to compare, e.g. [2018, 2019]")
                .require("seasons")
                .build();

        return new SoccerTool("compare_seasons", "Compare seasons",
                "Side by side comparison of several seasons of a competition: matches, goals per "
                        + "match, home advantage, champion and the best attack of each season.",
                schema,
                args -> {
                    Competition competition = context.competition(args.string("competition", "serie_a"))
                            .orElse(Competition.SERIE_A);
                    List<Integer> seasons = args.integerList("seasons");
                    if (seasons.isEmpty()) {
                        throw new ToolException("Provide at least one season, e.g. seasons=[2018,2019].");
                    }
                    List<List<String>> rows = new ArrayList<>();
                    for (int season : seasons) {
                        List<Match> matches = context.graph().matchesOf(competition, season);
                        StatisticsService.Overview overview = StatisticsService.overview(matches);
                        if (overview.played() == 0) {
                            rows.add(List.of(String.valueOf(season), "0", "-", "-", "-", "no data", "-"));
                            continue;
                        }
                        List<StatisticsService.TeamRanking> bestAttack = StatisticsService.rank(
                                matches, Venue.ALL, StatisticsService.Metric.GOALS_SCORED, 1, 1);
                        Optional<CompetitionService.TitleInfo> title = context.competitions().champion(competition, season);
                        rows.add(List.of(
                                String.valueOf(season),
                                String.valueOf(overview.played()),
                                TextUtils.round(overview.goalsPerMatch(), 2),
                                TextUtils.percent(overview.homeWins(), overview.played()),
                                TextUtils.percent(overview.draws(), overview.played()),
                                title.map(t -> t.championTeamId() == null ? "undetermined"
                                        : context.graph().nameOf(t.championTeamId())).orElse("undetermined"),
                                bestAttack.isEmpty() ? "-" : context.graph().nameOf(bestAttack.get(0).teamId())
                                        + " (" + bestAttack.get(0).record().goalsFor() + ")"));
                    }
                    return "Comparison of " + competition.displayName() + " seasons:\n"
                            + Formatters.table(List.of("Season", "Matches", "Goals/match", "Home win %",
                            "Draw %", "Champion", "Best attack"), rows);
                });
    }

    private static int requireSeason(ToolContext context, Competition competition, Integer season) {
        if (season == null) {
            throw new ToolException("Argument 'season' is required. Available seasons for "
                    + competition.displayName() + ": " + context.graph().seasons(competition) + ".");
        }
        if (!context.graph().seasons(competition).contains(season)) {
            throw new ToolException("No " + competition.displayName() + " data for season " + season
                    + ". Available seasons: " + context.graph().seasons(competition) + ".");
        }
        return season;
    }
}
