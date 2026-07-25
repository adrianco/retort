%%%-------------------------------------------------------------------
%%% @doc Unit tests for the property graph, on a hand built graph so
%%% that the traversal logic is tested independently of the data.
%%%-------------------------------------------------------------------
-module(br_graph_tests).

-include_lib("eunit/include/eunit.hrl").

setup() ->
    ok = br_graph:new(),
    Santos = br_graph:add_node(team, <<"santos">>, <<"Santos">>, #{state => <<"SP">>}),
    Vasco = br_graph:add_node(team, <<"vasco">>, <<"Vasco da Gama">>, #{state => <<"RJ">>}),
    Serie = br_graph:add_node(competition, <<"serie_a">>, <<"Serie A">>),
    Match = br_graph:add_node(match, <<"m1">>, <<"Santos 2-1 Vasco">>),
    Pele = br_graph:add_node(player, 1, <<"Pele">>),
    br_graph:add_edge(Match, home_team, Santos),
    br_graph:add_edge(Match, away_team, Vasco),
    br_graph:add_edge(Match, in_competition, Serie),
    br_graph:add_edge(Santos, played_in, Serie),
    br_graph:add_edge(Vasco, played_in, Serie),
    br_graph:add_edge(Pele, plays_for, Santos),
    #{santos => Santos, vasco => Vasco, serie => Serie, match => Match, pele => Pele}.

cleanup(_) -> br_graph:delete().

graph_test_() ->
    {setup, fun setup/0, fun cleanup/1, fun(Nodes) -> tests(Nodes) end}.

tests(#{santos := Santos, vasco := Vasco, serie := Serie, match := Match, pele := Pele}) ->
    [{"node ids are type prefixed",
      ?_assertEqual(<<"team:santos">>, Santos)},
     {"nodes carry labels and properties",
      ?_assertMatch({ok, #{label := <<"Santos">>, type := team,
                           props := #{state := <<"SP">>}}},
                    br_graph:get_node(Santos))},
     {"missing nodes are reported",
      ?_assertEqual(error, br_graph:get_node(<<"team:nope">>))},
     {"outgoing edges are labelled",
      ?_assertEqual([Santos], br_graph:out(Match, home_team))},
     {"incoming edges are indexed too",
      ?_assertEqual([Match], br_graph:in(Santos, home_team))},
     {"neighbours ignore direction",
      ?_assertEqual(3, length(br_graph:neighbours(Santos)))},
     {"degree counts both directions",
      ?_assertEqual(3, br_graph:degree(Santos))},
     {"nodes can be listed by type",
      ?_assertEqual(2, length(br_graph:nodes_of_type(team)))},
     {"a node is its own path",
      ?_assertEqual({ok, [{start, Santos}]}, br_graph:path(Santos, Santos, 3))},
     {"one hop path",
      ?_assertEqual({ok, [{start, Pele}, {plays_for, Santos}]},
                    br_graph:path(Pele, Santos, 3))},
     {"multi hop path player -> club -> competition",
      ?_assertMatch({ok, [{start, Pele}, {plays_for, Santos}, {played_in, Serie}]},
                    br_graph:path(Pele, Serie, 4))},
     {"paths respect the depth limit",
      ?_assertEqual(not_found, br_graph:path(Pele, Vasco, 1))},
     {"unknown endpoints have no path",
      ?_assertEqual(not_found, br_graph:path(Pele, <<"team:nope">>, 4))},
     {"counts", ?_assertEqual(5, br_graph:node_count())},
     {"edge count", ?_assertEqual(6, br_graph:edge_count())},
     {"ids can be parsed back",
      ?_assertEqual({<<"team">>, <<"santos">>}, br_graph:parse_id(Santos))}].
