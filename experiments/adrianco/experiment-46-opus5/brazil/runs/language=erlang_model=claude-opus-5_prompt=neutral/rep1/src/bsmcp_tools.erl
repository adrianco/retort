%%%-------------------------------------------------------------------
%%% @doc MCP tool catalogue and dispatcher.
%%%
%%% Context: this module is the contract the LLM sees.  Each entry
%%% carries a JSON Schema for its arguments and a description written
%%% for a model that has to pick a tool from a natural language question
%%% ("Who won the 2019 Brasileirão?" -> standings).  Arguments arrive as
%%% decoded JSON (binary keys, string/number values) and are coerced
%%% here into the atom-keyed option maps {@link bsmcp_query} expects;
%%% enum values are matched against a whitelist so no user input is ever
%%% turned into an atom.
%%%
%%% Every call returns both a `structuredContent' map and a text block
%%% rendered by {@link bsmcp_format}.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_tools).

-export([list/0, call/2, names/0]).

%%====================================================================
%% Catalogue
%%====================================================================

-spec names() -> [binary()].
names() -> [maps:get(name, T) || T <- list()].

-spec list() -> [map()].
list() ->
    [#{name => <<"search_matches">>,
       description => <<"Find matches by team, opponent, competition, season "
                        "or date range. Use this for questions like 'show me "
                        "all Flamengo vs Fluminense matches', 'what matches did "
                        "Palmeiras play in 2023' or 'Copa do Brasil finals'. "
                        "Team names are matched loosely: 'Sao Paulo', "
                        "'São Paulo FC' and 'Sao Paulo-SP' all work."/utf8>>,
       inputSchema => object(match_filter_props() ++
                                 [{<<"order">>, enum(<<"Sort order by date">>,
                                                     [<<"date_desc">>, <<"date_asc">>])},
                                  {<<"limit">>, int(<<"Maximum matches to return (default 20)">>)}],
                             [])},

     #{name => <<"head_to_head">>,
       description => <<"Complete head-to-head record between two clubs: wins, "
                        "draws, goals, a per-competition breakdown and the most "
                        "recent meetings. Use for 'compare Palmeiras and Santos' "
                        "or 'when did Flamengo last play Corinthians'.">>,
       inputSchema => object([{<<"team_a">>, str(<<"First club">>)},
                              {<<"team_b">>, str(<<"Second club">>)},
                              {<<"competition">>, competition_prop()},
                              {<<"season">>, int(<<"Restrict to one season">>)},
                              {<<"season_from">>, int(<<"First season (inclusive)">>)},
                              {<<"season_to">>, int(<<"Last season (inclusive)">>)},
                              {<<"limit">>, int(<<"How many recent matches to list">>)}],
                             [<<"team_a">>, <<"team_b">>])},

     #{name => <<"team_stats">>,
       description => <<"Win/draw/loss record, goals for and against, points and "
                        "win rate for one club, with home and away splits. "
                        "Filter by season, competition or venue for questions "
                        "like 'what is Corinthians home record in 2022'.">>,
       inputSchema => object([{<<"team">>, str(<<"Club name">>)},
                              {<<"competition">>, competition_prop()},
                              {<<"season">>, int(<<"Season year, e.g. 2022">>)},
                              {<<"seasons">>, int_array(<<"Several seasons">>)},
                              {<<"season_from">>, int(<<"First season (inclusive)">>)},
                              {<<"season_to">>, int(<<"Last season (inclusive)">>)},
                              {<<"venue">>, venue_prop()},
                              {<<"date_from">>, str(<<"ISO date, e.g. 2019-01-01">>)},
                              {<<"date_to">>, str(<<"ISO date, e.g. 2019-12-31">>)}],
                             [<<"team">>])},

     #{name => <<"team_profile">>,
       description => <<"Everything the graph knows about a club: overall "
                        "record, which competitions and seasons it appears in, "
                        "first and last match, biggest win and its highest "
                        "rated FIFA players. Use for 'what competitions has "
                        "Palmeiras played in'.">>,
       inputSchema => object([{<<"team">>, str(<<"Club name">>)}], [<<"team">>])},

     #{name => <<"standings">>,
       description => <<"League table for a season, calculated from the match "
                        "results (3 points for a win). Reports the champion and "
                        "the relegation zone when the season is complete in the "
                        "data. Use for 'who won the 2019 Brasileirão' or 'which "
                        "teams were relegated in 2020'."/utf8>>,
       inputSchema => object([{<<"competition">>, competition_prop()},
                              {<<"season">>, int(<<"Season year, e.g. 2019">>)}],
                             [<<"season">>])},

     #{name => <<"league_leaderboard">>,
       description => <<"Rank clubs by an aggregate metric (points, goals for or "
                        "against, wins, win rate, home or away record) over any "
                        "competition/season filter. Use for 'which team scored "
                        "the most goals in Serie A 2023' or 'which team has the "
                        "best away record'.">>,
       inputSchema => object([{<<"metric">>, enum(<<"Metric to rank by">>,
                                                  [<<"points">>, <<"wins">>, <<"draws">>,
                                                   <<"losses">>, <<"goals_for">>,
                                                   <<"goals_against">>, <<"goal_difference">>,
                                                   <<"win_rate">>, <<"points_per_match">>,
                                                   <<"home_win_rate">>, <<"away_win_rate">>,
                                                   <<"home_points">>, <<"away_points">>])},
                              {<<"competition">>, competition_prop()},
                              {<<"season">>, int(<<"Season year">>)},
                              {<<"seasons">>, int_array(<<"Several seasons">>)},
                              {<<"season_from">>, int(<<"First season">>)},
                              {<<"season_to">>, int(<<"Last season">>)},
                              {<<"venue">>, venue_prop()},
                              {<<"min_played">>, int(<<"Ignore clubs below this many matches">>)},
                              {<<"limit">>, int(<<"How many clubs to return">>)}],
                             [])},

     #{name => <<"biggest_wins">>,
       description => <<"Matches ordered by winning margin, optionally filtered "
                        "by competition or season. With a team filter it returns "
                        "that club's biggest wins. Use for 'show me the biggest "
                        "wins in the dataset' or 'Santos' biggest win'.">>,
       inputSchema => object(match_filter_props() ++
                                 [{<<"limit">>, int(<<"How many matches (default 20)">>)}],
                             [])},

     #{name => <<"competition_stats">>,
       description => <<"Aggregate statistics for a competition: goals per "
                        "match, home/away/draw split, high scoring and goalless "
                        "percentages, broken down by season. Use for 'average "
                        "goals per match in the Brasileirão' or 'compare the "
                        "2018 and 2019 seasons'."/utf8>>,
       inputSchema => object([{<<"competition">>, competition_prop()},
                              {<<"season">>, int(<<"Season year">>)},
                              {<<"seasons">>, int_array(<<"Several seasons to compare">>)},
                              {<<"season_from">>, int(<<"First season">>)},
                              {<<"season_to">>, int(<<"Last season">>)},
                              {<<"team">>, str(<<"Restrict to one club">>)},
                              {<<"date_from">>, str(<<"ISO date lower bound">>)},
                              {<<"date_to">>, str(<<"ISO date upper bound">>)}],
                             [])},

     #{name => <<"search_players">>,
       description => <<"Search the FIFA player database by name, nationality, "
                        "club, position or rating. Positions accept both codes "
                        "(ST, GK, CB) and groups (forward, midfielder, "
                        "defender, goalkeeper). Use for 'find all Brazilian "
                        "players', 'highest rated players at Flamengo' or 'show "
                        "me all forwards from São Paulo FC'."/utf8>>,
       inputSchema => object([{<<"name">>, str(<<"Full or partial player name">>)},
                              {<<"nationality">>, str(<<"Country, e.g. Brazil">>)},
                              {<<"club">>, str(<<"Club name">>)},
                              {<<"position">>, str(<<"Position code or group">>)},
                              {<<"min_overall">>, int(<<"Minimum FIFA overall rating">>)},
                              {<<"max_overall">>, int(<<"Maximum FIFA overall rating">>)},
                              {<<"min_potential">>, int(<<"Minimum potential rating">>)},
                              {<<"min_age">>, int(<<"Minimum age">>)},
                              {<<"max_age">>, int(<<"Maximum age">>)},
                              {<<"sort">>, enum(<<"Sort order">>,
                                                [<<"overall">>, <<"potential">>,
                                                 <<"age">>, <<"oldest">>, <<"name">>])},
                              {<<"limit">>, int(<<"How many players (default 20)">>)}],
                             [])},

     #{name => <<"player_profile">>,
       description => <<"Full FIFA profile for one player: ratings, club, "
                        "position, physical data, contract and top attributes. "
                        "Use for 'who is Gabriel Barbosa'.">>,
       inputSchema => object([{<<"name">>, str(<<"Player name">>)}], [<<"name">>])},

     #{name => <<"club_squad">>,
       description => <<"The FIFA squad of a club with average rating and age, "
                        "linked to the club's match record when the club also "
                        "appears in the match data. Use for 'which players play "
                        "for Flamengo'.">>,
       inputSchema => object([{<<"club">>, str(<<"Club name">>)},
                              {<<"sort">>, enum(<<"Sort order">>,
                                                [<<"overall">>, <<"potential">>,
                                                 <<"age">>, <<"oldest">>, <<"name">>])},
                              {<<"limit">>, int(<<"How many players (default 20)">>)}],
                             [<<"club">>])},

     #{name => <<"club_ratings">>,
       description => <<"Group players by club with squad size and average "
                        "rating, optionally filtered by nationality or "
                        "restricted to clubs that appear in the Brazilian match "
                        "data. Use for 'Brazilian players at Brazilian clubs'.">>,
       inputSchema => object([{<<"nationality">>, str(<<"Player nationality, e.g. Brazil">>)},
                              {<<"brazilian_clubs_only">>,
                               bool(<<"Only clubs that appear in the match data">>)},
                              {<<"min_players">>, int(<<"Ignore clubs below this squad size">>)},
                              {<<"limit">>, int(<<"How many clubs (default 20)">>)}],
                             [])},

     #{name => <<"list_teams">>,
       description => <<"Resolve or browse clubs and show every spelling of "
                        "their name found in the source files. Useful to "
                        "disambiguate 'Botafogo' (RJ, SP or PB) or to check how "
                        "a club is written before another query.">>,
       inputSchema => object([{<<"query">>, str(<<"Club name or fragment; omit to list all">>)},
                              {<<"limit">>, int(<<"How many clubs (default 20)">>)}],
                             [])},

     #{name => <<"dataset_summary">>,
       description => <<"What is loaded: source files, row counts, competitions, "
                        "seasons and the de-duplication note. Call this first if "
                        "you are unsure what the data covers.">>,
       inputSchema => object([], [])}].

%%====================================================================
%% Dispatch
%%====================================================================

%% @doc Run a tool. Returns `{ok, Structured, Text}' or
%% `{error, Structured, Text}' (a tool level error, not a protocol one).
-spec call(binary(), map()) -> {ok, map(), binary()} | {error, map(), binary()}.
call(Name, Args) when is_map(Args) ->
    case tool_atom(Name) of
        undefined ->
            E = #{error => unknown_tool, message => <<"No such tool">>, tool => Name},
            {error, E, <<"Unknown tool: ", Name/binary>>};
        Tool ->
            run(Tool, decode_args(Tool, Args))
    end.

run(Tool, Opts) ->
    Result = case Tool of
                 search_matches -> bsmcp_query:search_matches(Opts);
                 head_to_head -> bsmcp_query:head_to_head(Opts);
                 team_stats -> bsmcp_query:team_stats(Opts);
                 team_profile -> bsmcp_query:team_profile(Opts);
                 standings -> bsmcp_query:standings(Opts);
                 league_leaderboard -> bsmcp_query:leaderboard(Opts);
                 biggest_wins -> bsmcp_query:biggest_wins(Opts);
                 competition_stats -> bsmcp_query:competition_stats(Opts);
                 search_players -> bsmcp_query:search_players(Opts);
                 player_profile -> bsmcp_query:player_profile(Opts);
                 club_squad -> bsmcp_query:club_squad(Opts);
                 club_ratings -> bsmcp_query:club_ratings(Opts);
                 list_teams -> bsmcp_query:list_teams(Opts);
                 dataset_summary -> bsmcp_query:dataset_summary()
             end,
    case Result of
        {error, E} -> {error, E, bsmcp_format:error_text(E)};
        Map -> {ok, Map, bsmcp_format:render(Tool, Map)}
    end.

tool_atom(Name) ->
    Known = [{<<"search_matches">>, search_matches},
             {<<"head_to_head">>, head_to_head},
             {<<"team_stats">>, team_stats},
             {<<"team_profile">>, team_profile},
             {<<"standings">>, standings},
             {<<"league_leaderboard">>, league_leaderboard},
             {<<"biggest_wins">>, biggest_wins},
             {<<"competition_stats">>, competition_stats},
             {<<"search_players">>, search_players},
             {<<"player_profile">>, player_profile},
             {<<"club_squad">>, club_squad},
             {<<"club_ratings">>, club_ratings},
             {<<"list_teams">>, list_teams},
             {<<"dataset_summary">>, dataset_summary}],
    proplists:get_value(Name, Known).

%%====================================================================
%% Argument decoding
%%====================================================================

decode_args(Tool, Args) ->
    maps:from_list([{K, V} || {K, Type} <- arg_spec(Tool),
                              V <- [coerce(Type, get_arg(K, Args))],
                              V =/= undefined]).

get_arg(Key, Args) ->
    maps:get(atom_to_binary(Key, utf8), Args, undefined).

coerce(_Type, undefined) -> undefined;
coerce(_Type, null) -> undefined;
coerce(string, V) when is_binary(V) -> V;
coerce(string, V) when is_integer(V) -> integer_to_binary(V);
coerce(string, _) -> undefined;
coerce(integer, V) when is_integer(V) -> V;
coerce(integer, V) when is_float(V) -> round(V);
coerce(integer, V) when is_binary(V) -> bsmcp_text:to_int(V);
coerce(integer, _) -> undefined;
coerce(boolean, true) -> true;
coerce(boolean, false) -> false;
coerce(boolean, <<"true">>) -> true;
coerce(boolean, <<"false">>) -> false;
coerce(boolean, _) -> undefined;
coerce(integer_list, V) when is_list(V) ->
    case [I || X <- V, I <- [coerce(integer, X)], I =/= undefined] of
        [] -> undefined;
        L -> L
    end;
coerce(integer_list, V) -> coerce(integer_list, [V]);
coerce({enum, Allowed}, V) when is_binary(V) ->
    Norm = bsmcp_text:normalize(V),
    case [A || A <- Allowed, bsmcp_text:normalize(atom_to_binary(A, utf8)) =:= Norm] of
        [A | _] -> A;
        [] -> undefined
    end;
coerce({enum, _}, _) -> undefined.

%% Which arguments each tool understands, and how to coerce them.
arg_spec(search_matches) ->
    match_filter_spec() ++ [{order, {enum, [date_desc, date_asc]}}, {limit, integer}];
arg_spec(biggest_wins) ->
    match_filter_spec() ++ [{limit, integer}];
arg_spec(head_to_head) ->
    [{team_a, string}, {team_b, string}, {competition, string}, {season, integer},
     {seasons, integer_list}, {season_from, integer}, {season_to, integer},
     {limit, integer}];
arg_spec(team_stats) ->
    [{team, string}, {competition, string}, {season, integer}, {seasons, integer_list},
     {season_from, integer}, {season_to, integer}, {venue, {enum, [home, away]}},
     {date_from, string}, {date_to, string}];
arg_spec(team_profile) ->
    [{team, string}];
arg_spec(standings) ->
    [{competition, string}, {season, integer}];
arg_spec(league_leaderboard) ->
    [{metric, {enum, [points, wins, draws, losses, goals_for, goals_against,
                      goal_difference, win_rate, points_per_match, home_win_rate,
                      away_win_rate, home_points, away_points]}},
     {competition, string}, {season, integer}, {seasons, integer_list},
     {season_from, integer}, {season_to, integer}, {team, string},
     {venue, {enum, [home, away]}}, {min_played, integer}, {limit, integer}];
arg_spec(competition_stats) ->
    [{competition, string}, {season, integer}, {seasons, integer_list},
     {season_from, integer}, {season_to, integer}, {team, string},
     {date_from, string}, {date_to, string}];
arg_spec(search_players) ->
    [{name, string}, {nationality, string}, {club, string}, {position, string},
     {min_overall, integer}, {max_overall, integer}, {min_potential, integer},
     {min_age, integer}, {max_age, integer},
     {sort, {enum, [overall, potential, age, oldest, name]}}, {limit, integer}];
arg_spec(player_profile) ->
    [{name, string}];
arg_spec(club_squad) ->
    [{club, string}, {sort, {enum, [overall, potential, age, oldest, name]}},
     {limit, integer}];
arg_spec(club_ratings) ->
    [{nationality, string}, {brazilian_clubs_only, boolean}, {min_players, integer},
     {limit, integer}];
arg_spec(list_teams) ->
    [{query, string}, {limit, integer}];
arg_spec(dataset_summary) ->
    [].

match_filter_spec() ->
    [{team, string}, {opponent, string}, {home_team, string}, {away_team, string},
     {competition, string}, {season, integer}, {seasons, integer_list},
     {season_from, integer}, {season_to, integer}, {date_from, string},
     {date_to, string}, {venue, {enum, [home, away]}}, {round, string},
     {stage, string}, {played_only, boolean}].

%%====================================================================
%% JSON Schema helpers
%%====================================================================

match_filter_props() ->
    [{<<"team">>, str(<<"Club involved in the match (home or away)">>)},
     {<<"opponent">>, str(<<"Second club, to get meetings between two clubs">>)},
     {<<"home_team">>, str(<<"Club playing at home">>)},
     {<<"away_team">>, str(<<"Club playing away">>)},
     {<<"competition">>, competition_prop()},
     {<<"season">>, int(<<"Season year, e.g. 2019">>)},
     {<<"seasons">>, int_array(<<"Several seasons">>)},
     {<<"season_from">>, int(<<"First season (inclusive)">>)},
     {<<"season_to">>, int(<<"Last season (inclusive)">>)},
     {<<"date_from">>, str(<<"ISO date lower bound, e.g. 2019-01-01">>)},
     {<<"date_to">>, str(<<"ISO date upper bound, e.g. 2019-12-31">>)},
     {<<"venue">>, venue_prop()},
     {<<"round">>, str(<<"League round number or cup round">>)},
     {<<"stage">>, str(<<"Tournament stage, e.g. final, semifinals, group stage">>)},
     {<<"played_only">>, bool(<<"Skip fixtures with no recorded score">>)}].

competition_prop() ->
    enum(<<"Competition: brasileirao (Serie A), serie b, serie c, copa do brasil "
           "or libertadores">>,
         [<<"serie a">>, <<"serie b">>, <<"serie c">>, <<"copa do brasil">>,
          <<"libertadores">>]).

venue_prop() ->
    enum(<<"Restrict to home or away matches of the team filter">>,
         [<<"home">>, <<"away">>]).

object(Props, Required) ->
    Base = #{type => <<"object">>, properties => maps:from_list(Props)},
    case Required of
        [] -> Base;
        _ -> Base#{required => Required}
    end.

str(Desc) -> #{type => <<"string">>, description => Desc}.
int(Desc) -> #{type => <<"integer">>, description => Desc}.
bool(Desc) -> #{type => <<"boolean">>, description => Desc}.
int_array(Desc) -> #{type => <<"array">>, items => #{type => <<"integer">>},
                     description => Desc}.
enum(Desc, Values) -> #{type => <<"string">>, description => Desc, enum => Values}.
