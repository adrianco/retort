%% @doc MCP tool definitions and dispatch.
%%
%% `list/0' returns the tool catalog (name/description/inputSchema maps);
%% `call/3' runs one tool against a store `#{matches => [...], players =>
%% [...]}' and returns `{ok, Text}' or `{error, Reason}'.
-module(bsmcp_tools).

-export([list/0, call/3]).

-define(DEFAULT_LIMIT, 25).

%% --- catalog ----------------------------------------------------------

-spec list() -> [map()].
list() ->
    [tool(<<"find_matches">>,
          <<"Find soccer matches by team, opponent, season, competition or venue. "
            "All arguments are optional; combine them to narrow the search.">>,
          #{<<"team">> => str(<<"Team name (matches home or away). Suffixes like '-SP' are ignored.">>),
            <<"opponent">> => str(<<"Restrict to matches against this opponent.">>),
            <<"home_team">> => str(<<"Team that played at home.">>),
            <<"away_team">> => str(<<"Team that played away.">>),
            <<"season">> => int(<<"Season year, e.g. 2019.">>),
            <<"competition">> => str(<<"Competition name: Brasileirão, Copa do Brasil or Libertadores."/utf8>>),
            <<"limit">> => int(<<"Maximum number of matches to show (default 25).">>)},
          []),
     tool(<<"head_to_head">>,
          <<"Head-to-head record and match list between two teams.">>,
          #{<<"team_a">> => str(<<"First team.">>),
            <<"team_b">> => str(<<"Second team.">>)},
          [<<"team_a">>, <<"team_b">>]),
     tool(<<"team_record">>,
          <<"Aggregate win/draw/loss record, goals and win rate for a team.">>,
          #{<<"team">> => str(<<"Team name.">>),
            <<"season">> => int(<<"Restrict to a season year.">>),
            <<"competition">> => str(<<"Restrict to a competition.">>),
            <<"home_only">> => bool(<<"Only count home matches.">>),
            <<"away_only">> => bool(<<"Only count away matches.">>)},
          [<<"team">>]),
     tool(<<"find_players">>,
          <<"Search FIFA players by name, nationality, club, position or rating.">>,
          #{<<"name">> => str(<<"Player name (substring match).">>),
            <<"nationality">> => str(<<"Nationality, e.g. Brazil.">>),
            <<"club">> => str(<<"Club name (substring match).">>),
            <<"position">> => str(<<"Position code, e.g. ST, GK, LW.">>),
            <<"min_overall">> => int(<<"Minimum FIFA overall rating.">>),
            <<"limit">> => int(<<"Maximum number of players to show (default 25).">>)},
          []),
     tool(<<"standings">>,
          <<"League table for a competition and season, computed from match results.">>,
          #{<<"competition">> => str(<<"Competition name.">>),
            <<"season">> => int(<<"Season year.">>)},
          [<<"competition">>, <<"season">>]),
     tool(<<"match_statistics">>,
          <<"Aggregate statistics (average goals, home win rate, biggest wins) "
            "for a competition/season, optionally filtered by team.">>,
          #{<<"competition">> => str(<<"Restrict to a competition.">>),
            <<"season">> => int(<<"Restrict to a season year.">>),
            <<"team">> => str(<<"Restrict to a team's matches.">>)},
          [])].

tool(Name, Desc, Props, Required) ->
    #{name => Name,
      description => Desc,
      inputSchema => #{<<"type">> => <<"object">>,
                       <<"properties">> => Props,
                       <<"required">> => Required}}.

str(D) -> #{<<"type">> => <<"string">>, <<"description">> => D}.
int(D) -> #{<<"type">> => <<"integer">>, <<"description">> => D}.
bool(D) -> #{<<"type">> => <<"boolean">>, <<"description">> => D}.

%% --- dispatch ---------------------------------------------------------

-spec call(binary(), map(), map()) -> {ok, binary()} | {error, binary()}.
call(<<"find_matches">>, Args, Store) ->
    Matches = maps:get(matches, Store),
    Opts = match_opts(Args),
    Found = bsmcp_query:find_matches(Matches, Opts),
    {ok, limited_matches(Found, limit(Args))};
call(<<"head_to_head">>, Args, Store) ->
    with_required([<<"team_a">>, <<"team_b">>], Args,
        fun() ->
            A = maps:get(<<"team_a">>, Args),
            B = maps:get(<<"team_b">>, Args),
            {Ms, Rec} = bsmcp_query:head_to_head(maps:get(matches, Store), A, B),
            {ok, bsmcp_format:head_to_head(A, B, Ms, Rec)}
        end);
call(<<"team_record">>, Args, Store) ->
    with_required([<<"team">>], Args,
        fun() ->
            Team = maps:get(<<"team">>, Args),
            Rec = bsmcp_query:team_record(maps:get(matches, Store), Team,
                                          record_opts(Args)),
            {ok, bsmcp_format:team_record(Team, Rec)}
        end);
call(<<"find_players">>, Args, Store) ->
    Players = maps:get(players, Store),
    Found = bsmcp_query:find_players(Players, player_opts(Args)),
    {ok, limited_players(Found, limit(Args))};
call(<<"standings">>, Args, Store) ->
    with_required([<<"competition">>, <<"season">>], Args,
        fun() ->
            Comp = maps:get(<<"competition">>, Args),
            Season = maps:get(<<"season">>, Args),
            S = bsmcp_query:standings(maps:get(matches, Store), Comp, Season),
            {ok, bsmcp_format:standings(Comp, Season, S)}
        end);
call(<<"match_statistics">>, Args, Store) ->
    Ms0 = maps:get(matches, Store),
    Ms = bsmcp_query:find_matches(Ms0, match_opts(Args)),
    {ok, statistics_text(Ms)};
call(Name, _Args, _Store) ->
    {error, <<"Unknown tool: ", Name/binary>>}.

%% --- arg extraction ---------------------------------------------------

match_opts(Args) ->
    collect(Args,
            [{<<"team">>, team}, {<<"opponent">>, opponent},
             {<<"home_team">>, home_team}, {<<"away_team">>, away_team},
             {<<"season">>, season}, {<<"competition">>, competition}]).

record_opts(Args) ->
    collect(Args,
            [{<<"season">>, season}, {<<"competition">>, competition},
             {<<"home_only">>, home_only}, {<<"away_only">>, away_only}]).

player_opts(Args) ->
    collect(Args,
            [{<<"name">>, name}, {<<"nationality">>, nationality},
             {<<"club">>, club}, {<<"position">>, position},
             {<<"min_overall">>, min_overall}]).

collect(Args, Mapping) ->
    lists:foldl(
      fun({SrcKey, DstKey}, Acc) ->
              case maps:find(SrcKey, Args) of
                  {ok, V} when V =/= null, V =/= <<>> -> Acc#{DstKey => V};
                  _ -> Acc
              end
      end, #{}, Mapping).

limit(Args) ->
    case maps:get(<<"limit">>, Args, ?DEFAULT_LIMIT) of
        N when is_integer(N), N > 0 -> N;
        _ -> ?DEFAULT_LIMIT
    end.

%% --- rendering helpers ------------------------------------------------

limited_matches(Found, Limit) ->
    Total = length(Found),
    Sorted = lists:sort(fun(A, B) ->
                            maps:get(date, A, <<>>) >= maps:get(date, B, <<>>)
                        end, Found),
    Shown = lists:sublist(Sorted, Limit),
    Body = bsmcp_format:matches(Shown),
    maybe_truncation(Body, Total, length(Shown)).

limited_players(Found, Limit) ->
    Total = length(Found),
    Shown = lists:sublist(Found, Limit),
    Body = bsmcp_format:players(Shown),
    maybe_truncation(Body, Total, length(Shown)).

maybe_truncation(Body, Total, Shown) when Shown < Total ->
    Note = iolist_to_binary(["\n\nShowing ", integer_to_binary(Shown),
                             " of ", integer_to_binary(Total),
                             " results (use 'limit' to see more)."]),
    <<Body/binary, Note/binary>>;
maybe_truncation(Body, _Total, _Shown) ->
    Body.

statistics_text(Ms) ->
    Avg = bsmcp_query:avg_goals(Ms),
    HomeRate = bsmcp_query:home_win_rate(Ms),
    Biggest = bsmcp_query:biggest_wins(Ms, 5),
    Header = ["Statistics over ", integer_to_binary(length(Ms)), " matches:\n",
              "- Average goals per match: ", float_to_binary(Avg, [{decimals, 2}]), "\n",
              "- Home win rate: ", float_to_binary(HomeRate, [{decimals, 1}]), "%\n",
              "- Biggest wins:"],
    Lines = [["\n  ", bsmcp_format:match_line(M)] || M <- Biggest],
    iolist_to_binary([Header | Lines]).

%% --- validation -------------------------------------------------------

with_required(Keys, Args, Fun) ->
    Missing = [K || K <- Keys, not present(K, Args)],
    case Missing of
        [] -> Fun();
        _ ->
            Names = lists:join(<<", ">>, Missing),
            {error, iolist_to_binary(["Missing required argument(s): ", Names])}
    end.

present(K, Args) ->
    case maps:find(K, Args) of
        {ok, V} when V =/= null, V =/= <<>> -> true;
        _ -> false
    end.
