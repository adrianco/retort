%%% Feature: The real Kaggle datasets answer the questions in the specification.
%%% Skipped when data/kaggle is not present.
-module(bs_integration_tests).

-include_lib("eunit/include/eunit.hrl").
-import(bs_test_support, [u/1]).

integration_test_() ->
    case filelib:is_dir(bs_test_support:real_data_dir()) of
        false ->
            [];
        true ->
            {timeout, 120,
             {setup, fun() -> bs_data:load(bs_test_support:real_data_dir()) end,
              fun(_) -> ok end,
              fun(D) ->
                  [{"Given all match files, When the 2019 Série A table is calculated, "
                    "Then Flamengo are champions with 90 points",
                    ?_test(begin
                               [Top | _] = bs_query:standings(D, #{season => 2019,
                                                                   competition => u("Brasileirão Série A")}),
                               ?assertEqual({<<"flamengo-rj">>, 90},
                                            {maps:get(key, Top), maps:get(points, Top)})
                           end)},

                   {"Given the 2019 table, When read below the top, Then Santos and Palmeiras both have 74",
                    ?_test(begin
                               [_, Santos, Palmeiras | _] =
                                   bs_query:standings(D, #{season => 2019,
                                                           competition => u("Brasileirão Série A")}),
                               ?assertEqual([74, 74], [maps:get(points, Santos),
                                                        maps:get(points, Palmeiras)])
                           end)},

                   {"Given Flamengo and Fluminense, When asked head-to-head, Then many matches are found",
                    ?_assert(length(maps:get(matches,
                                             bs_query:head_to_head(D, <<"flamengo-rj">>,
                                                                   <<"fluminense-rj">>))) > 40)},

                   {"Given the FIFA data, When Brazilian players are searched, Then more than 100 are found",
                    ?_assert(length(bs_query:search_players(D, #{nationality => <<"brazil">>})) > 100)}]
              end}}
    end.
