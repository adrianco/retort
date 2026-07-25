package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.format.Formatters;
import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.query.MatchQuery;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.query.TeamStatsService;
import com.brazilsoccer.mcp.query.Venue;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/** Tools answering club oriented questions: records, competition history and club lookup. */
public final class TeamTools {

    private TeamTools() {
    }

    public static List<SoccerTool> create(ToolContext context) {
        return List.of(teamStats(context), teamCompetitions(context), listTeams(context));
    }

    private static SoccerTool teamStats(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("team", "Club name, any spelling")
                .enumeration("competition", "Restrict to one competition",
                        List.of("serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"))
                .integer("season", "Restrict to one season")
                .integer("season_from", "First season of a range")
                .integer("season_to", "Last season of a range")
                .string("date_from", "Earliest match date (YYYY-MM-DD)")
                .string("date_to", "Latest match date (YYYY-MM-DD)")
                .enumeration("venue", "Report the home record, the away record or both",
                        List.of("all", "home", "away"))
                .require("team")
                .build();

        return new SoccerTool("team_stats", "Team statistics",
                "Wins, draws, losses, goals, points and win rate for a club, optionally restricted to "
                        + "a competition, a season or home/away matches.",
                schema,
                args -> {
                    Team team = context.requireTeam(args.requireString("team"));
                    Venue venue = Venue.parse(args.string("venue"));
                    MatchQuery query = context.baseQuery(args);
                    TeamStatsService.TeamProfile profile = context.teamStats().profile(team.id(), query);

                    if (profile.matches() == 0) {
                        return "No matches found for " + team.qualifiedName() + context.filterDescription(args)
                                + "." + context.ambiguityNote(args.string("team"), team);
                    }

                    StringBuilder output = new StringBuilder();
                    output.append(team.qualifiedName()).append(' ').append(venue.label()).append(" record")
                            .append(context.filterDescription(args)).append(":\n");
                    TeamRecord main = switch (venue) {
                        case HOME -> profile.home();
                        case AWAY -> profile.away();
                        case ALL -> profile.overall();
                    };
                    output.append(Formatters.recordBlock(main, "- ")).append('\n');

                    if (venue == Venue.ALL) {
                        output.append("\nHome: ").append(Formatters.recordLine(profile.home()));
                        output.append("\nAway: ").append(Formatters.recordLine(profile.away()));
                    }
                    if (profile.byCompetition().size() > 1) {
                        output.append("\n\nBy competition:");
                        profile.byCompetition().forEach((competition, record) ->
                                output.append("\n- ").append(competition.displayName()).append(": ")
                                        .append(Formatters.recordLine(record)));
                    }
                    profile.biggestWin().ifPresent(match -> output.append("\n\nBiggest win: ")
                            .append(Formatters.matchLine(context.graph(), match)));
                    profile.heaviestDefeat().ifPresent(match -> output.append("\nHeaviest defeat: ")
                            .append(Formatters.matchLine(context.graph(), match)));
                    List<Match> recent = venue == Venue.ALL
                            ? profile.recentMatches()
                            : context.matchQueries().find(context.baseQuery(args)
                                    .team(team.id()).venue(venue).limit(10));
                    output.append("\n\nMost recent ")
                            .append(venue == Venue.ALL ? "matches" : venue.label() + " matches").append(":\n")
                            .append(Formatters.matchList(context.graph(), recent, main.played()));
                    output.append(context.ambiguityNote(args.string("team"), team));
                    return output.toString();
                });
    }

    private static SoccerTool teamCompetitions(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("team", "Club name, any spelling")
                .require("team")
                .build();

        return new SoccerTool("team_competitions", "Competitions of a club",
                "Which competitions and seasons a club appears in, with its record in each of them.",
                schema,
                args -> {
                    Team team = context.requireTeam(args.requireString("team"));
                    List<TeamStatsService.CompetitionSpell> spells = context.teamStats().competitions(team.id());
                    if (spells.isEmpty()) {
                        return "No match data for " + team.qualifiedName() + " in the dataset."
                                + context.ambiguityNote(args.string("team"), team);
                    }
                    StringBuilder output = new StringBuilder("Competitions played by ")
                            .append(team.qualifiedName()).append(":\n");
                    for (TeamStatsService.CompetitionSpell spell : spells) {
                        output.append("- ").append(spell.competition().displayName())
                                .append(" (").append(seasonsLabel(spell.seasons())).append("): ")
                                .append(Formatters.recordLine(spell.record())).append('\n');
                    }
                    output.append("\nKnown spellings in the source files: ")
                            .append(String.join(", ", team.aliases()));
                    return output.toString();
                });
    }

    private static SoccerTool listTeams(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("search", "Optional text to filter club names")
                .enumeration("competition", "Only clubs that played this competition",
                        List.of("serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"))
                .integer("season", "Only clubs that played in this season")
                .integer("min_matches", "Only clubs with at least this many matches (default 1)")
                .integer("limit", "Maximum number of clubs (default 30, max 300)")
                .build();

        return new SoccerTool("list_teams", "List clubs",
                "Discover the clubs in the knowledge graph and how they are spelled in the source "
                        + "files. Useful to disambiguate names such as Atlético-MG / Athletico-PR.",
                schema,
                args -> {
                    int limit = args.positiveInt("limit", 30, 300);
                    int minMatches = args.integer("min_matches", 1);
                    String search = args.string("search");
                    Competition competition = context.competition(args.string("competition")).orElse(null);
                    Integer season = args.integer("season");

                    List<Team> teams;
                    if (search != null) {
                        teams = new ArrayList<>(context.graph().registry().search(search));
                    } else {
                        teams = new ArrayList<>(context.graph().registry().teams());
                    }
                    List<List<String>> rows = new ArrayList<>();
                    teams.sort(Comparator.comparingInt(Team::matchCount).reversed());
                    for (Team team : teams) {
                        List<Match> matches = context.graph().matchesOf(team.id());
                        if (competition != null || season != null) {
                            matches = matches.stream()
                                    .filter(m -> competition == null || m.competition() == competition)
                                    .filter(m -> season == null || m.season() == season)
                                    .toList();
                        }
                        if (matches.size() < minMatches) {
                            continue;
                        }
                        rows.add(List.of(team.qualifiedName(), team.id(), String.valueOf(matches.size()),
                                MatchTools.seasonRange(matches),
                                String.valueOf(team.playerCount()),
                                shorten(String.join(" | ", team.aliases()))));
                        if (rows.size() >= limit) {
                            break;
                        }
                    }
                    if (rows.isEmpty()) {
                        return "No clubs matched" + (search == null ? " the filters" : " '" + search + "'") + ".";
                    }
                    return "Clubs in the knowledge graph"
                            + (search == null ? "" : " matching '" + search + "'") + ":\n"
                            + Formatters.table(List.of("Club", "Id", "Matches", "Seasons", "Players", "Spellings in the data"), rows);
                });
    }

    private static String seasonsLabel(java.util.NavigableSet<Integer> seasons) {
        if (seasons.isEmpty()) {
            return "-";
        }
        if (seasons.size() == seasons.last() - seasons.first() + 1) {
            return seasons.size() == 1 ? String.valueOf(seasons.first()) : seasons.first() + "-" + seasons.last();
        }
        List<String> parts = seasons.stream().map(String::valueOf).toList();
        return String.join(", ", parts);
    }

    private static String shorten(String value) {
        return value.length() <= 60 ? value : value.substring(0, 57) + "...";
    }
}
