%% Context: the MCP tool surface. Each tool takes structured arguments (the LLM
%% client turns the natural-language question into these) and returns plain
%% text. Bad arguments are reported back to the client as tool errors.
-module(soccer_tools).
-export([definitions/0, call/3]).

-define(COMPETITION_DEFAULT, <<"Brasileirão Série A"/utf8>>).

definitions() ->
    [tool(<<"search_matches">>,
          <<"Find matches by team (home, away or either), opponent, season, competition, stage (e.g. 'Final'), date range and venue. Newest first.">>,
          maps:merge(filter_props(), #{<<"limit">> => int_prop(<<"Max matches to list (default 20)">>)}),
          []),
     tool(<<"team_record">>,
          <<"Win/draw/loss record, goals for/against and win rate for a team, optionally filtered by season, competition or venue.">>,
          filter_props(), [<<"team">>]),
     tool(<<"head_to_head">>,
          <<"Head-to-head record between two teams in the dataset, with recent meetings.">>,
          maps:merge(filter_props(), #{<<"limit">> => int_prop(<<"Recent meetings to list (default 10)">>)}),
          [<<"team">>, <<"opponent">>]),
     tool(<<"standings">>,
          <<"League table calculated from match results (3 points for a win, 1 for a draw).">>,
          #{<<"season">> => int_prop(<<"Season year, e.g. 2019">>),
            <<"competition">> => str_prop(<<"Default: Brasileirão Série A"/utf8>>)},
          [<<"season">>]),
     tool(<<"league_summary">>,
          <<"Aggregate statistics: goals per match, home, draw and away win rates.">>,
          #{<<"season">> => int_prop(<<"Season year">>),
            <<"competition">> => str_prop(<<"Competition name, e.g. Copa Libertadores">>)},
          []),
     tool(<<"biggest_wins">>,
          <<"Largest winning margins in the dataset.">>,
          #{<<"season">> => int_prop(<<"Season year">>),
            <<"competition">> => str_prop(<<"Competition name">>),
            <<"limit">> => int_prop(<<"How many to list (default 10)">>)},
          []),
     tool(<<"search_players">>,
          <<"Search FIFA player data by name, nationality, club, position or minimum overall rating. Highest overall first.">>,
          #{<<"name">> => str_prop(<<"Name or part of a name, e.g. Gabriel Barbosa">>),
            <<"nationality">> => str_prop(<<"e.g. Brazil">>),
            <<"club">> => str_prop(<<"Club name or part of it, e.g. Flamengo">>),
            <<"position">> => str_prop(<<"Position code, e.g. ST, GK, CAM">>),
            <<"min_overall">> => int_prop(<<"Minimum overall rating">>),
            <<"limit">> => int_prop(<<"Max players to list (default 10)">>)},
          []),
     tool(<<"club_summary">>,
          <<"Squad size and average overall rating per club, for players of one nationality.">>,
          #{<<"nationality">> => str_prop(<<"Default: Brazil">>),
            <<"limit">> => int_prop(<<"Max clubs to list (default 20)">>)},
          [])].

filter_props() ->
    #{<<"team">> => str_prop(<<"Team name; state suffixes and accents are ignored">>),
      <<"opponent">> => str_prop(<<"Opponent team name">>),
      <<"venue">> => #{type => <<"string">>, enum => [<<"home">>, <<"away">>, <<"any">>],
                       description => <<"Whether the team played at home, away or either">>},
      <<"season">> => int_prop(<<"Season year, e.g. 2023">>),
      <<"competition">> => str_prop(<<"Brasileirão Série A, Série B, Série C, Copa do Brasil, Copa Libertadores"/utf8>>),
      <<"stage">> => str_prop(<<"Stage or round, e.g. Final, quarterfinals, group stage">>),
      <<"date_from">> => str_prop(<<"Start date, YYYY-MM-DD">>),
      <<"date_to">> => str_prop(<<"End date, YYYY-MM-DD">>)}.

