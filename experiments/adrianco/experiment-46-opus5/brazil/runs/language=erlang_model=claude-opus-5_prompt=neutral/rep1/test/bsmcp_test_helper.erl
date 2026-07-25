%%%-------------------------------------------------------------------
%%% @doc Shared test bootstrap.
%%%
%%% Context: Common Test runs every suite in one node, so the ~2.5 s CSV
%%% load happens once and is then shared.  The data directory is located
%%% by walking up from the compiled application, which works no matter
%%% what CT sets the working directory to.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_test_helper).

-export([start/0, data_dir/0, sample_questions/0]).

start() ->
    {ok, _} = application:ensure_all_started(bsmcp),
    Status = bsmcp_data:status(),
    case maps:get(matches, Status, 0) of
        0 ->
            ct:fail({no_data_loaded, bsmcp_data:data_dir()});
        _ ->
            ok
    end.

data_dir() -> bsmcp_data:data_dir().

%% @doc The specification asks that at least 20 natural language
%% questions can be answered.  Each entry is
%% {Question, Tool, Arguments, CheckFun} and is executed by
%% sample_questions_SUITE.
sample_questions() ->
    [{<<"Show me all Flamengo vs Fluminense matches">>,
      <<"search_matches">>, #{<<"team">> => <<"Flamengo">>,
                              <<"opponent">> => <<"Fluminense">>},
      fun(R) -> maps:get(total, R) > 20 end},

     {<<"What matches did Palmeiras play in 2023?">>,
      <<"search_matches">>, #{<<"team">> => <<"Palmeiras">>, <<"season">> => 2023,
                              <<"limit">> => 60},
      fun(R) -> maps:get(total, R) >= 38 end},

     {<<"Find all Copa Libertadores finals">>,
      <<"search_matches">>, #{<<"competition">> => <<"libertadores">>,
                              <<"stage">> => <<"final">>},
      fun(R) -> maps:get(total, R) >= 10 end},

     {<<"When did Flamengo last play Corinthians and what was the score?">>,
      <<"search_matches">>, #{<<"team">> => <<"Flamengo">>,
                              <<"opponent">> => <<"Corinthians">>,
                              <<"played_only">> => true, <<"limit">> => 1},
      fun(R) -> [M] = maps:get(matches, R), is_binary(maps:get(score, M)) end},

     {<<"What is Corinthians' home record in 2022?">>,
      <<"team_stats">>, #{<<"team">> => <<"Corinthians">>, <<"season">> => 2022,
                          <<"competition">> => <<"serie a">>, <<"venue">> => <<"home">>},
      fun(R) -> maps:get(played, maps:get(record, R)) =:= 19 end},

     {<<"Which team scored the most goals in Serie A 2023?">>,
      <<"league_leaderboard">>, #{<<"metric">> => <<"goals_for">>,
                                  <<"competition">> => <<"serie a">>,
                                  <<"season">> => 2023, <<"limit">> => 1},
      fun(R) -> [Top] = maps:get(leaderboard, R), maps:get(value, Top) > 50 end},

     {<<"Compare Palmeiras and Santos head-to-head">>,
      <<"head_to_head">>, #{<<"team_a">> => <<"Palmeiras">>, <<"team_b">> => <<"Santos">>},
      fun(R) -> maps:get(played, maps:get(summary, R)) > 20 end},

     {<<"What competitions has Palmeiras played in?">>,
      <<"team_profile">>, #{<<"team">> => <<"Palmeiras">>},
      fun(R) -> length(maps:get(competitions, R)) >= 3 end},

     {<<"Who won the 2019 Brasileirao?">>,
      <<"standings">>, #{<<"competition">> => <<"serie a">>, <<"season">> => 2019},
      fun(R) -> maps:get(champion, R) =:= <<"Flamengo-RJ">> end},

     {<<"Which teams were relegated in 2020?">>,
      <<"standings">>, #{<<"competition">> => <<"serie a">>, <<"season">> => 2020},
      fun(R) -> length(maps:get(relegated, R)) =:= 4 end},

     {<<"Show the 2018 Copa Libertadores results by stage">>,
      <<"search_matches">>, #{<<"competition">> => <<"libertadores">>,
                              <<"season">> => 2018, <<"limit">> => 200},
      fun(R) -> maps:get(total, R) > 100 end},

     {<<"What is the average goals per match in the Brasileirao?">>,
      <<"competition_stats">>, #{<<"competition">> => <<"serie a">>},
      fun(R) -> G = maps:get(goals_per_match, maps:get(overall, R)),
                G > 2.0 andalso G < 3.5
      end},

     {<<"Which team has the best away record?">>,
      <<"league_leaderboard">>, #{<<"metric">> => <<"away_win_rate">>,
                                  <<"competition">> => <<"serie a">>,
                                  <<"min_played">> => 100, <<"limit">> => 3},
      fun(R) -> length(maps:get(leaderboard, R)) =:= 3 end},

     {<<"Show me the biggest wins in the dataset">>,
      <<"biggest_wins">>, #{<<"limit">> => 5},
      fun(R) -> [Top | _] = maps:get(matches, R), maps:get(margin, Top) >= 7 end},

     {<<"Compare the 2018 and 2019 seasons">>,
      <<"competition_stats">>, #{<<"competition">> => <<"serie a">>,
                                 <<"seasons">> => [2018, 2019]},
      fun(R) -> length(maps:get(by_season, R)) =:= 2 end},

     {<<"Find all Brazilian players in the dataset">>,
      <<"search_players">>, #{<<"nationality">> => <<"Brazil">>, <<"limit">> => 10},
      fun(R) -> maps:get(total, R) > 800 end},

     {<<"Who are the highest rated players at Gremio?">>,
      <<"club_squad">>, #{<<"club">> => <<"Gremio">>, <<"limit">> => 5},
      fun(R) -> maps:get(squad_size, R) >= 15 end},

     {<<"Show me all forwards from Atletico Mineiro">>,
      <<"search_players">>, #{<<"club">> => <<"Atletico Mineiro">>,
                              <<"position">> => <<"forward">>},
      fun(R) -> maps:get(total, R) >= 1 end},

     {<<"Which players play for Fluminense?">>,
      <<"club_squad">>, #{<<"club">> => <<"Fluminense">>},
      fun(R) -> maps:get(squad_size, R) >= 15 end},

     {<<"Brazilian players at Brazilian clubs, by average rating">>,
      <<"club_ratings">>, #{<<"nationality">> => <<"Brazil">>,
                            <<"brazilian_clubs_only">> => true,
                            <<"min_players">> => 5},
      fun(R) -> maps:get(total_clubs, R) >= 10 end},

     {<<"Who is Neymar?">>,
      <<"player_profile">>, #{<<"name">> => <<"Neymar">>},
      fun(R) -> maps:get(overall, maps:get(player, R)) >= 90 end},

     {<<"Which Botafogo is which?">>,
      <<"list_teams">>, #{<<"query">> => <<"Botafogo">>},
      fun(R) -> maps:get(total, R) >= 3 end},

     {<<"What data is loaded?">>,
      <<"dataset_summary">>, #{},
      fun(R) -> length(maps:get(competitions, R)) =:= 5 end},

     {<<"How did Sao Paulo do in the 2006 season?">>,
      <<"team_stats">>, #{<<"team">> => <<"Sao Paulo">>, <<"season">> => 2006,
                          <<"competition">> => <<"serie a">>},
      fun(R) -> maps:get(points, maps:get(record, R)) =:= 78 end},

     {<<"How many goals did Gremio score at home in 2019?">>,
      <<"team_stats">>, #{<<"team">> => <<"Gremio">>, <<"season">> => 2019,
                          <<"competition">> => <<"serie a">>, <<"venue">> => <<"home">>},
      fun(R) -> maps:get(goals_for, maps:get(record, R)) > 0 end}].
