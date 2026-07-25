package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.format.Formatters;
import com.brazilsoccer.mcp.model.Competition;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Team;
import com.brazilsoccer.mcp.query.MatchQuery;
import com.brazilsoccer.mcp.query.MatchQueryService;
import com.brazilsoccer.mcp.query.Rivalries;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.query.Venue;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Tools answering match oriented questions: fixture search, head-to-head and derbies. */
public final class MatchTools {

    private MatchTools() {
    }

    public static List<SoccerTool> create(ToolContext context) {
        return List.of(searchMatches(context), headToHead(context), findDerbies(context));
    }

    private static SoccerTool searchMatches(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("team", "Club that took part in the match, any spelling (e.g. 'Flamengo', 'Atletico-MG')")
                .string("opponent", "Second club, to look for meetings between two clubs")
                .string("home_team", "Restrict to matches where this club played at home")
                .string("away_team", "Restrict to matches where this club played away")
                .enumeration("competition", "Competition filter",
                        List.of("serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"))
                .integer("season", "Season (year) of the competition")
                .integer("season_from", "First season of a range")
                .integer("season_to", "Last season of a range")
                .string("date_from", "Earliest match date, ISO format YYYY-MM-DD")
                .string("date_to", "Latest match date, ISO format YYYY-MM-DD")
                .string("round", "Round or stage filter, e.g. '22' or 'final'")
                .enumeration("venue", "Where the 'team' argument played", List.of("all", "home", "away"))
                .enumeration("order", "Sort order by date", List.of("newest", "oldest"))
                .integer("limit", "Maximum number of matches to return (default 20, max 200)")
                .build();

        return new SoccerTool("search_matches", "Search matches",
                "Find matches by club, opponent, competition, season, round or date range. "
                        + "Returns date, teams, score and competition context for each match.",
                schema,
                args -> {
                    MatchQuery query = context.baseQuery(args);
                    query.venue(Venue.parse(args.string("venue")));
                    query.newestFirst(!"oldest".equalsIgnoreCase(args.string("order", "newest")));
                    query.limit(args.positiveInt("limit", 20, 200));

                    StringBuilder header = new StringBuilder("Matches");
                    Team team = null;
                    if (args.has("team")) {
                        team = context.requireTeam(args.requireString("team"));
                        query.team(team.id());
                        header.append(" for ").append(team.qualifiedName());
                    }
                    if (args.has("opponent")) {
                        Team opponent = context.requireTeam(args.requireString("opponent"));
                        query.opponent(opponent.id());
                        header.append(team == null ? " involving " : " vs ").append(opponent.qualifiedName());
                    }
                    if (args.has("home_team")) {
                        Team home = context.requireTeam(args.requireString("home_team"));
                        query.homeTeam(home.id());
                        header.append(" with ").append(home.qualifiedName()).append(" at home");
                    }
                    if (args.has("away_team")) {
                        Team away = context.requireTeam(args.requireString("away_team"));
                        query.awayTeam(away.id());
                        header.append(" with ").append(away.qualifiedName()).append(" away");
                    }
                    header.append(context.filterDescription(args));
                    if (query.venue() != Venue.ALL && team != null) {
                        header.append(" [").append(query.venue().label()).append(" matches only]");
                    }

                    List<Match> all = context.matchQueries().findAll(query);
                    List<Match> shown = all.size() > query.limit() ? all.subList(0, query.limit()) : all;
                    StringBuilder output = new StringBuilder(header).append(":\n");
                    output.append(Formatters.matchList(context.graph(), shown, all.size())).append('\n');
                    output.append("\nTotal: ").append(all.size()).append(" match(es) found");
                    if (all.size() > shown.size()) {
                        output.append(", showing ").append(shown.size());
                    }
                    output.append('.');
                    if (!all.isEmpty()) {
                        output.append("\nCompetitions covered: ").append(competitionBreakdown(all));
                    } else if (team != null && team.matchCount() == 0 && team.playerCount() > 0) {
                        output.append('\n').append(team.displayName())
                                .append(" is only known from the FIFA player dataset; the bundled match files "
                                        + "cover Brazilian competitions only.");
                    }
                    if (team != null) {
                        output.append(context.ambiguityNote(args.string("team"), team));
                    }
                    return output.toString();
                });
    }

