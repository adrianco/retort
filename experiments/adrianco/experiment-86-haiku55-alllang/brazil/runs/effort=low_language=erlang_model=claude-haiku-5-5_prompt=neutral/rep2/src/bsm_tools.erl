%% @doc MCP tool catalogue: JSON Schemas for each tool and the handlers that
%% turn tool arguments into query filters and JSON results.
-module(bsm_tools).
-export([definitions/0, call/2]).
-include("bsm.hrl").

-spec definitions() -> [map()].
definitions() ->
    [
     tool(<<"find_teams">>,
          <<"Look up canonical team names before querying. Accepts partial, accented or state-suffixed names (e.g. 'atletico', 'Grêmio', 'Palmeiras-SP')."/utf8>>,
          #{query => str(<<"Name fragment; empty lists all teams">>),
            limit => int(<<"Max results (default 20)">>)},
          []),
     tool(<<"search_matches">>,
          <<"Find matches across Brasileirão (Serie A/B/C), Copa do Brasil and Copa Libertadores. Newest first. With team alone, returns matches for that team (home or away); with team and opponent, returns head-to-head matches."/utf8>>,
          #{team => str(<<"Team name, e.g. Flamengo or Palmeiras-SP">>),
            opponent => str(<<"Second team; used with team for head-to-head">>),
            competition => str(<<"Competition fragment, e.g. Brasileirão, Copa do Brasil, Libertadores"/utf8>>),
            season => int(<<"Season year, e.g. 2023">>),
            date_from => str(<<"Earliest date: YYYY-MM-DD or DD/MM/YYYY">>),
            date_to => str(<<"Latest date: YYYY-MM-DD or DD/MM/YYYY">>),
            venue => enum([<<"home">>, <<"away">>, <<"any">>], <<"Restrict team to home or away games (default any)">>),
            limit => int(<<"Max matches to return (default 20)">>)},
          []),
     tool(<<"team_record">>,
          <<"Win/draw/loss record, goals for/against and win rate for a team, with optional competition, season, date and venue filters.">>,
          #{team => str(<<"Team name">>),
            competition => str(<<"Competition fragment">>),
            season => int(<<"Season year">>),
            date_from => str(<<"Earliest date">>),
            date_to => str(<<"Latest date">>),
            venue => enum([<<"home">>, <<"away">>, <<"any">>], <<"Home, away or any (default any)">>)},
          [<<"team">>]),
     tool(<<"head_to_head">>,
          <<"Head-to-head record between two teams: wins, draws, goals, and the most recent matches.">>,
          #{team_a => str(<<"First team">>),
            team_b => str(<<"Second team">>),
            competition => str(<<"Competition fragment">>),
            season => int(<<"Season year">>),
            limit => int(<<"Max recent matches to list (default 20)">>)},
          [<<"team_a">>, <<"team_b">>]),
     tool(<<"standings">>,
          <<"Brasileirão Série A table for a season, calculated from match results (3 pts win, 1 draw). Ties: wins, goal difference, goals scored."/utf8>>,
          #{season => int(<<"Season year, e.g. 2019">>)},
          [<<"season">>]),
     tool(<<"league_stats">>,
          <<"Aggregate statistics: matches, average goals per match, home/draw/away percentages and the biggest wins.">>,
          #{competition => str(<<"Competition fragment">>),
            season => int(<<"Season year">>)},
          []),
     tool(<<"search_players">>,
          <<"Search the FIFA player database. Sorted by overall rating, highest first.">>,
          #{name => str(<<"Name fragment, e.g. Neymar">>),
            nationality => str(<<"Exact nationality, e.g. Brazil">>),
            club => str(<<"Club name fragment, e.g. Flamengo">>),
            position => str(<<"Position code, e.g. ST, GK, CAM">>),
            min_overall => int(<<"Minimum overall rating">>),
            limit => int(<<"Max players to return (default 20)">>)},
          [])
    ].

-spec call(binary(), map()) -> {ok, binary()} | {error, binary() | unknown_tool}.
call(Name, Args) ->
    try dispatch(Name, Args)
    catch throw:{bad_argument, Msg} -> {error, Msg}
    end.

dispatch(<<"find_teams">>, A) ->
    Teams = bsm_query:find_teams(bsm_store:matches(), text(A, <<"query">>)),
    Limit = int(A, <<"limit">>, ?DEFAULT_LIMIT),
    json(#{total => length(Teams),
           teams => [#{name => maps:get(name, T), state => maps:get(state, T)}
                     || T <- lists:sublist(Teams, Limit)]});

dispatch(<<"search_matches">>, A) ->
    All = bsm_query:find_matches(bsm_store:matches(), filters(A)),
    Shown = lists:sublist(All, int(A, <<"limit">>, ?DEFAULT_LIMIT)),
    json(#{total => length(All), returned => length(Shown),
           matches => [match_json(M) || M <- Shown]});

dispatch(<<"team_record">>, A) ->
    Team = required_team(A, <<"team">>),
    json(bsm_query:team_record(bsm_store:matches(), Team, filters(A)));

