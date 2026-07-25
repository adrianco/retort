%% MCP tool definitions (name/description/JSON input schema) and dispatch of
%% tools/call requests onto the query layer.
-module(bsmcp_tools).

-export([tools/0, call/2]).

tools() ->
    [#{name => <<"search_matches">>,
       description =>
           <<"Search Brazilian soccer matches by team(s), competition, "
             "season, stage and/or date range. Covers Brasileirao Serie A "
             "(2003-2023), Serie B, Serie C, Copa do Brasil and Copa "
             "Libertadores. Team names are normalized, so 'Flamengo', "
             "'Flamengo-RJ' and 'flamengo' all work. When both team and "
             "opponent are given, a head-to-head summary is included.">>,
       inputSchema =>
           #{type => <<"object">>,
             properties =>
                 #{team => str(<<"Team name (either home or away)">>),
                   opponent => str(<<"Second team, to find head-to-head matches">>),
                   competition => str(<<"Competition filter: Brasileirao / Serie A, "
                                        "Serie B, Serie C, Copa do Brasil, Libertadores">>),
                   season => int(<<"Season year, e.g. 2019">>),
                   stage => str(<<"Stage filter, e.g. final, semifinals, "
                                  "quarterfinals, group stage (cup finals are "
                                  "labeled 'final')">>),
                   date_from => str(<<"Earliest date, YYYY-MM-DD">>),
                   date_to => str(<<"Latest date, YYYY-MM-DD">>),
                   limit => int(<<"Max matches to list (default 20)">>)}}},
     #{name => <<"team_stats">>,
       description =>
           <<"Win/draw/loss record, goals for/against and home/away splits "
             "for a team, optionally filtered by season, competition and "
             "venue (home/away).">>,
       inputSchema =>
           #{type => <<"object">>,
             properties =>
                 #{team => str(<<"Team name">>),
                   season => int(<<"Season year">>),
                   competition => str(<<"Competition filter">>),
                   venue => #{type => <<"string">>,
                              enum => [<<"home">>, <<"away">>, <<"all">>],
                              description => <<"Only home or away matches (default all)">>}},
             required => [<<"team">>]}},
     #{name => <<"head_to_head">>,
       description =>
           <<"Full head-to-head comparison between two teams: every meeting "
             "in the dataset plus a wins/draws/goals summary.">>,
       inputSchema =>
           #{type => <<"object">>,
             properties =>
                 #{team1 => str(<<"First team">>),
                   team2 => str(<<"Second team">>),
                   limit => int(<<"Max matches to list (default 20)">>)},
             required => [<<"team1">>, <<"team2">>]}},
     #{name => <<"competition_standings">>,
       description =>
           <<"League table for a competition season, computed from match "
             "results (3 points per win). Use for questions like 'who won "
             "the 2019 Brasileirao' (top of table) or 'which teams were "
             "relegated' (bottom four of Serie A).">>,
       inputSchema =>
           #{type => <<"object">>,
             properties =>
                 #{competition => str(<<"Competition (default Brasileirao Serie A)">>),
                   season => int(<<"Season year, e.g. 2019">>),
                   limit => int(<<"Max table rows (default 30)">>)},
             required => [<<"season">>]}},
     #{name => <<"search_players">>,
       description =>
           <<"Search the FIFA 19 player database (18k players) by name, "
             "nationality, club, position and minimum overall rating. "
             "Results are sorted by overall rating. Position accepts FIFA "
             "codes (ST, GK, CDM...) or roles (forward, midfielder, "
             "defender, goalkeeper).">>,
       inputSchema =>
           #{type => <<"object">>,
             properties =>
                 #{name => str(<<"Player name (partial match)">>),
                   nationality => str(<<"Nationality, e.g. Brazil">>),
                   club => str(<<"Club name (partial match)">>),
                   position => str(<<"Position code or role keyword">>),
                   min_overall => int(<<"Minimum overall rating">>),
                   limit => int(<<"Max players to list (default 10)">>)}}},
     #{name => <<"league_stats">>,
       description =>
           <<"Aggregate statistics for a set of matches: goals per match, "
             "home-win / draw / away-win rates. Filter by competition "
             "and/or season.">>,
       inputSchema =>
           #{type => <<"object">>,
             properties =>
                 #{competition => str(<<"Competition filter">>),
                   season => int(<<"Season year">>)}}},
     #{name => <<"biggest_wins">>,
       description =>
           <<"Largest margins of victory in the dataset, optionally filtered "
             "by competition and/or season.">>,
       inputSchema =>
           #{type => <<"object">>,
             properties =>
                 #{competition => str(<<"Competition filter">>),
                   season => int(<<"Season year">>),
                   limit => int(<<"Max matches to list (default 10)">>)}}},
     #{name => <<"data_summary">>,
       description =>
           <<"Overview of the loaded datasets: match counts per competition, "
             "season coverage, team and player counts.">>,
       inputSchema => #{type => <<"object">>, properties => #{}}}].

str(Desc) -> #{type => <<"string">>, description => Desc}.
int(Desc) -> #{type => <<"integer">>, description => Desc}.

%%% Dispatch -------------------------------------------------------------------

-spec call(binary(), map()) -> {ok, binary()} | {error, binary()}.
call(Name, Args) when is_map(Args) ->
    try do_call(Name, Args)
    catch
        Class:Reason:Stack ->
            {error, iolist_to_binary(
                      io_lib:format("Internal error running tool ~ts: ~p:~p~n~p",
                                    [Name, Class, Reason, Stack]))}
    end;
