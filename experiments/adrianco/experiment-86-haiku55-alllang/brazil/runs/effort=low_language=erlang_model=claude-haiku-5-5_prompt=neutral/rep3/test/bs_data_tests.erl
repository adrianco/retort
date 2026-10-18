%%% Feature: The six source files are joined into one clean dataset.
-module(bs_data_tests).

-include_lib("eunit/include/eunit.hrl").
-import(bs_test_support, [u/1]).

data_test_() ->
    {setup, fun bs_test_support:fixture_data/0, fun(_) -> ok end,
     fun(D) ->
         [{"Given the fixture files, When loaded, Then fixtures from every file are present",
           ?_assert(lists:all(fun(F) -> lists:any(fun(M) -> maps:get(source, M) =:= F end,
                                                 maps:get(matches, D))
                                     end,
                              [<<"Brasileirao_Matches.csv">>, <<"novo_campeonato_brasileiro.csv">>,
                               <<"Brazilian_Cup_Matches.csv">>, <<"Libertadores_Matches.csv">>,
                               <<"BR-Football-Dataset.csv">>]))},

          {"Given the same match in two files, When loaded, Then it is kept once",
           ?_assertEqual(1, count(D, <<"2019-04-27">>, <<"flamengo">>))},

          {"Given BR-Football dates a match one day later, When loaded, Then it is still de-duplicated",
           ?_assertEqual(0, count(D, <<"2019-06-02">>, <<"atletico-pr">>))},

          {"Given an unplayed fixture with NA scores, When loaded, Then it is skipped",
           ?_assertEqual(0, count(D, <<"2019-05-19">>, <<"flamengo">>))},

          {"Given 14 distinct fixtures across all files, When loaded, Then 14 matches remain",
           ?_assertEqual(14, length(maps:get(matches, D)))},

          {"Given Atlético-MG and Atlético-PR, When loaded, Then they get distinct team keys",
           ?_assertEqual([<<"atletico-mg">>, <<"atletico-pr">>],
                         maps:get(<<"atletico">>, maps:get(bases, D)))},

          {"Given Atlético-MG, When loaded, Then its display name keeps the state",
           ?_assertEqual(<<"Atletico-MG">>, maps:get(<<"atletico-mg">>, maps:get(teams, D)))},

          {"Given Flamengo appears with and without a state, When loaded, Then one key is used",
           ?_assertEqual(<<"Flamengo">>, maps:get(<<"flamengo">>, maps:get(teams, D)))},

          {"Given Libertadores scores stored as quoted strings, When loaded, Then they are integers",
           ?_assertMatch([#{home_goals := 3, away_goals := 0}],
                         [M || M <- maps:get(matches, D), maps:get(date, M) =:= <<"2019-03-13">>])},

          {"Given a 2003 row dated DD/MM/YYYY, When loaded, Then the date is ISO",
           ?_assertEqual(1, count(D, <<"2003-03-29">>, <<"guarani">>))},

          {"Given the FIFA file, When loaded, Then player ratings are integers",
           ?_assertMatch([#{name := <<"Casemiro">>, overall := 88, nationality := <<"Brazil">>}],
                         [P || P <- maps:get(players, D), maps:get(name, P) =:= <<"Casemiro">>])}]
     end}.

count(D, Date, HomeKey) ->
    length([M || M <- maps:get(matches, D),
                 maps:get(date, M) =:= Date,
                 maps:get(home, M) =:= HomeKey orelse maps:get(away, M) =:= HomeKey]).