tool(Name, Desc, Props, Required) ->
    #{name => Name, description => Desc,
      inputSchema => #{type => <<"object">>, properties => Props, required => Required}}.

str_prop(Desc) -> #{type => <<"string">>, description => Desc}.
int_prop(Desc) -> #{type => <<"integer">>, description => Desc}.

-spec call(binary(), map(), map()) -> {ok, binary()} | {error, binary()}.
call(Name, Args, Data) ->
    try dispatch(Name, Args, Data) of
        Text -> {ok, Text}
    catch
        throw:{bad_arg, Msg} -> {error, Msg};
        throw:{unknown_tool, N} -> {error, <<"Unknown tool: ", N/binary>>}
    end.

dispatch(<<"search_matches">>, A, D) -> search_matches(A, D);
dispatch(<<"team_record">>, A, D) -> team_record(A, D);
dispatch(<<"head_to_head">>, A, D) -> head_to_head(A, D);
dispatch(<<"standings">>, A, D) -> standings(A, D);
dispatch(<<"league_summary">>, A, D) -> league_summary(A, D);
dispatch(<<"biggest_wins">>, A, D) -> biggest_wins(A, D);
dispatch(<<"search_players">>, A, D) -> search_players(A, D);
dispatch(<<"club_summary">>, A, D) -> club_summary(A, D);
dispatch(N, _, _) -> throw({unknown_tool, N}).

search_matches(A, Data) ->
    F = match_filter(A),
    Limit = opt_int(<<"limit">>, A, 20),
    Results = soccer_stats:search(matches(Data), F),
    Shown = lists:sublist(Results, Limit),
    lines(header(<<"Matches">>, F, length(Results), length(Shown)),
          [<<"- ", (match_line(M))/binary>> || M <- Shown]).

team_record(A, Data) ->
    F = match_filter(A),
    Team = req_str(<<"team">>, A),
    R = soccer_stats:record(matches(Data), F),
    lines(<<(Team)/binary, (describe(F))/binary, ":">>,
          [fmt("- Matches: ~B", [maps:get(played, R)]),
           fmt("- Wins: ~B, Draws: ~B, Losses: ~B",
               [maps:get(wins, R), maps:get(draws, R), maps:get(losses, R)]),
           fmt("- Goals For: ~B, Goals Against: ~B", [maps:get(gf, R), maps:get(ga, R)]),
           fmt("- Win rate: ~.1f%", [maps:get(win_rate, R)])]).

head_to_head(A, Data) ->
    F = match_filter(A),
    Team = req_str(<<"team">>, A),
    Opp = req_str(<<"opponent">>, A),
    Limit = opt_int(<<"limit">>, A, 10),
    Ms = matches(Data),
    R = soccer_stats:record(Ms, F),
    Meetings = soccer_stats:search(Ms, F),
    lines(<<"Head-to-head ", Team/binary, " vs ", Opp/binary, " (", (describe_short(F))/binary, ")">>,
          [fmt("- Matches in dataset: ~B", [maps:get(played, R)]),
           fmt("- ~ts wins: ~B, ~ts wins: ~B, Draws: ~B",
               [Team, maps:get(wins, R), Opp, maps:get(losses, R), maps:get(draws, R)]),
           fmt("- Goals: ~B for, ~B against", [maps:get(gf, R), maps:get(ga, R)]),
           <<"Most recent meetings:">>] ++
          [match_line(M) || M <- lists:sublist(Meetings, Limit)]).