call(Name, _) ->
    call(Name, #{}).

do_call(<<"search_matches">>, Args) ->
    Opts = maps:filter(
             fun(_, V) -> V =/= undefined end,
             #{team1 => arg_str(Args, <<"team">>),
               team2 => arg_str(Args, <<"opponent">>),
               competition => arg_str(Args, <<"competition">>),
               season => arg_int(Args, <<"season">>),
               stage => arg_str(Args, <<"stage">>),
               date_from => arg_str(Args, <<"date_from">>),
               date_to => arg_str(Args, <<"date_to">>)}),
    Limit = arg_limit(Args, 20),
    case bsmcp_query:search_matches(Opts) of
        {ok, Result} -> {ok, bsmcp_format:matches(Result, Limit)};
        {error, E} -> {error, err_text(E)}
    end;

do_call(<<"team_stats">>, Args) ->
    case arg_str(Args, <<"team">>) of
        undefined ->
            {error, <<"Missing required argument: team">>};
        Team ->
            Opts = maps:filter(
                     fun(_, V) -> V =/= undefined end,
                     #{season => arg_int(Args, <<"season">>),
                       competition => arg_str(Args, <<"competition">>),
                       venue => arg_str(Args, <<"venue">>)}),
            case bsmcp_query:team_stats(Team, maps:merge(#{venue => <<"all">>}, Opts)) of
                {ok, Stats} -> {ok, bsmcp_format:team_stats(Stats)};
                {error, E} -> {error, err_text(E)}
            end
    end;

do_call(<<"head_to_head">>, Args) ->
    case {arg_str(Args, <<"team1">>), arg_str(Args, <<"team2">>)} of
        {T1, T2} when T1 =/= undefined, T2 =/= undefined ->
            case bsmcp_query:head_to_head(T1, T2) of
                {ok, Result} ->
                    {ok, bsmcp_format:matches(Result, arg_limit(Args, 20))};
                {error, E} -> {error, err_text(E)}
            end;
        _ ->
            {error, <<"Missing required arguments: team1 and team2">>}
    end;

do_call(<<"competition_standings">>, Args) ->
    case arg_int(Args, <<"season">>) of
        undefined ->
            {error, <<"Missing required argument: season (e.g. 2019)">>};
        Season ->
            Comp = arg_str(Args, <<"competition">>),
            {ok, Result} = bsmcp_query:standings(Comp, Season),
            {ok, bsmcp_format:standings(Result, arg_limit(Args, 30))}
    end;

do_call(<<"search_players">>, Args) ->
    Opts = maps:filter(
             fun(_, V) -> V =/= undefined end,
             #{name => arg_str(Args, <<"name">>),
               nationality => arg_str(Args, <<"nationality">>),
               club => arg_str(Args, <<"club">>),
               position => arg_str(Args, <<"position">>),
               min_overall => arg_int(Args, <<"min_overall">>)}),
    {ok, Ps} = bsmcp_query:search_players(Opts),
    {ok, bsmcp_format:players(Ps, arg_limit(Args, 10))};

do_call(<<"league_stats">>, Args) ->
    Opts = maps:filter(
             fun(_, V) -> V =/= undefined end,
             #{competition => arg_str(Args, <<"competition">>),
               season => arg_int(Args, <<"season">>)}),
    {ok, Stats} = bsmcp_query:league_stats(Opts),
    {ok, bsmcp_format:league_stats(Stats)};

do_call(<<"biggest_wins">>, Args) ->
    Opts = maps:filter(
             fun(_, V) -> V =/= undefined end,
             #{competition => arg_str(Args, <<"competition">>),
               season => arg_int(Args, <<"season">>)}),
    {ok, Ms} = bsmcp_query:biggest_wins(Opts),
    {ok, bsmcp_format:biggest_wins(Ms, arg_limit(Args, 10))};

do_call(<<"data_summary">>, _Args) ->
    {ok, bsmcp_format:data_summary(bsmcp_query:data_summary())};

do_call(Name, _Args) ->
    {error, iolist_to_binary(io_lib:format("Unknown tool: ~ts", [Name]))}.

err_text({unknown_team, Name}) ->
    iolist_to_binary(
      io_lib:format("Team \"~ts\" was not found in the dataset. Check the "
                    "spelling, or use data_summary to see what is loaded.",
                    [Name]));
err_text(Other) ->
    iolist_to_binary(io_lib:format("~p", [Other])).

%%% Argument helpers -----------------------------------------------------------

arg_str(Args, Key) ->
    case maps:get(Key, Args, undefined) of
        undefined -> undefined;
        null -> undefined;
        <<>> -> undefined;
        B when is_binary(B) -> B;
        I when is_integer(I) -> integer_to_binary(I);
        _ -> undefined
    end.

arg_int(Args, Key) ->
    case maps:get(Key, Args, undefined) of
        I when is_integer(I) -> I;
        F when is_float(F) -> round(F);
        B when is_binary(B) ->
            try binary_to_integer(string:trim(B))
            catch _:_ -> undefined
            end;
        _ -> undefined
    end.

arg_limit(Args, Default) ->
    case arg_int(Args, <<"limit">>) of
        I when is_integer(I), I > 0 -> min(I, 500);
        _ -> Default
    end.
