%%% =====================================================================
%%% bsoccer_tests — EUnit suite for the Brazilian Soccer MCP server.
%%%
%%% Two groups of tests:
%%%   * Pure-unit tests for the parsing/normalisation helpers (bsoccer_csv,
%%%     bsoccer_util) that need no data files.
%%%   * Integration tests that load the bundled datasets once (via a shared
%%%     setup fixture) and exercise the query layer and the MCP protocol
%%%     end-to-end, asserting against known-good facts — most notably that the
%%%     calculated 2019 Brasileirão table crowns Flamengo champion on 90 pts,
%%%     exactly as the specification's worked example shows.
%%% =====================================================================
-module(bsoccer_tests).

-include_lib("eunit/include/eunit.hrl").

-define(DATA_DIR, "data/kaggle").

%% =====================================================================
%% Pure unit tests (no data files required)
%% =====================================================================

csv_quoted_fields_test() ->
    Csv = <<"a,b,c\n1,\"hello, world\",3\n\"x\"\"y\",p,q\n">>,
    {Header, Rows} = bsoccer_csv:parse(Csv),
    ?assertEqual([<<"a">>, <<"b">>, <<"c">>], Header),
    ?assertEqual([[<<"1">>, <<"hello, world">>, <<"3">>],
                  [<<"x\"y">>, <<"p">>, <<"q">>]], Rows).

csv_bom_and_crlf_test() ->
    Csv = <<239, 187, 191, "h1,h2\r\nv1,v2\r\n">>,
    {Header, Rows} = bsoccer_csv:parse(Csv),
    ?assertEqual([<<"h1">>, <<"h2">>], Header),
    ?assertEqual([[<<"v1">>, <<"v2">>]], Rows).

clean_team_strips_suffixes_test() ->
    ?assertEqual(<<"Palmeiras">>, bsoccer_util:clean_team(<<"Palmeiras-SP">>)),
    ?assertEqual(<<"Nacional">>, bsoccer_util:clean_team(<<"Nacional (URU)">>)),
    ?assertEqual(<<"América"/utf8>>, bsoccer_util:clean_team(<<"América - MG"/utf8>>)),
    ?assertEqual(<<"Barcelona">>, bsoccer_util:clean_team(<<"Barcelona-EQU">>)).

team_key_normalisation_test() ->
    %% Accents, suffixes and case all collapse to the same key.
    ?assertEqual(bsoccer_util:team_key(<<"São Paulo"/utf8>>),
                 bsoccer_util:team_key(<<"Sao Paulo-SP">>)),
    ?assertEqual(bsoccer_util:team_key(<<"Grêmio"/utf8>>),
                 bsoccer_util:team_key(<<"GREMIO">>)),
    ?assertEqual(<<"flamengo">>, bsoccer_util:team_key(<<"Flamengo-RJ">>)).

fold_accents_test() ->
    ?assertEqual(<<"Sao Paulo">>, bsoccer_util:fold_accents(<<"São Paulo"/utf8>>)),
    ?assertEqual(<<"Gremio">>, bsoccer_util:fold_accents(<<"Grêmio"/utf8>>)),
    ?assertEqual(<<"Avai">>, bsoccer_util:fold_accents(<<"Avaí"/utf8>>)).

parse_date_formats_test() ->
    ?assertEqual({{2012, 5, 19}, <<"2012-05-19">>},
                 bsoccer_util:parse_date(<<"2012-05-19 18:30:00">>)),
    ?assertEqual({{2023, 9, 24}, <<"2023-09-24">>},
                 bsoccer_util:parse_date(<<"2023-09-24">>)),
    ?assertEqual({{2003, 3, 29}, <<"2003-03-29">>},
                 bsoccer_util:parse_date(<<"29/03/2003">>)),
    ?assertEqual(undefined, bsoccer_util:parse_date(<<"not a date">>)).

parse_goal_variants_test() ->
    ?assertEqual(2, bsoccer_util:parse_goal(<<"2">>)),
    ?assertEqual(2, bsoccer_util:parse_goal(<<"2.0">>)),
    ?assertEqual(0, bsoccer_util:parse_goal(<<"0.0">>)),
    ?assertEqual(undefined, bsoccer_util:parse_goal(<<>>)),
    ?assertEqual(undefined, bsoccer_util:parse_goal(<<"  ">>)).