standings(A, Data) ->
    Season = req_int(<<"season">>, A),
    Comp = opt_str(<<"competition">>, A, ?COMPETITION_DEFAULT),
    Table = soccer_stats:standings(matches(Data), Season, Comp),
    case Table of
        [] -> throw({bad_arg, fmt_bin("No matches for ~ts in season ~B", [Comp, Season])});
        _ -> ok
    end,
    lines(fmt_bin("~ts standings, ~B (calculated from matches):", [Comp, Season]),
          [fmt("~B. ~ts - ~B pts (~BW, ~BD, ~BL, GF ~B, GA ~B)",
               [I, maps:get(team, R), maps:get(points, R), maps:get(wins, R),
                maps:get(draws, R), maps:get(losses, R), maps:get(gf, R), maps:get(ga, R)])
           || {I, R} <- lists:zip(lists:seq(1, length(Table)), Table)]).

league_summary(A, Data) ->
    Season = opt_int(<<"season">>, A, undefined),
    Comp = opt_str(<<"competition">>, A, undefined),
    S = soccer_stats:league_summary(matches(Data), Season, Comp),
    lines(<<"Summary", (describe(#{season => Season, competition => Comp}))/binary, ":">>,
          [fmt("- Matches: ~B", [maps:get(matches, S)]),
           fmt("- Goals per match: ~.2f", [maps:get(goals_per_match, S)]),
           fmt("- Home win rate: ~.1f%", [maps:get(home_win_rate, S)]),
           fmt("- Draw rate: ~.1f%", [maps:get(draw_rate, S)]),
           fmt("- Away win rate: ~.1f%", [maps:get(away_win_rate, S)])]).

biggest_wins(A, Data) ->
    Filter = #{season => opt_int(<<"season">>, A, undefined),
               competition => opt_str(<<"competition">>, A, undefined)},
    Limit = opt_int(<<"limit">>, A, 10),
    Wins = soccer_stats:biggest_wins(matches(Data), Filter, Limit),
    lines(<<"Biggest wins in the dataset:">>,
          [fmt_bin("~B. ~ts", [I, match_line(M)]) || {I, M} <- lists:zip(lists:seq(1, length(Wins)), Wins)]).

search_players(A, Data) ->
    Filter = #{name => opt_str(<<"name">>, A, undefined),
               nationality => opt_str(<<"nationality">>, A, undefined),
               club => opt_str(<<"club">>, A, undefined),
               position => upper(opt_str(<<"position">>, A, undefined)),
               min_overall => opt_int(<<"min_overall">>, A, undefined)},
    Limit = opt_int(<<"limit">>, A, 10),
    Hits = soccer_stats:search_players(players(Data), Filter),
    lines(header(<<"Players">>, Filter, length(Hits), min(Limit, length(Hits))),
          [<<"- ", (player_line(P))/binary>> || P <- lists:sublist(Hits, Limit)]).

club_summary(A, Data) ->
    Nat = opt_str(<<"nationality">>, A, <<"Brazil">>),
    Limit = opt_int(<<"limit">>, A, 20),
    Clubs = soccer_stats:club_summary(players(Data), Nat),
    lines(fmt_bin("~ts players by club (squad size, average overall):", [Nat]),
          [fmt_bin("- ~ts: ~B players (avg overall ~.1f)", [Club, N, Avg])
           || {Club, N, Avg} <- lists:sublist(Clubs, Limit), Club =/= <<>>]).

%% ---- argument handling ----

match_filter(A) ->
    #{team => opt_str(<<"team">>, A, undefined),
      opponent => opt_str(<<"opponent">>, A, undefined),
      competition => opt_str(<<"competition">>, A, undefined),
      stage => opt_str(<<"stage">>, A, undefined),
      season => opt_int(<<"season">>, A, undefined),
      from => opt_date(<<"date_from">>, A),
      to => opt_date(<<"date_to">>, A),
      venue => venue(A)}.

venue(A) ->
    case opt_str(<<"venue">>, A, undefined) of
        undefined -> any;
        <<"home">> -> home;
        <<"away">> -> away;
        <<"any">> -> any;
        Other -> throw({bad_arg, fmt_bin("venue must be home, away or any, got ~ts", [Other])})
    end.

arg(Key, A) ->
    case maps:get(Key, A, undefined) of
        null -> undefined;
        V -> V
    end.