dispatch(<<"head_to_head">>, A) ->
    R = bsm_query:head_to_head(bsm_store:matches(), required_team(A, <<"team_a">>),
                               required_team(A, <<"team_b">>), filters(A)),
    #{recent := Recent} = R,
    json(R#{recent => [match_json(M) || M <- lists:sublist(Recent, int(A, <<"limit">>, ?DEFAULT_LIMIT))]});

dispatch(<<"standings">>, A) ->
    Season = required_int(A, <<"season">>),
    json(#{competition => ?SERIE_A, season => Season,
           table => bsm_query:standings(bsm_store:matches(), Season)});

dispatch(<<"league_stats">>, A) ->
    R = bsm_query:league_stats(bsm_store:matches(), filters(A)),
    #{biggest_wins := Wins} = R,
    json(R#{biggest_wins => [match_json(M) || M <- Wins]});

dispatch(<<"search_players">>, A) ->
    F = #{name => text(A, <<"name">>), nationality => text(A, <<"nationality">>),
          club => text(A, <<"club">>), position => text(A, <<"position">>),
          min_overall => int(A, <<"min_overall">>, 0)},
    All = bsm_query:search_players(bsm_store:players(), F),
    Shown = lists:sublist(All, int(A, <<"limit">>, ?DEFAULT_LIMIT)),
    json(#{total => length(All), returned => length(Shown),
           players => [player_json(P) || P <- Shown]});

dispatch(_Unknown, _Args) ->
    {error, unknown_tool}.

%% --- argument handling -----------------------------------------------------

filters(A) ->
    F1 = opt_filter(<<"competition">>, competition, fun(V) -> V end, A, #{venue => venue(A)}),
    F2 = opt_filter(<<"season">>, season, fun(V) -> int_value(<<"season">>, V) end, A, F1),
    F3 = opt_filter(<<"date_from">>, date_from, fun(V) -> date_value(<<"date_from">>, V) end, A, F2),
    F4 = opt_filter(<<"date_to">>, date_to, fun(V) -> date_value(<<"date_to">>, V) end, A, F3),
    F5 = opt_filter(<<"team">>, team, fun bsm_team:parse/1, A, F4),
    opt_filter(<<"opponent">>, opponent, fun bsm_team:parse/1, A, F5).

opt_filter(ArgKey, FilterKey, Convert, A, Acc) ->
    case text(A, ArgKey) of
        <<>> -> Acc;
        V -> Acc#{FilterKey => Convert(V)}
    end.

venue(A) ->
    case text(A, <<"venue">>) of
        <<"home">> -> home;
        <<"away">> -> away;
        V when V =:= <<>>; V =:= <<"any">> -> any;
        _ -> bad_argument(<<"venue must be home, away or any">>)
    end.

required_team(A, Key) ->
    case text(A, Key) of
        <<>> -> bad_argument(<<"missing required argument: ", Key/binary>>);
        V -> bsm_team:parse(V)
    end.

required_int(A, Key) ->
    case text(A, Key) of
        <<>> -> bad_argument(<<"missing required argument: ", Key/binary>>);
        V -> int_value(Key, V)
    end.

int(A, Key, Default) ->
    case text(A, Key) of
        <<>> -> Default;
        V -> int_value(Key, V)
    end.

int_value(Key, V) ->
    try binary_to_integer(V)
    catch error:badarg -> bad_argument(<<Key/binary, " must be an integer">>)
    end.

date_value(Key, V) ->
    case bsm_date:parse(V) of
        {ok, Iso} -> Iso;
        error -> bad_argument(<<Key/binary, " must be YYYY-MM-DD or DD/MM/YYYY">>)
    end.

%% Strings are trimmed; numbers are accepted as text too so "2023" and 2023 both work.
text(A, Key) ->
    case maps:get(Key, A, null) of
        B when is_binary(B) -> bsm_text:trim(B);
        I when is_integer(I) -> integer_to_binary(I);
        _ -> <<>>
    end.

bad_argument(Msg) -> throw({bad_argument, Msg}).

%% --- output shaping --------------------------------------------------------

match_json(M) ->
    #{date => maps:get(date, M),
      competition => maps:get(competition, M),
      stage => maps:get(stage, M),
      home => maps:get(name, maps:get(home, M)),
      away => maps:get(name, maps:get(away, M)),
      home_goals => maps:get(home_goals, M),
      away_goals => maps:get(away_goals, M)}.

player_json(P) ->
    maps:with([name, age, nationality, club, position, overall, potential,
               value, wage, jersey_number, preferred_foot], P).

json(Term) ->
    {ok, iolist_to_binary(json:encode(Term))}.

%% --- schema helpers --------------------------------------------------------

tool(Name, Description, Properties, Required) ->
    #{name => Name,
      description => Description,
      inputSchema => #{type => <<"object">>,
                       properties => Properties,
                       required => Required}}.

str(Desc) -> #{type => <<"string">>, description => Desc}.
int(Desc) -> #{type => <<"integer">>, description => Desc}.
enum(Values, Desc) -> #{type => <<"string">>, enum => Values, description => Desc}.