%% MCP message handling that needs no data.
mcp_initialize_test() ->
    {reply, Resp} = bsoccer_mcp:handle_message(
                      msg(1, <<"initialize">>, #{})),
    ?assertEqual(1, maps:get(<<"id">>, Resp)),
    Result = maps:get(<<"result">>, Resp),
    ?assertMatch(#{<<"protocolVersion">> := _}, Result),
    ?assertEqual(<<"brazilian-soccer-mcp">>,
                 maps:get(<<"name">>, maps:get(<<"serverInfo">>, Result))).

mcp_notification_no_reply_test() ->
    ?assertEqual(noreply,
                 bsoccer_mcp:handle_message(
                   #{<<"jsonrpc">> => <<"2.0">>,
                     <<"method">> => <<"notifications/initialized">>})).

mcp_unknown_method_test() ->
    {reply, Resp} = bsoccer_mcp:handle_message(msg(9, <<"no/such">>, #{})),
    ?assertMatch(#{<<"error">> := #{<<"code">> := -32601}}, Resp).

mcp_tools_list_test() ->
    {reply, Resp} = bsoccer_mcp:handle_message(msg(2, <<"tools/list">>, #{})),
    Tools = maps:get(<<"tools">>, maps:get(<<"result">>, Resp)),
    Names = [maps:get(<<"name">>, T) || T <- Tools],
    ?assert(lists:member(<<"search_matches">>, Names)),
    ?assert(lists:member(<<"standings">>, Names)),
    ?assert(lists:member(<<"search_players">>, Names)),
    %% Every tool must advertise a JSON-Schema object.
    lists:foreach(
      fun(T) ->
              ?assertEqual(<<"object">>,
                           maps:get(<<"type">>, maps:get(<<"inputSchema">>, T)))
      end, Tools).

%% =====================================================================
%% Integration tests (load the bundled data once)
%% =====================================================================

data_test_() ->
    {setup,
     fun setup/0,
     fun(_) -> ok end,
     fun(_) ->
             [?_test(t_data_loaded()),
              ?_test(t_search_matches_flu()),
              ?_test(t_head_to_head_symmetry()),
              ?_test(t_team_record_corinthians()),
              ?_test(t_standings_2019_flamengo_champion()),
              ?_test(t_standings_2020_no_state_merge()),
              ?_test(t_search_players_brazil()),
              ?_test(t_search_players_by_club()),
              ?_test(t_match_stats_nonempty()),
              ?_test(t_data_summary()),
              ?_test(t_tool_call_via_mcp()),
              ?_test(t_tool_missing_arg_is_error()),
              ?_test(t_utf8_json_roundtrip())]
     end}.

setup() ->
    {ok, _} = bsoccer_data:ensure_started(?DATA_DIR),
    ok.

t_data_loaded() ->
    S = bsoccer_data:stats(),
    ?assert(maps:get(matches, S) > 20000),
    ?assert(maps:get(players, S) > 18000),
    ?assert(map_size(maps:get(matches_by_competition, S)) >= 4).

t_search_matches_flu() ->
    R = bsoccer_query:search_matches(
          #{<<"team">> => <<"Flamengo">>, <<"opponent">> => <<"Fluminense">>}),
    Data = maps:get(data, R),
    ?assert(maps:get(total, Data) > 10),
    %% The rendered answer mentions both clubs and a head-to-head line.
    Text = maps:get(text, R),
    ?assert(contains(Text, <<"Flamengo">>)),
    ?assert(contains(Text, <<"Head-to-head">>)).

t_head_to_head_symmetry() ->
    A = maps:get(data, bsoccer_query:head_to_head(
                          #{<<"team1">> => <<"Palmeiras">>,
                            <<"team2">> => <<"Santos">>})),
    B = maps:get(data, bsoccer_query:head_to_head(
                          #{<<"team1">> => <<"Santos">>,
                            <<"team2">> => <<"Palmeiras">>})),
    %% Same fixtures, mirrored perspective.
    ?assertEqual(maps:get(matches, A), maps:get(matches, B)),
    ?assertEqual(maps:get(team1_wins, A), maps:get(team2_wins, B)),
    ?assertEqual(maps:get(draws, A), maps:get(draws, B)),
    ?assert(maps:get(matches, A) > 0).

t_team_record_corinthians() ->
    R = bsoccer_query:team_record(
          #{<<"team">> => <<"Corinthians">>, <<"season">> => 2022,
            <<"venue">> => <<"home">>}),
    D = maps:get(data, R),
    P = maps:get(played, D),
    ?assert(P > 0),
    %% Internal consistency: W + D + L = played.
    ?assertEqual(P, maps:get(wins, D) + maps:get(draws, D) + maps:get(losses, D)).

t_standings_2019_flamengo_champion() ->
    R = bsoccer_query:standings(#{<<"season">> => 2019}),
    Table = maps:get(table, maps:get(data, R)),
    %% A full Brasileirão season is 380 matches / 20 teams.
    ?assertEqual(380, maps:get(matches, maps:get(data, R))),
    [Champion | _] = Table,
    ?assertEqual(1, maps:get(rank, Champion)),
    ?assertEqual(<<"Flamengo">>, maps:get(name, Champion)),
    ?assertEqual(90, maps:get(points, Champion)).

t_standings_2020_no_state_merge() ->
    %% 2020 has Atlético-MG, -GO and -PR — clubs distinguished only by their
    %% state suffix. The table must keep them separate, so no row can show
    %% more than the 38 games a Brasileirão team plays.
    Table = maps:get(table, maps:get(data,
              bsoccer_query:standings(#{<<"season">> => 2020}))),
    Played = [maps:get(played, Row) || Row <- Table],
    ?assert(lists:max(Played) =< 38),
    %% Flamengo won the real 2020 Brasileirão.
    [Champion | _] = Table,
    ?assertEqual(71, maps:get(points, Champion)),
    ?assert(contains(maps:get(name, Champion), <<"Flamengo">>)).

t_search_players_by_club() ->
    %% Filtering by club must not crash on players with an empty club field
    %% and must find players for a club present in the FIFA data.
    R = bsoccer_query:search_players(#{<<"club">> => <<"Grêmio"/utf8>>,
                                       <<"limit">> => 3}),
    D = maps:get(data, R),
    ?assert(maps:get(total, D) > 0),
    lists:foreach(
      fun(P) -> ?assert(contains(maps:get(club, P), <<"Grêmio"/utf8>>)) end,
      maps:get(players, D)).

t_search_players_brazil() ->
    R = bsoccer_query:search_players(
          #{<<"nationality">> => <<"Brazil">>, <<"limit">> => 5}),
    D = maps:get(data, R),
    ?assert(maps:get(total, D) > 100),
    Players = maps:get(players, D),
    %% Sorted by overall, descending.
    Overalls = [maps:get(overall, P) || P <- Players],
    ?assertEqual(lists:reverse(lists:sort(Overalls)), Overalls),
    %% Top Brazilian in the FIFA file is Neymar.
    [Top | _] = Players,
    ?assert(contains(maps:get(name, Top), <<"Neymar">>)).

t_match_stats_nonempty() ->
    R = bsoccer_query:match_stats(#{<<"season">> => 2019}),
    D = maps:get(data, R),
    ?assert(maps:get(matches, D) > 0),
    Avg = maps:get(avg_goals_per_match, D),
    ?assert(Avg > 1.0 andalso Avg < 5.0).

t_data_summary() ->
    R = bsoccer_query:data_summary(#{}),
    ?assert(contains(maps:get(text, R), <<"Total matches">>)).

t_tool_call_via_mcp() ->
    {reply, Resp} =
        bsoccer_mcp:handle_message(
          msg(3, <<"tools/call">>,
              #{<<"name">> => <<"team_record">>,
                <<"arguments">> => #{<<"team">> => <<"Palmeiras">>}})),
    Result = maps:get(<<"result">>, Resp),
    ?assertNot(maps:get(<<"isError">>, Result, false)),
    [Content | _] = maps:get(<<"content">>, Result),
    ?assertEqual(<<"text">>, maps:get(<<"type">>, Content)),
    ?assert(contains(maps:get(<<"text">>, Content), <<"Palmeiras">>)).

t_tool_missing_arg_is_error() ->
    {reply, Resp} =
        bsoccer_mcp:handle_message(
          msg(4, <<"tools/call">>,
              #{<<"name">> => <<"head_to_head">>,
                <<"arguments">> => #{<<"team1">> => <<"Flamengo">>}})),
    Result = maps:get(<<"result">>, Resp),
    ?assertEqual(true, maps:get(<<"isError">>, Result)).

t_utf8_json_roundtrip() ->
    %% A query whose answer contains accented names must survive JSON
    %% encode/decode unchanged (the bug class the stdio transport had).
    {reply, Resp} =
        bsoccer_mcp:handle_message(
          msg(5, <<"tools/call">>,
              #{<<"name">> => <<"standings">>,
                <<"arguments">> => #{<<"season">> => 2019, <<"limit">> => 5}})),
    Encoded = iolist_to_binary(json:encode(Resp)),
    Decoded = json:decode(Encoded),
    Text = maps:get(<<"text">>,
                    hd(maps:get(<<"content">>,
                               maps:get(<<"result">>, Decoded)))),
    ?assert(contains(Text, <<"Grêmio"/utf8>>)),
    ?assert(contains(Text, <<"Série A"/utf8>>)).

%% =====================================================================
%% Helpers
%% =====================================================================

msg(Id, Method, Params) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
      <<"method">> => Method, <<"params">> => Params}.

contains(Hay, Needle) ->
    binary:match(Hay, Needle) =/= nomatch.