req_str(Key, A) ->
    case opt_str(Key, A, undefined) of
        undefined -> throw({bad_arg, <<"Missing required argument: ", Key/binary>>});
        V -> V
    end.

req_int(Key, A) ->
    case opt_int(Key, A, undefined) of
        undefined -> throw({bad_arg, <<"Missing required argument: ", Key/binary>>});
        V -> V
    end.

opt_str(Key, A, Default) ->
    case arg(Key, A) of
        undefined -> Default;
        V when is_binary(V) -> V;
        V -> iolist_to_binary(io_lib:format("~p", [V]))
    end.

opt_int(Key, A, Default) ->
    case arg(Key, A) of
        undefined -> Default;
        V when is_integer(V) -> V;
        V when is_binary(V) ->
            try binary_to_integer(V)
            catch error:badarg -> throw({bad_arg, <<Key/binary, " must be an integer">>})
            end;
        _ -> throw({bad_arg, <<Key/binary, " must be an integer">>})
    end.

opt_date(Key, A) ->
    case arg(Key, A) of
        undefined -> undefined;
        V ->
            case soccer_util:parse_date(V) of
                {ok, D} -> D;
                error -> throw({bad_arg, <<Key/binary, " must be YYYY-MM-DD">>})
            end
    end.

matches(Data) -> maps:get(matches, Data).
players(Data) -> maps:get(players, Data).

%% ---- formatting ----

match_line(M) ->
    Stage = maps:get(stage, M),
    Where = case Stage of
                <<>> -> maps:get(competition, M);
                _ -> <<(maps:get(competition, M))/binary, ", ", Stage/binary>>
            end,
    fmt_bin("~ts: ~ts ~B-~B ~ts (~ts)",
            [soccer_util:format_date(maps:get(date, M)), maps:get(home, M),
             maps:get(home_goals, M), maps:get(away_goals, M), maps:get(away, M), Where]).

player_line(P) ->
    fmt_bin("~ts - Overall: ~B, Position: ~ts, Club: ~ts, Nationality: ~ts",
            [maps:get(name, P), maps:get(overall, P), maps:get(position, P),
             blank(maps:get(club, P)), maps:get(nationality, P)]).

blank(<<>>) -> <<"none">>;
blank(B) -> B.

header(Title, F, Total, Shown) ->
    fmt_bin("~ts~ts: ~B found (showing ~B)", [Title, describe(F), Total, Shown]).

%% Describes which filters were applied, e.g. " (season 2022, Brasileirão Série A)".
describe(F) ->
    Parts = [P || P <- [season_part(maps:get(season, F, undefined)),
                        comp_part(maps:get(competition, F, undefined)),
                        opt_text(<<"venue">>, maps:get(venue, F, any))], P =/= <<>>],
    case Parts of
        [] -> <<>>;
        _ -> <<" (", (join(Parts))/binary, ")">>
    end.

describe_short(F) ->
    case describe(F) of
        <<>> -> <<"all seasons and competitions">>;
        D -> binary:part(D, 2, byte_size(D) - 3)
    end.

opt_text(_, any) -> <<>>;
opt_text(_, undefined) -> <<>>;
opt_text(_, home) -> <<"home games">>;
opt_text(_, away) -> <<"away games">>.

season_part(undefined) -> <<>>;
season_part(S) -> fmt_bin("season ~B", [S]).

comp_part(undefined) -> <<>>;
comp_part(C) -> C.

join([X]) -> X;
join([X | Rest]) -> <<X/binary, ", ", (join(Rest))/binary>>.

lines(Title, Body) ->
    iolist_to_binary(lists:join($\n, [Title | Body])).

fmt(Fmt, Args) -> fmt_bin(Fmt, Args).

fmt_bin(Fmt, Args) ->
    unicode:characters_to_binary(io_lib:format(Fmt, Args)).

upper(undefined) -> undefined;
upper(B) -> unicode:characters_to_binary(string:uppercase(B)).
