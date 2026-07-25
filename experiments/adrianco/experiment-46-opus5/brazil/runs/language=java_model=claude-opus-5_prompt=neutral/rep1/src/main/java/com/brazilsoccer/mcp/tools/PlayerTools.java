package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.format.Formatters;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.query.MatchQuery;
import com.brazilsoccer.mcp.query.PlayerQueryService;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.query.TeamStatsService;
import com.brazilsoccer.mcp.query.Venue;
import com.brazilsoccer.mcp.util.TextUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Tools answering player oriented questions, including the cross-file player/club report. */
public final class PlayerTools {

    private PlayerTools() {
    }

    public static List<SoccerTool> create(ToolContext context) {
        return List.of(searchPlayers(context), playerProfile(context), clubSquads(context), playerClubReport(context));
    }

    private static SoccerTool searchPlayers(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("name", "Full or partial player name")
                .string("nationality", "Nationality, e.g. 'Brazil'")
                .string("club", "Club name; resolved through the same club index as the match data")
                .enumeration("position_group", "Broad position filter",
                        List.of("goalkeeper", "defender", "midfielder", "forward"))
                .string("position", "Exact FIFA position code, e.g. 'ST', 'CAM', 'GK'")
                .integer("min_overall", "Minimum FIFA overall rating")
                .integer("max_age", "Maximum age")
                .enumeration("sort_by", "Sort criterion (default overall)",
                        List.of("overall", "potential", "age", "name"))
                .integer("limit", "Maximum number of players (default 20, max 200)")
                .build();

        return new SoccerTool("search_players", "Search players",
                "Search the FIFA player database by name, nationality, club, position, rating or age. "
                        + "Returns rating, position, club and age for each player.",
                schema,
                args -> {
                    int limit = args.positiveInt("limit", 20, 200);
                    PlayerQueryService.PlayerQuery query = PlayerQueryService.PlayerQuery.create()
                            .name(args.string("name"))
                            .nationality(args.string("nationality"))
                            .position(args.string("position"))
                            .minOverall(args.integer("min_overall"))
                            .maxAge(args.integer("max_age"))
                            .sortBy(args.string("sort_by"))
                            .limit(limit);
                    if (args.has("position_group")) {
                        query.positionGroup(Player.PositionGroup.parse(args.string("position_group")));
                    }
                    Team club = null;
                    if (args.has("club")) {
                        String clubName = args.requireString("club");
                        club = context.graph().registry().search(clubName).stream()
                                .filter(t -> t.playerCount() > 0)
                                .findFirst()
                                .orElse(null);
                        if (club != null) {
                            query.clubTeamId(club.id());
                        } else {
                            query.clubText(clubName);
                        }
                    }

                    List<Player> players = context.playerQueries().search(query);
                    StringBuilder header = new StringBuilder("Players");
                    if (args.has("nationality")) {
                        header.append(" from ").append(args.string("nationality"));
                    }
                    if (args.has("club")) {
                        header.append(" at ").append(club == null ? args.string("club") : club.qualifiedName());
                    }
                    if (args.has("position_group") || args.has("position")) {
                        header.append(" playing ").append(args.string("position_group", args.string("position")));
                    }
                    if (args.has("name")) {
                        header.append(" matching '").append(args.string("name")).append('\'');
                    }
                    if (args.has("min_overall")) {
                        header.append(" rated ").append(args.integer("min_overall")).append("+");
                    }

                    if (players.isEmpty()) {
                        StringBuilder empty = new StringBuilder(header).append(": no player found.");
                        if (args.has("club")) {
                            empty.append("\nThe FIFA dataset only licenses part of the Brazilian clubs. Clubs "
                                    + "with players in the data: ")
                                    .append(String.join(", ", context.playerQueries()
                                            .clubsWithMatchData("Brazil", 12).stream()
                                            .map(PlayerQueryService.ClubSummary::clubName).toList()))
                                    .append(".");
                        }
                        if (args.has("name")) {
                            List<Player> suggestions = context.playerQueries().suggestions(args.string("name"), 5);
                            if (!suggestions.isEmpty()) {
                                empty.append("\nClosest names in the dataset:\n")
                                        .append(Formatters.playerList(suggestions, suggestions.size()));
                            }
                        }
                        return empty.toString();
                    }
                    List<Player> shown = players.size() > limit ? players.subList(0, limit) : players;
                    return header.append(" (") .append(players.size()).append(" found):\n")
                            .append(Formatters.playerList(shown, players.size())).toString();
                });
    }

    private static SoccerTool playerProfile(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("name", "Player name")
                .require("name")
                .build();

        return new SoccerTool("player_profile", "Player profile",
                "Full profile of one player: ratings, position, physical data, contract value and "
                        + "the key skill attributes, plus a link to the club node of the graph.",
                schema,
                args -> {
                    String name = args.requireString("name");
                    Optional<Player> found = context.playerQueries().findByName(name);
                    if (found.isEmpty()) {
                        List<Player> suggestions = context.playerQueries().suggestions(name, 5);
                        StringBuilder output = new StringBuilder("No player named '" + name + "' in the FIFA dataset.");
                        if (!suggestions.isEmpty()) {
                            output.append("\nClosest matches:\n").append(Formatters.playerList(suggestions, suggestions.size()));
                        }
                        return output.toString();
                    }
                    Player player = found.get();
                    StringBuilder output = new StringBuilder(player.name()).append(":\n");
                    output.append("- Overall rating: ").append(player.overall())
                            .append(" (potential ").append(player.potential()).append(")\n");
                    output.append("- Position: ").append(player.position())
                            .append(" (").append(player.positionGroup().name().toLowerCase(java.util.Locale.ROOT)).append(")\n");
                    output.append("- Club: ").append(player.hasClub() ? player.club() : "free agent");
                    if (player.jerseyNumber() != null) {
                        output.append(", shirt ").append(player.jerseyNumber());
                    }
                    output.append('\n');
                    output.append("- Nationality: ").append(player.nationality()).append('\n');
                    output.append("- Age: ").append(player.age())
                            .append(", height ").append(player.height())
                            .append(", weight ").append(player.weight()).append('\n');
                    output.append("- Preferred foot: ").append(player.preferredFoot()).append('\n');
                    output.append("- Value: ").append(player.value()).append(", wage: ").append(player.wage()).append('\n');
                    if (!player.skills().isEmpty()) {
                        List<String> skills = new ArrayList<>();
                        player.skills().forEach((skill, rating) -> skills.add(skill + " " + rating));
                        output.append("- Attributes: ").append(String.join(", ", skills)).append('\n');
                    }
                    if (player.clubTeamId() != null) {
                        int matches = context.graph().matchesOf(player.clubTeamId()).size();
                        output.append("- Club node in the graph: ").append(player.clubTeamId())
                                .append(matches > 0
                                        ? " (" + matches + " matches available, use team_stats for its record)"
                                        : " (no match data for this club in the bundled datasets)");
                    }
                    return output.toString();
                });
    }