    private static SoccerTool headToHead(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("team_a", "First club")
                .string("team_b", "Second club")
                .enumeration("competition", "Restrict the comparison to one competition",
                        List.of("serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"))
                .integer("season", "Restrict the comparison to one season")
                .integer("season_from", "First season of a range")
                .integer("season_to", "Last season of a range")
                .integer("limit", "How many recent meetings to list (default 10, max 100)")
                .require("team_a", "team_b")
                .build();

        return new SoccerTool("head_to_head", "Head-to-head record",
                "Compare two clubs: wins, draws, losses, goals and the list of their meetings "
                        + "across every competition in the dataset.",
                schema,
                args -> {
                    Team teamA = context.requireTeam(args.requireString("team_a"));
                    Team teamB = context.requireTeam(args.requireString("team_b"));
                    if (teamA.id().equals(teamB.id())) {
                        throw new ToolException("Both arguments resolved to the same club: " + teamA.qualifiedName());
                    }
                    int limit = args.positiveInt("limit", 10, 100);
                    MatchQueryService.HeadToHead h2h =
                            context.matchQueries().headToHead(teamA.id(), teamB.id(), context.baseQuery(args));
                    TeamRecord record = h2h.recordForA();

                    StringBuilder output = new StringBuilder();
                    output.append(teamA.displayName()).append(" vs ").append(teamB.displayName());
                    Optional<Rivalries.Derby> derby = context.rivalries().between(teamA.id(), teamB.id());
                    derby.ifPresent(d -> output.append(" (").append(d.name()).append(" derby)"));
                    output.append(context.filterDescription(args)).append(":\n");

                    if (h2h.matches().isEmpty()) {
                        output.append("No meetings between these clubs in the dataset.");
                        return output.toString();
                    }
                    List<Match> recent = h2h.matches().stream()
                            .sorted((a, b) -> compareDates(b, a))
                            .limit(limit)
                            .toList();
                    output.append(Formatters.matchList(context.graph(), recent, h2h.matches().size())).append("\n\n");
                    output.append("Head-to-head in dataset: ")
                            .append(teamA.displayName()).append(' ').append(record.wins()).append(" wins, ")
                            .append(teamB.displayName()).append(' ').append(record.losses()).append(" wins, ")
                            .append(record.draws()).append(" draws\n");
                    output.append("Goals: ").append(teamA.displayName()).append(' ').append(record.goalsFor())
                            .append(" - ").append(record.goalsAgainst()).append(' ').append(teamB.displayName())
                            .append(" over ").append(record.played()).append(" played matches\n");
                    output.append("Competitions: ").append(competitionBreakdown(h2h.matches())).append('\n');

                    TeamRecord homeRecord = TeamRecord.of(h2h.matches(), teamA.id(), Venue.HOME);
                    TeamRecord awayRecord = TeamRecord.of(h2h.matches(), teamA.id(), Venue.AWAY);
                    output.append(teamA.displayName()).append(" at home: ").append(Formatters.recordLine(homeRecord)).append('\n');
                    output.append(teamA.displayName()).append(" away:    ").append(Formatters.recordLine(awayRecord));
                    return output.toString();
                });
    }

    private static SoccerTool findDerbies(ToolContext context) {
        Map<String, Object> schema = Schemas.object()
                .string("team", "Only derbies involving this club")
                .integer("season", "Only derbies played in this season")
                .enumeration("competition", "Only derbies in this competition",
                        List.of("serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"))
                .integer("limit", "Maximum number of matches per derby (default 5, max 50)")
                .build();

        return new SoccerTool("find_derbies", "Find derbies",
                "List the classic Brazilian derbies (Fla-Flu, Derby Paulista, Gre-Nal, ...) and the "
                        + "matches that were played, optionally filtered by club, season or competition.",
                schema,
                args -> {
                    int limit = args.positiveInt("limit", 5, 50);
                    List<Rivalries.Derby> derbies;
                    if (args.has("team")) {
                        Team team = context.requireTeam(args.requireString("team"));
                        derbies = context.rivalries().involving(team.id());
                        if (derbies.isEmpty()) {
                            return "No classic derby registered for " + team.qualifiedName() + ".";
                        }
                    } else {
                        derbies = context.rivalries().all();
                    }
                    StringBuilder output = new StringBuilder("Derbies")
                            .append(context.filterDescription(args)).append(":\n");
                    int totalMatches = 0;
                    for (Rivalries.Derby derby : derbies) {
                        MatchQuery query = context.baseQuery(args)
                                .team(derby.teamAId()).opponent(derby.teamBId()).limit(Integer.MAX_VALUE);
                        List<Match> matches = context.matchQueries().findAll(query);
                        if (matches.isEmpty()) {
                            continue;
                        }
                        totalMatches += matches.size();
                        output.append('\n').append(derby.name()).append(" - ")
                                .append(context.graph().nameOf(derby.teamAId())).append(" vs ")
                                .append(context.graph().nameOf(derby.teamBId()))
                                .append(" (").append(matches.size()).append(" matches):\n");
                        output.append(Formatters.matchList(context.graph(),
                                matches.size() > limit ? matches.subList(0, limit) : matches, matches.size()))
                                .append('\n');
                    }
                    if (totalMatches == 0) {
                        return output.append("\nNo derby matches found for these filters.").toString();
                    }
                    return output.append("\nTotal derby matches found: ").append(totalMatches).append('.').toString();
                });
    }

    private static int compareDates(Match a, Match b) {
        if (a.date() == null && b.date() == null) {
            return a.id().compareTo(b.id());
        }
        if (a.date() == null) {
            return -1;
        }
        if (b.date() == null) {
            return 1;
        }
        return a.date().compareTo(b.date());
    }

    /** "Brasileirão Série A 30, Copa do Brasil 4" */
    static String competitionBreakdown(List<Match> matches) {
        Map<Competition, Integer> counts = new EnumMap<>(Competition.class);
        for (Match match : matches) {
            counts.merge(match.competition(), 1, Integer::sum);
        }
        List<String> parts = new ArrayList<>();
        counts.forEach((competition, count) -> parts.add(competition.displayName() + " " + count));
        return String.join(", ", parts);
    }

    /** Exposed for reuse by other tool groups. */
    static String seasonRange(List<Match> matches) {
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        for (Match match : matches) {
            min = Math.min(min, match.season());
            max = Math.max(max, match.season());
        }
        return matches.isEmpty() ? "-" : min == max ? String.valueOf(min) : min + "-" + max;
    }
}
