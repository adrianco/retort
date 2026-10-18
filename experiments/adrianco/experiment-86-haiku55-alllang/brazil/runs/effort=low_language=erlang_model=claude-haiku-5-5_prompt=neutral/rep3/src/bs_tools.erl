%%% MCP tool catalogue: JSON Schemas for each tool, argument handling and
%%% human-readable formatting of query results.
%%%
%%% Each call returns {ok, Text} or {error, Text}. Errors are returned to the
%%% LLM as tool results (isError) rather than protocol errors, so the model
%%% can correct its arguments and retry.
-module(bs_tools).

-export([list/0, call/3]).

-define(U(S), unicode:characters_to_binary(S)).

-define(DEFAULT_COMPETITION, ?U("Brasileirão Série A")).

%% --- catalogue -------------------------------------------------------------

-spec list() -> [map()].
list() ->
    [tool(<<"search_matches">>,
          <<"Find matches by team, opponent, competition, season or date range. "
            "Newest first. Team names may omit state suffixes (e.g. 'Flamengo').">>,
          #{team => str(<<"Team name (either side)">>),
            opponent => str(<<"Second team; with 'team' returns matches between them">>),
            competition => str(?U("Competition, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'")),
            season => int(<<"Season year, e.g. 2023">>),
            from => str(<<"Start date, YYYY-MM-DD or DD/MM/YYYY">>),
            to => str(<<"End date, YYYY-MM-DD or DD/MM/YYYY">>),
            limit => int(<<"Maximum matches to list (default 20)">>)}, []),
     tool(<<"team_stats">>,
          <<"Wins, draws, losses, goals and win rate for one team, with home/away splits.">>,
          #{team => str(<<"Team name">>), season => int(<<"Season year">>),
            competition => str(<<"Competition filter">>),
            from => str(<<"Start date">>), to => str(<<"End date">>)},
          [<<"team">>]),
     tool(<<"head_to_head">>,
          <<"Historical record between two teams across all matches in the dataset.">>,
          #{team1 => str(<<"First team">>), team2 => str(<<"Second team">>),
            limit => int(<<"Maximum recent matches to list (default 10)">>)},
          [<<"team1">>, <<"team2">>]),
     tool(<<"standings">>,
          <<"League table for a season, calculated from match results (3 pts win, 1 draw).">>,
          #{season => int(<<"Season year">>),
            competition => str(?U("Competition (default 'Brasileirão')"))},
          [<<"season">>]),
     tool(<<"aggregate_stats">>,
          <<"Aggregate statistics over matches. Metrics: average_goals, home_win_rate, "
            "biggest_wins, best_away_record, top_scorers.">>,
          #{metric => #{type => <<"string">>,
                        enum => [<<"average_goals">>, <<"home_win_rate">>,
                                 <<"biggest_wins">>, <<"best_away_record">>,
                                 <<"top_scorers">>]},
            season => int(<<"Season year">>),
            competition => str(<<"Competition filter">>),
            team => str(<<"Restrict to matches involving this team">>),
            from => str(<<"Start date">>), to => str(<<"End date">>)},
          [<<"metric">>]),
     tool(<<"search_players">>,
          <<"Search FIFA player records by name, nationality, club, position or rating.">>,
          #{name => str(<<"Name (case and accent insensitive, substring)">>),
            nationality => str(<<"Nationality, e.g. 'Brazil'">>),
            club => str(<<"Club name, e.g. 'Flamengo'">>),
            position => str(<<"Position code, e.g. 'ST', 'GK'">>),
            min_overall => int(<<"Minimum overall rating">>),
            limit => int(<<"Maximum players to list (default 20)">>)}, []),
     tool(<<"brazilian_club_summary">>,
          <<"Brazilian players grouped by Brazilian club: player count and average overall.">>,
          #{}, [])].

tool(Name, Desc, Props, Required) ->
    #{name => Name, description => Desc,
      inputSchema => #{type => <<"object">>, properties => Props, required => Required}}.

str(Desc) -> #{type => <<"string">>, description => Desc}.
int(Desc) -> #{type => <<"integer">>, description => Desc}.

%% --- dispatch --------------------------------------------------------------

-spec call(binary(), map(), map()) -> {ok, binary()} | {error, binary()}.
call(<<"search_matches">>, Args, Data) -> search_matches(Args, Data);
call(<<"team_stats">>, Args, Data) -> team_stats(Args, Data);
call(<<"head_to_head">>, Args, Data) -> head_to_head(Args, Data);
call(<<"standings">>, Args, Data) -> standings(Args, Data);
call(<<"aggregate_stats">>, Args, Data) -> aggregate_stats(Args, Data);
call(<<"search_players">>, Args, Data) -> search_players(Args, Data);
call(<<"brazilian_club_summary">>, _Args, Data) -> club_summary(Data);
call(Name, _Args, _Data) -> {error, <<"Unknown tool: ", Name/binary>>}.

search_matches(Args, Data) ->
    with_filters(Args, Data, fun(Filters) ->
        Matches = bs_query:search_matches(Data, Filters),
        {ok, format_matches(scope(Filters, Data), Matches, int_arg(<<"limit">>, Args, 20))}
    end).

team_stats(Args, Data) ->
    with_filters(Args, Data, fun(Filters) ->
        case maps:find(team, Filters) of
            error -> {error, <<"team_stats requires a team name">>};
            {ok, K} ->
                S = bs_query:team_stats(Data, K, maps:remove(team, Filters)),
                {ok, format_team_stats(name(K, Data), scope(Filters, Data), S)}
        end
    end).

head_to_head(Args, Data) ->
    Teams = {resolve_arg(<<"team1">>, Args, Data), resolve_arg(<<"team2">>, Args, Data)},
    case Teams of
        {{ok, K1}, {ok, K2}} ->
            H = bs_query:head_to_head(Data, K1, K2),
            {ok, format_h2h(name(K1, Data), name(K2, Data), H,
                            int_arg(<<"limit">>, Args, 10))};
        {{error, E}, _} -> {error, E};
        {_, {error, E}} -> {error, E}
    end.

standings(Args, Data) ->
    case int_opt(<<"season">>, Args) of
        {ok, none} -> {error, <<"standings requires a season, e.g. 2023">>};
        {ok, Season} ->
            Comp = str_arg(<<"competition">>, Args, ?DEFAULT_COMPETITION),
            case bs_query:standings(Data, #{season => Season, competition => Comp}) of
                [] -> {error, no_matches_text(Comp, Season)};
                Rows -> {ok, format_standings(Comp, Season, Rows)}
            end;
        {error, E} -> {error, E}
    end.

aggregate_stats(Args, Data) ->
    case metric(str_arg(<<"metric">>, Args, <<>>)) of
        error -> {error, <<"Unknown metric. Use average_goals, home_win_rate, "
                           "biggest_wins, best_away_record or top_scorers.">>};
        {ok, Metric} ->
            with_filters(Args, Data, fun(Filters) ->
                Result = bs_query:aggregate(Data, {Metric, Filters}),
                {ok, format_aggregate(Metric, Result, Data, scope(Filters, Data))}
            end)
    end.

search_players(Args, Data) ->
    Filters = maps:from_list(
                [{name, V} || V <- [str_arg(<<"name">>, Args, <<>>)], V =/= <<>>] ++
                [{nationality, V} || V <- [str_arg(<<"nationality">>, Args, <<>>)], V =/= <<>>] ++
                [{position, V} || V <- [str_arg(<<"position">>, Args, <<>>)], V =/= <<>>] ++
                [{club, bs_text:normalize_team(V)}
                 || V <- [str_arg(<<"club">>, Args, <<>>)], V =/= <<>>] ++
                [{min_overall, V} || {ok, V} <- [int_opt(<<"min_overall">>, Args)], V =/= none]),
    case bs_query:search_players(Data, Filters) of
        [] -> {error, <<"No players match those filters.">>};
        Players -> {ok, format_players(Players, int_arg(<<"limit">>, Args, 20))}
    end.

club_summary(Data) ->
    case bs_query:brazilian_club_summary(Data) of
        [] -> {error, <<"No Brazilian players found at clubs in the match data.">>};
        Rows -> {ok, format_clubs(Rows)}
    end.

%% --- filters and argument helpers ------------------------------------------

%% Builds the filter map shared by match, stats and aggregate tools.
%% Absent arguments are left out; invalid ones produce an error message.
with_filters(Args, Data, Fun) ->
    Parsed = [{season, int_opt(<<"season">>, Args)},
              {competition, str_opt(<<"competition">>, Args)},
              {from, date_opt(<<"from">>, Args)},
              {to, date_opt(<<"to">>, Args)},
              {team, team_opt(<<"team">>, Args, Data)},
              {opponent, team_opt(<<"opponent">>, Args, Data)}],
    case [E || {_, {error, E}} <- Parsed] of
        [E | _] -> {error, E};
        [] ->
            Filters = maps:from_list([{K, V} || {K, {ok, V}} <- Parsed, V =/= none]),
            Fun(Filters)
    end.

%% Each *_opt helper returns {ok, none} when the argument is absent.
int_opt(Key, Args) ->
    case maps:get(Key, Args, null) of
        null -> {ok, none};
        N when is_integer(N) -> {ok, N};
        _ -> {error, <<Key/binary, " must be an integer">>}
    end.

str_opt(Key, Args) ->
    case str_arg(Key, Args, <<>>) of
        <<>> -> {ok, none};
        S -> {ok, S}
    end.

date_opt(Key, Args) ->
    case str_opt(Key, Args) of
        {ok, none} -> {ok, none};
        {ok, S} ->
            case bs_text:parse_date(S) of
                {ok, Iso} -> {ok, Iso};
                error -> {error, <<"Cannot read date '", S/binary, "' for ", Key/binary>>}
            end
    end.

team_opt(Key, Args, Data) ->
    case str_opt(Key, Args) of
        {ok, none} -> {ok, none};
        {ok, Q} -> resolve(Q, Data)
    end.

resolve_arg(Key, Args, Data) ->
    case str_opt(Key, Args) of
        {ok, none} -> {error, <<Key/binary, " is required">>};
        {ok, Q} -> resolve(Q, Data)
    end.

resolve(Query, Data) ->
    case bs_query:resolve_team(Query, Data) of
        {ok, K} -> {ok, K};
        {error, not_found} ->
            {error, <<"No team matching '", Query/binary, "' in the match data.">>};
        {error, {ambiguous, Names}} ->
            {error, fmt("'~ts' is ambiguous. Did you mean one of: ~ts?",
                        [Query, join(Names, ", ")])}
    end.

str_arg(Key, Args, Default) ->
    case maps:get(Key, Args, null) of
        S when is_binary(S) -> string:trim(S);
        _ -> Default
    end.

int_arg(Key, Args, Default) ->
    case maps:get(Key, Args, null) of
        N when is_integer(N), N > 0 -> N;
        _ -> Default
    end.

metric(<<"average_goals">>) -> {ok, average_goals};
metric(<<"home_win_rate">>) -> {ok, home_win_rate};
metric(<<"biggest_wins">>) -> {ok, biggest_wins};
metric(<<"best_away_record">>) -> {ok, best_away_record};
metric(<<"top_scorers">>) -> {ok, top_scorers};
metric(_) -> error.

name(K, Data) -> maps:get(K, maps:get(teams, Data), K).

%% "Brasileirão, 2023" style label for headings.
scope(Filters, _Data) ->
    Parts = [maps:get(competition, Filters, <<>>),
             case maps:find(season, Filters) of
                 {ok, S} -> integer_to_binary(S);
                 error -> <<>>
             end],
    case [P || P <- Parts, P =/= <<>>] of
        [] -> <<"all competitions, all seasons">>;
        Present -> join(Present, ", ")
    end.

no_matches_text(Comp, Season) ->
    fmt("No matches found for ~ts in ~p.", [Comp, Season]).

%% --- formatting ------------------------------------------------------------

format_matches(Scope, [], _Limit) ->
    fmt("No matches found (~ts).", [Scope]);
format_matches(Scope, Matches, Limit) ->
    Shown = lists:sublist(Matches, Limit),
    More = length(Matches) - length(Shown),
    Lines = [match_line(M) || M <- Shown],
    Tail = [fmt("... (~B more matches in dataset)", [More]) || More > 0],
    join([fmt("Matches (~ts): ~B found", [Scope, length(Matches)]) | Lines ++ Tail], "\n").

match_line(M) ->
    Details = join([D || D <- [maps:get(competition, M), maps:get(round, M)], D =/= <<>>], ", "),
    Suffix = case Details of
                 <<>> -> <<>>;
                 _ -> fmt(" (~ts)", [Details])
             end,
    fmt("- ~ts: ~ts ~B-~B ~ts~ts",
        [maps:get(date, M), maps:get(home_name, M), maps:get(home_goals, M),
         maps:get(away_goals, M), maps:get(away_name, M), Suffix]).

format_team_stats(Team, Scope, S) ->
    join([fmt("~ts record (~ts):", [Team, Scope]),
          fmt("- Matches: ~B", [maps:get(matches, S)]),
          fmt("- Wins: ~B, Draws: ~B, Losses: ~B",
              [maps:get(wins, S), maps:get(draws, S), maps:get(losses, S)]),
          fmt("- Goals For: ~B, Goals Against: ~B",
              [maps:get(goals_for, S), maps:get(goals_against, S)]),
          fmt("- Win rate: ~.1f%", [maps:get(win_rate, S)]),
          fmt("- Home: ~ts", [record_line(maps:get(home, S))]),
          fmt("- Away: ~ts", [record_line(maps:get(away, S))])], "\n").

record_line(S) ->
    fmt("~B-~B-~B (W-D-L), win rate ~.1f%",
        [maps:get(wins, S), maps:get(draws, S), maps:get(losses, S), maps:get(win_rate, S)]).

format_h2h(N1, N2, H, Limit) ->
    Matches = maps:get(matches, H),
    Recent = lists:sublist(Matches, Limit),
    Head = [fmt("~ts vs ~ts head-to-head in dataset: ~B matches", [N1, N2, length(Matches)]),
            fmt("~ts wins: ~B, ~ts wins: ~B, Draws: ~B",
                [N1, maps:get(team1_wins, H), N2, maps:get(team2_wins, H), maps:get(draws, H)]),
            fmt("Goals: ~ts ~B, ~ts ~B",
                [N1, maps:get(team1_goals, H), N2, maps:get(team2_goals, H)])],
    case Recent of
        [] -> join(Head, "\n");
        _ -> join(Head ++ ["Most recent:" | [match_line(M) || M <- Recent]], "\n")
    end.

format_standings(Comp, Season, Rows) ->
    Header = fmt("~ts ~B standings (calculated from matches):", [Comp, Season]),
    Lines = [fmt("~B. ~ts - ~B pts (~B-~B-~B, GF ~B, GA ~B)",
                 [I, maps:get(team, R), maps:get(points, R), maps:get(won, R),
                  maps:get(drawn, R), maps:get(lost, R), maps:get(goals_for, R),
                  maps:get(goals_against, R)])
             || {I, R} <- lists:zip(lists:seq(1, length(Rows)), Rows)],
    join([Header | Lines], "\n").

format_aggregate(average_goals, R, _Data, Scope) ->
    fmt("Average goals per match (~ts): ~.2f over ~B matches",
        [Scope, maps:get(average_goals, R), maps:get(matches, R)]);
format_aggregate(home_win_rate, R, _Data, Scope) ->
    fmt("Home win rate (~ts): ~.1f% (~B of ~B matches)",
        [Scope, maps:get(home_win_rate, R), maps:get(home_wins, R), maps:get(matches, R)]);
format_aggregate(biggest_wins, Matches, _Data, Scope) ->
    join([fmt("Biggest wins (~ts):", [Scope]) | [match_line(M) || M <- Matches]], "\n");
format_aggregate(best_away_record, Rows, _Data, Scope) ->
    join([fmt("Best away records (~ts, min. 10 away matches):", [Scope]) |
          [fmt("~B. ~ts - ~.1f% away win rate (~B of ~B)",
               [I, maps:get(team, R), maps:get(away_win_rate, R),
                maps:get(away_wins, R), maps:get(away_matches, R)])
           || {I, R} <- lists:zip(lists:seq(1, length(Rows)), Rows)]], "\n");
format_aggregate(top_scorers, Rows, _Data, Scope) ->
    join([fmt("Top scorers (~ts):", [Scope]) |
          [fmt("~B. ~ts - ~B goals in ~B matches",
               [I, maps:get(team, R), maps:get(goals_for, R), maps:get(matches, R)])
           || {I, R} <- lists:zip(lists:seq(1, length(Rows)), Rows)]], "\n").

format_players(Players, Limit) ->
    Shown = lists:sublist(Players, Limit),
    More = length(Players) - length(Shown),
    Lines = [fmt("~B. ~ts - Overall: ~B, Position: ~ts, Club: ~ts (age ~B, ~ts)",
                 [I, maps:get(name, P), maps:get(overall, P), maps:get(position, P),
                  maps:get(club, P), maps:get(age, P), maps:get(nationality, P)])
             || {I, P} <- lists:zip(lists:seq(1, length(Shown)), Shown)],
    Tail = [fmt("... (~B more players in dataset)", [More]) || More > 0],
    join(Lines ++ Tail, "\n").

format_clubs(Rows) ->
    join(["Brazilian players at Brazilian clubs (from FIFA data):" |
          [fmt("- ~ts: ~B players (avg overall ~.1f)",
               [maps:get(club, R), maps:get(players, R), maps:get(average_overall, R)])
           || R <- Rows]], "\n").

%% --- text utilities --------------------------------------------------------

fmt(Format, Args) ->
    unicode:characters_to_binary(io_lib:format(Format, Args)).

join(Parts, Sep) ->
    unicode:characters_to_binary(lists:join(Sep, Parts)).