    private static SoccerTool clubSquads(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("nationality", "Only count players of this nationality, e.g. 'Brazil'")
                .bool("only_clubs_with_matches", "Restrict to clubs that also have match data (default false)")
                .integer("min_players", "Minimum squad size to be listed (default 1)")
                .integer("limit", "Maximum number of clubs (default 25, max 200)")
                .build();

        return new SoccerTool("player_club_summary", "Players per club",
                "How many players each club has in the FIFA dataset and their average rating, "
                        + "optionally restricted to one nationality - answers questions such as "
                        + "'Brazilian players at Brazilian clubs'.",
                schema,
                args -> {
                    int limit = args.positiveInt("limit", 25, 200);
                    String nationality = args.string("nationality");
                    boolean onlyWithMatches = args.bool("only_clubs_with_matches", false);
                    List<PlayerQueryService.ClubSummary> summaries = onlyWithMatches
                            ? context.playerQueries().clubsWithMatchData(nationality, limit)
                            : context.playerQueries().clubSummaries(nationality, args.integer("min_players", 1), limit);
                    if (summaries.isEmpty()) {
                        return "No club matched these filters.";
                    }
                    List<List<String>> rows = new ArrayList<>();
                    for (PlayerQueryService.ClubSummary summary : summaries) {
                        rows.add(List.of(summary.clubName(),
                                String.valueOf(summary.players()),
                                TextUtils.round(summary.averageOverall(), 1),
                                summary.bestPlayer().map(p -> p.name() + " (" + p.overall() + ")").orElse("-"),
                                String.valueOf(context.graph().matchesOf(summary.teamId()).size())));
                    }
                    return (nationality == null ? "Clubs" : nationality + " players") + " in the FIFA dataset:\n"
                            + Formatters.table(List.of("Club", "Players", "Avg rating", "Best player", "Matches in graph"), rows);
                });
    }

    private static SoccerTool playerClubReport(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("name", "Player name")
                .integer("season", "Season to report for the player's club (default: latest available)")
                .require("name")
                .build();

        return new SoccerTool("player_club_report", "Player and club report",
                "Cross-file query: looks a player up in the FIFA dataset, resolves his club in the "
                        + "match graph and reports that club's record, so player and match data can "
                        + "be combined in a single answer.",
                schema,
                args -> {
                    String name = args.requireString("name");
                    Optional<Player> found = context.playerQueries().findByName(name);
                    if (found.isEmpty()) {
                        return "No player named '" + name + "' in the FIFA dataset.";
                    }
                    Player player = found.get();
                    StringBuilder output = new StringBuilder(Formatters.playerLine(player)).append("\n\n");
                    if (player.clubTeamId() == null) {
                        return output.append("This player has no club in the dataset.").toString();
                    }
                    Optional<Team> club = context.graph().team(player.clubTeamId());
                    if (club.isEmpty() || context.graph().matchesOf(player.clubTeamId()).isEmpty()) {
                        return output.append("His club (").append(player.club())
                                .append(") has no match data in the bundled Brazilian datasets.").toString();
                    }
                    Integer season = args.integer("season");
                    MatchQuery query = MatchQuery.create().season(season);
                    TeamStatsService.TeamProfile profile = context.teamStats().profile(club.get().id(), query);
                    if (profile.matches() == 0) {
                        return output.append("No matches for ").append(club.get().qualifiedName())
                                .append(season == null ? "" : " in " + season).append('.').toString();
                    }
                    TeamRecord record = profile.overall();
                    output.append("Club: ").append(club.get().qualifiedName())
                            .append(season == null ? " (all seasons in the dataset)" : " (season " + season + ")").append('\n');
                    output.append(Formatters.recordBlock(record, "- ")).append('\n');
                    output.append("\nHome: ").append(Formatters.recordLine(TeamRecord.of(
                            context.matchQueries().findAll(MatchQuery.create().season(season).team(club.get().id())
                                    .limit(Integer.MAX_VALUE)), club.get().id(), Venue.HOME)));
                    output.append("\n\nRecent matches:\n")
                            .append(Formatters.matchList(context.graph(), profile.recentMatches(), profile.matches()));
                    List<Player> teammates = context.graph().playersOfClub(club.get().id()).stream()
                            .filter(p -> p.id() != player.id())
                            .limit(5)
                            .toList();
                    if (!teammates.isEmpty()) {
                        output.append("\n\nOther players of the club in the FIFA dataset:\n")
                                .append(Formatters.playerList(teammates, teammates.size()));
                    }
                    return output.toString();
                });
    }
}
