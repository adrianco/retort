%%% ===================================================================
%%% Brazilian Soccer MCP Server - Executable Acceptance Tests (ATDD)
%%%
%%% Context: These tests are the executable specification for the
%%% Brazilian Soccer MCP server. They are written from the perspective
%%% of an external MCP client and exercise the System Under Test ONLY
%%% through the public MCP JSON-RPC interface (`bsoccer_mcp:handle/1',
%%% which takes a JSON-RPC request and returns a JSON-RPC response).
%%% There is no back-door access to ETS tables or internal modules.
%%%
%%% Each scenario asserts on WHAT the system does in the language of the
%%% problem domain ("find matches between two teams", "team statistics",
%%% "league standings", "search players") rather than on HOW it is
%%% implemented. Scenarios are independent: the server is a read-only
%%% query interface over a fixed dataset, so no test mutates state that
%%% another test depends on, and tests may run in any order.
%%%
%%% Ground-truth values used in the assertions were derived directly
%%% from the provided CSV datasets (see data/kaggle/).
%%% ===================================================================
-module(bsoccer_acceptance_tests).

-include_lib("eunit/include/eunit.hrl").

%%% -------------------------------------------------------------------
%%% Fixture: a running server with the real datasets loaded.
%%% Loading happens once for the suite; every scenario then runs against
%%% that running-but-read-only system through the MCP protocol only.
%%% -------------------------------------------------------------------
all_test_() ->
    {setup,
     fun setup/0,
     fun cleanup/1,
     {inorder,
      [ {timeout, 30, fun protocol_initialize_handshake/0}
      , {timeout, 30, fun protocol_lists_available_tools/0}
      , {timeout, 30, fun protocol_rejects_unknown_method/0}
      , {timeout, 30, fun tool_call_unknown_tool_is_error/0}
      , {timeout, 30, fun all_datasets_are_loaded_and_queryable/0}
      , {timeout, 30, fun find_all_matches_between_two_teams/0}
      , {timeout, 30, fun find_matches_for_a_team_in_a_season/0}
      , {timeout, 30, fun find_matches_by_competition/0}
      , {timeout, 30, fun head_to_head_record_is_consistent/0}
      , {timeout, 30, fun team_statistics_for_a_season/0}
      , {timeout, 30, fun team_name_variations_are_normalised/0}
      , {timeout, 30, fun home_record_differs_from_away_record/0}
      , {timeout, 30, fun league_standings_crown_the_champion/0}
      , {timeout, 30, fun search_player_by_name/0}
      , {timeout, 30, fun search_brazilian_players/0}
      , {timeout, 30, fun search_players_by_club/0}
      , {timeout, 30, fun top_players_are_sorted_by_rating/0}
      , {timeout, 30, fun aggregate_statistics_for_a_competition/0}
      , {timeout, 30, fun biggest_wins_are_reported/0}
      , {timeout, 30, fun cross_dataset_player_then_matches/0}
      ]}}.

setup() ->
    application:set_env(bsoccer, data_dir, data_dir()),
    {ok, _} = application:ensure_all_started(bsoccer),
    ok.

cleanup(_) ->
    application:stop(bsoccer),
    ok.

%% Locate the data directory whether tests run from the project root
%% (rebar3 eunit) or from a build profile dir.
data_dir() ->
    Candidates = ["data/kaggle",
                  "../../../../data/kaggle",
                  filename:join([code:lib_dir(bsoccer), "..", "..", "data", "kaggle"])],
    case lists:dropwhile(fun(D) -> not filelib:is_dir(D) end, Candidates) of
        [Dir | _] -> Dir;
        [] -> "data/kaggle"
    end.

%%% -------------------------------------------------------------------
%%% Protocol-level scenarios
%%% -------------------------------------------------------------------

protocol_initialize_handshake() ->
    Resp = rpc(<<"initialize">>, #{}),
    Result = maps:get(<<"result">>, Resp),
    ?assert(maps:is_key(<<"protocolVersion">>, Result)),
    ?assert(maps:is_key(<<"capabilities">>, Result)),
    ServerInfo = maps:get(<<"serverInfo">>, Result),
    ?assert(maps:is_key(<<"name">>, ServerInfo)).

protocol_lists_available_tools() ->
    Resp = rpc(<<"tools/list">>, #{}),
    Tools = maps:get(<<"tools">>, maps:get(<<"result">>, Resp)),
    Names = [maps:get(<<"name">>, T) || T <- Tools],
    %% Each advertised tool must carry a description and an input schema.
    lists:foreach(fun(T) ->
                      ?assert(maps:is_key(<<"description">>, T)),
                      ?assert(maps:is_key(<<"inputSchema">>, T))
                  end, Tools),
    Expected = [<<"find_matches">>, <<"head_to_head">>, <<"team_statistics">>,
                <<"search_players">>, <<"competition_standings">>,
                <<"aggregate_statistics">>, <<"list_competitions">>],
    lists:foreach(fun(N) -> ?assert(lists:member(N, Names)) end, Expected).

protocol_rejects_unknown_method() ->
    Resp = rpc(<<"no/such/method">>, #{}),
    Error = maps:get(<<"error">>, Resp),
    ?assertEqual(-32601, maps:get(<<"code">>, Error)).

tool_call_unknown_tool_is_error() ->
    {Struct, IsError, _Text} = raw_call(<<"does_not_exist">>, #{}),
    ?assertEqual(true, IsError),
    ?assertEqual(undefined, Struct).

%%% -------------------------------------------------------------------
%%% Data coverage
%%% -------------------------------------------------------------------

all_datasets_are_loaded_and_queryable() ->
    S = call(<<"list_competitions">>, #{}),
    Comps = maps:get(<<"competitions">>, S),
    ?assert(length(Comps) >= 4),
    %% Every competition reports at least one loaded match.
    TotalMatches = lists:sum([maps:get(<<"matches">>, C) || C <- Comps]),
    ?assert(TotalMatches > 10000),
    %% The headline competitions are present by name.
    Names = [maps:get(<<"name">>, C) || C <- Comps],
    ?assert(lists:any(fun(N) -> contains(N, <<"Brasileir">>) end, Names)),
    ?assert(lists:any(fun(N) -> contains(N, <<"Copa do Brasil">>) end, Names)),
    ?assert(lists:any(fun(N) -> contains(N, <<"Libertadores">>) end, Names)),
    %% Players are loaded too (cross-dataset coverage).
    P = call(<<"search_players">>, #{<<"nationality">> => <<"Brazil">>, <<"limit">> => 1}),
    ?assert(maps:get(<<"total_available">>, P) > 0).

%%% -------------------------------------------------------------------
%%% Match queries
%%% -------------------------------------------------------------------

find_all_matches_between_two_teams() ->
    S = call(<<"find_matches">>,
             #{<<"team">> => <<"Flamengo">>, <<"opponent">> => <<"Fluminense">>}),
    Matches = maps:get(<<"matches">>, S),
    ?assert(maps:get(<<"count">>, S) > 0),
    %% Every returned fixture genuinely involves both clubs.
    lists:foreach(
      fun(M) ->
          Teams = [maps:get(<<"home">>, M), maps:get(<<"away">>, M)],
          ?assert(lists:any(fun(T) -> contains(T, <<"Flamengo">>) end, Teams)),
          ?assert(lists:any(fun(T) -> contains(T, <<"Fluminense">>) end, Teams))
      end, Matches).

find_matches_for_a_team_in_a_season() ->
    S = call(<<"find_matches">>,
             #{<<"team">> => <<"Palmeiras">>, <<"season">> => 2019,
               <<"competition">> => <<"Brasileirão"/utf8>>}),
    Matches = maps:get(<<"matches">>, S),
    ?assert(maps:get(<<"count">>, S) > 0),
    lists:foreach(
      fun(M) ->
          ?assertEqual(2019, maps:get(<<"season">>, M)),
          Teams = [maps:get(<<"home">>, M), maps:get(<<"away">>, M)],
          ?assert(lists:any(fun(T) -> contains(T, <<"Palmeiras">>) end, Teams))
      end, Matches).

find_matches_by_competition() ->
    S = call(<<"find_matches">>,
             #{<<"competition">> => <<"Libertadores">>, <<"limit">> => 5}),
    Matches = maps:get(<<"matches">>, S),
    ?assert(length(Matches) =< 5),
    ?assert(maps:get(<<"count">>, S) > 0),
    lists:foreach(
      fun(M) -> ?assert(contains(maps:get(<<"competition">>, M), <<"Libertadores">>)) end,
      Matches).

head_to_head_record_is_consistent() ->
    S = call(<<"head_to_head">>,
             #{<<"team1">> => <<"Flamengo">>, <<"team2">> => <<"Fluminense">>}),
    Total = maps:get(<<"total_matches">>, S),
    W1 = maps:get(<<"team1_wins">>, S),
    W2 = maps:get(<<"team2_wins">>, S),
    D = maps:get(<<"draws">>, S),
    ?assert(Total > 0),
    %% Domain invariant: wins + wins + draws == matches played.
    ?assertEqual(Total, W1 + W2 + D).

%%% -------------------------------------------------------------------
%%% Team queries
%%% -------------------------------------------------------------------

team_statistics_for_a_season() ->
    %% Flamengo, 2019 Brasileirão: champions with a famous 90-point season.
    S = call(<<"team_statistics">>,
             #{<<"team">> => <<"Flamengo">>, <<"season">> => 2019,
               <<"competition">> => <<"Brasileirão"/utf8>>}),
    ?assertEqual(38, maps:get(<<"matches">>, S)),
    ?assertEqual(28, maps:get(<<"wins">>, S)),
    ?assertEqual(6, maps:get(<<"draws">>, S)),
    ?assertEqual(4, maps:get(<<"losses">>, S)),
    ?assertEqual(86, maps:get(<<"goals_for">>, S)),
    ?assertEqual(37, maps:get(<<"goals_against">>, S)),
    ?assertEqual(90, maps:get(<<"points">>, S)),
    %% wins/draws/losses partition the matches.
    ?assertEqual(maps:get(<<"matches">>, S),
                 maps:get(<<"wins">>, S) + maps:get(<<"draws">>, S)
                 + maps:get(<<"losses">>, S)).

team_name_variations_are_normalised() ->
    %% "Flamengo" (query) must match the dataset spelling "Flamengo-RJ".
    Plain = call(<<"team_statistics">>,
                 #{<<"team">> => <<"Flamengo">>, <<"season">> => 2019,
                   <<"competition">> => <<"Brasileirão"/utf8>>}),
    Suffixed = call(<<"team_statistics">>,
                    #{<<"team">> => <<"Flamengo-RJ">>, <<"season">> => 2019,
                      <<"competition">> => <<"Brasileirão"/utf8>>}),
    ?assertEqual(maps:get(<<"points">>, Plain), maps:get(<<"points">>, Suffixed)),
    ?assertEqual(maps:get(<<"matches">>, Plain), maps:get(<<"matches">>, Suffixed)).

home_record_differs_from_away_record() ->
    Home = call(<<"team_statistics">>,
                #{<<"team">> => <<"Corinthians">>, <<"competition">> => <<"Brasileirão"/utf8>>,
                  <<"venue">> => <<"home">>}),
    Away = call(<<"team_statistics">>,
                #{<<"team">> => <<"Corinthians">>, <<"competition">> => <<"Brasileirão"/utf8>>,
                  <<"venue">> => <<"away">>}),
    All = call(<<"team_statistics">>,
               #{<<"team">> => <<"Corinthians">>, <<"competition">> => <<"Brasileirão"/utf8>>,
                 <<"venue">> => <<"all">>}),
    ?assert(maps:get(<<"matches">>, Home) > 0),
    ?assert(maps:get(<<"matches">>, Away) > 0),
    %% Home + away matches account for all matches played.
    ?assertEqual(maps:get(<<"matches">>, All),
                 maps:get(<<"matches">>, Home) + maps:get(<<"matches">>, Away)).

%%% -------------------------------------------------------------------
%%% Competition queries
%%% -------------------------------------------------------------------

league_standings_crown_the_champion() ->
    S = call(<<"competition_standings">>,
             #{<<"competition">> => <<"Brasileirão"/utf8>>, <<"season">> => 2019}),
    Table = maps:get(<<"standings">>, S),
    ?assert(length(Table) >= 16),
    Champion = hd(Table),
    ?assertEqual(1, maps:get(<<"position">>, Champion)),
    ?assert(contains(maps:get(<<"team">>, Champion), <<"Flamengo">>)),
    ?assertEqual(90, maps:get(<<"points">>, Champion)),
    ?assertEqual(38, maps:get(<<"played">>, Champion)),
    ?assertEqual(28, maps:get(<<"wins">>, Champion)),
    %% The table is sorted by points (non-increasing).
    Points = [maps:get(<<"points">>, R) || R <- Table],
    ?assertEqual(Points, lists:reverse(lists:sort(Points))).

%%% -------------------------------------------------------------------
%%% Player queries
%%% -------------------------------------------------------------------

search_player_by_name() ->
    S = call(<<"search_players">>, #{<<"name">> => <<"Neymar">>}),
    Players = maps:get(<<"players">>, S),
    ?assert(maps:get(<<"count">>, S) > 0),
    Neymar = hd([P || P <- Players, contains(maps:get(<<"name">>, P), <<"Neymar">>)]),
    ?assertEqual(<<"Brazil">>, maps:get(<<"nationality">>, Neymar)),
    ?assertEqual(92, maps:get(<<"overall">>, Neymar)).

search_brazilian_players() ->
    S = call(<<"search_players">>,
             #{<<"nationality">> => <<"Brazil">>, <<"limit">> => 10}),
    ?assertEqual(827, maps:get(<<"total_available">>, S)),
    Players = maps:get(<<"players">>, S),
    ?assert(length(Players) =< 10),
    lists:foreach(fun(P) -> ?assertEqual(<<"Brazil">>, maps:get(<<"nationality">>, P)) end,
                  Players).

search_players_by_club() ->
    S = call(<<"search_players">>, #{<<"club">> => <<"Santos">>, <<"limit">> => 50}),
    Players = maps:get(<<"players">>, S),
    ?assert(maps:get(<<"total_available">>, S) >= 20),
    lists:foreach(fun(P) -> ?assert(contains(maps:get(<<"club">>, P), <<"Santos">>)) end,
                  Players).

top_players_are_sorted_by_rating() ->
    S = call(<<"search_players">>,
             #{<<"nationality">> => <<"Brazil">>, <<"sort_by">> => <<"overall">>,
               <<"limit">> => 5}),
    Players = maps:get(<<"players">>, S),
    ?assertEqual(<<"Neymar Jr">>, maps:get(<<"name">>, hd(Players))),
    Ratings = [maps:get(<<"overall">>, P) || P <- Players],
    ?assertEqual(Ratings, lists:reverse(lists:sort(Ratings))).

%%% -------------------------------------------------------------------
%%% Statistical analysis
%%% -------------------------------------------------------------------

aggregate_statistics_for_a_competition() ->
    S = call(<<"aggregate_statistics">>, #{<<"competition">> => <<"Brasileirão"/utf8>>}),
    ?assert(maps:get(<<"total_matches">>, S) > 1000),
    Avg = maps:get(<<"avg_goals_per_match">>, S),
    ?assert(Avg > 1.5 andalso Avg < 4.0),
    Rate = maps:get(<<"home_win_rate">>, S),
    ?assert(Rate > 0.0 andalso Rate < 1.0),
    %% Outcomes partition the matches.
    ?assertEqual(maps:get(<<"total_matches">>, S),
                 maps:get(<<"home_wins">>, S) + maps:get(<<"away_wins">>, S)
                 + maps:get(<<"draws">>, S)).

biggest_wins_are_reported() ->
    S = call(<<"aggregate_statistics">>,
             #{<<"competition">> => <<"Brasileirão"/utf8>>, <<"season">> => 2019}),
    Big = maps:get(<<"biggest_wins">>, S),
    ?assert(length(Big) > 0),
    First = hd(Big),
    Margin = maps:get(<<"margin">>, First),
    %% The biggest victory has the largest goal margin in the list.
    Margins = [maps:get(<<"margin">>, B) || B <- Big],
    ?assertEqual(Margin, lists:max(Margins)),
    ?assert(Margin >= 4).

%%% -------------------------------------------------------------------
%%% Cross-dataset scenario (player data + match data)
%%% -------------------------------------------------------------------

cross_dataset_player_then_matches() ->
    %% Find a Brazilian player, then look up matches for a Brazilian club
    %% — demonstrating queries that span the player and match datasets.
    P = call(<<"search_players">>, #{<<"name">> => <<"Gabriel">>}),
    ?assert(maps:get(<<"count">>, P) > 0),
    M = call(<<"find_matches">>,
             #{<<"team">> => <<"Santos">>, <<"competition">> => <<"Brasileirão"/utf8>>,
               <<"limit">> => 3}),
    ?assert(maps:get(<<"count">>, M) > 0),
    ?assert(length(maps:get(<<"matches">>, M)) =< 3).

%%% -------------------------------------------------------------------
%%% MCP client helpers - the ONLY way these tests touch the system.
%%% -------------------------------------------------------------------

%% Issue a JSON-RPC request through the public MCP entry point and
%% return the decoded JSON-RPC response object.
rpc(Method, Params) ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 1,
            <<"method">> => Method,
            <<"params">> => Params},
    RespBin = bsoccer_mcp:handle(json:encode(Req)),
    json:decode(RespBin).

%% Call an MCP tool and return its structured content map (the machine
%% readable result), failing the test if the tool reported an error.
call(Tool, Args) ->
    {Struct, IsError, Text} = raw_call(Tool, Args),
    ?assertEqual({Tool, false}, {Tool, IsError}),
    ?assert(is_binary(Text)),
    Struct.

%% Call an MCP tool, returning {StructuredContent, IsError, Text}.
raw_call(Tool, Args) ->
    Resp = rpc(<<"tools/call">>,
               #{<<"name">> => Tool, <<"arguments">> => Args}),
    Result = maps:get(<<"result">>, Resp),
    IsError = maps:get(<<"isError">>, Result, false),
    Content = maps:get(<<"content">>, Result, []),
    Text = case Content of
               [#{<<"text">> := T} | _] -> T;
               _ -> <<>>
           end,
    Struct = maps:get(<<"structuredContent">>, Result, undefined),
    {Struct, IsError, Text}.

contains(Haystack, Needle) ->
    binary:match(Haystack, Needle) =/= nomatch.
