%%%-------------------------------------------------------------------
%%% @doc Feature: Data coverage and integrity
%%%
%%% Checks the loading side of the success criteria: all six CSV files
%%% are loadable and queryable, the merge across files is sound, the
%%% Portuguese text survives, and the seasons add up.
%%% @end
%%%-------------------------------------------------------------------
-module(data_integrity_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").
-include("br_soccer.hrl").

all() ->
    [all_six_files_load,
     row_counts_match_the_specification,
     every_match_has_teams_and_a_competition,
     duplicates_are_merged_not_lost,
     league_seasons_are_round_robins,
     accented_names_survive_loading,
     team_ids_never_mix_two_clubs,
     dates_are_parsed_from_every_format,
     players_are_linked_to_clubs,
     graph_is_consistent_with_the_tables].

init_per_suite(Config) ->
    bdd:feature("Data coverage and integrity"),
    bdd:data_is_loaded(),
    [{data_dir_kaggle, br_loader:data_dir()} | Config].

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
all_six_files_load(Config) ->
    bdd:scenario("All six CSV files are loadable and queryable"),
    Dir = ?config(data_dir_kaggle, Config),
    bdd:given("the data directory is found",
              fun() -> ?assertNotEqual(undefined, Dir) end),
    Counts = bdd:'when'("each file is loaded on its own",
                        fun() ->
                                [{Source, length(br_loader:load_file(Source, Dir))}
                                 || {Source, _File} <- br_loader:data_files()]
                        end),
    bdd:then("each file should yield records",
             fun() ->
                     ct:log("~p", [Counts]),
                     lists:foreach(fun({Source, N}) -> ?assertMatch({_, true}, {Source, N > 0})
                                   end, Counts)
             end).

%%--------------------------------------------------------------------
row_counts_match_the_specification(Config) ->
    bdd:scenario("The files contain the documented number of rows"),
    Dir = ?config(data_dir_kaggle, Config),
    bdd:given("the data directory is found", fun() -> ?assertNotEqual(undefined, Dir) end),
    bdd:then("the row counts should match the specification",
             fun() ->
                     Expected = [{brasileirao_matches, 4180},
                                 {novo_brasileirao, 6886},
                                 {copa_do_brasil, 1337},
                                 {libertadores, 1255},
                                 {br_football, 10296},
                                 {fifa_players, 18207}],
                     lists:foreach(
                       fun({Source, Count}) ->
                               Loaded = length(br_loader:load_file(Source, Dir)),
                               ?assertEqual({Source, Count}, {Source, Loaded})
                       end, Expected)
             end).

%%--------------------------------------------------------------------
every_match_has_teams_and_a_competition(_Config) ->
    bdd:scenario("Every stored match is well formed"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Problems = bdd:'when'("I inspect every match in the store",
                          fun() ->
                                  br_store:fold_matches(
                                    fun(M, Acc) ->
                                            case well_formed(M) of
                                                true -> Acc;
                                                false -> [M#match.id | Acc]
                                            end
                                    end, [])
                          end),
    bdd:then("none of them should be missing a team or a competition",
             fun() -> ?assertEqual([], lists:sublist(Problems, 5)) end),
    bdd:'and'("no team plays itself: the broken source rows are dropped",
              fun() ->
                      Same = br_store:fold_matches(
                               fun(#match{home = H, away = A, id = Id}, Acc)
                                     when H =:= A -> [Id | Acc];
                                  (_, Acc) -> Acc
                               end, []),
                      ?assertEqual([], Same),
                      %% Brazilian_Cup_Matches.csv contains two 2019 rows where
                      %% the opponent's state suffix was lost, making both sides
                      %% "Bragantino - PA"; they are counted and skipped.
                      ?assertEqual(2, maps:get(invalid_rows, br_store:stats()))
              end).

well_formed(#match{home = H, away = A, competition = C}) ->
    is_binary(H) andalso H =/= <<>>
        andalso is_binary(A) andalso A =/= <<>>
        andalso is_binary(C) andalso C =/= <<>>.

%%--------------------------------------------------------------------
duplicates_are_merged_not_lost(_Config) ->
    bdd:scenario("Fixtures present in several files are merged"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Stats = bdd:'when'("I look at the load statistics",
                       fun() -> br_store:stats() end),
    bdd:then("rows read should equal stored matches plus players plus merges",
             fun() ->
                     #{rows_read := Rows, matches := Matches, players := Players,
                       duplicates_merged := Merged, invalid_rows := Invalid} = Stats,
                     ct:log("~p rows -> ~p matches (~p merged, ~p invalid) + ~p players",
                            [Rows, Matches, Merged, Invalid, Players]),
                     ?assertEqual(Rows, Matches + Merged + Invalid + Players)
             end),
    bdd:'and'("merged matches should record more than one source",
              fun() ->
                      Multi = br_store:fold_matches(
                                fun(#match{sources = S}, Acc) when length(S) > 1 -> Acc + 1;
                                   (_, Acc) -> Acc
                                end, 0),
                      ?assert(Multi > 1000)
              end).

%%--------------------------------------------------------------------
league_seasons_are_round_robins(_Config) ->
    bdd:scenario("A complete league season is a double round robin"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    %% 2009 is missing one fixture and 2015 carries a stray non-league
    %% fixture in BR-Football-Dataset.csv; both are gaps in the source
    %% data, and the `complete' flag is expected to catch them.
    Known = [2009, 2015],
    Seasons = bdd:'when'("I check every Serie A season from 2006 to 2022",
                         fun() ->
                                 [begin
                                      {ok, T} = br_query:standings(
                                                  #{competition => <<"serie a">>,
                                                    season => S}),
                                      {S, maps:get(matches, T), maps:get(teams, T),
                                       maps:get(complete, T)}
                                  end || S <- lists:seq(2006, 2022)]
                         end),
    bdd:then("each of them should have 20 teams and 380 matches",
             fun() ->
                     ct:log("~p", [Seasons]),
                     lists:foreach(fun({S, Matches, Teams, Complete}) ->
                                           ?assertEqual({S, 380, 20, true},
                                                        {S, Matches, Teams, Complete})
                                   end, [X || {S, _, _, _} = X <- Seasons,
                                              not lists:member(S, Known)])
             end),
    bdd:but("the two seasons with gaps in the source data are not called complete",
            fun() ->
                    lists:foreach(
                      fun(S) ->
                              {ok, T} = br_query:standings(#{competition => <<"serie a">>,
                                                             season => S}),
                              ?assertEqual({S, false}, {S, maps:get(complete, T)})
                      end, Known)
            end),
    bdd:'and'("the earlier seasons with more teams are still consistent",
              fun() ->
                      {ok, T2003} = br_query:standings(#{competition => <<"serie a">>,
                                                         season => 2003}),
                      N = maps:get(teams, T2003),
                      ?assertEqual(N * (N - 1), maps:get(matches, T2003))
              end).

%%--------------------------------------------------------------------
accented_names_survive_loading(_Config) ->
    bdd:scenario("UTF-8 Portuguese text is preserved"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    bdd:then("accented club names come back with their accents",
             fun() ->
                     lists:foreach(
                       fun({Query, Expected}) ->
                               {ok, Id} = br_store:resolve_team(Query),
                               {ok, Team} = br_store:team(Id),
                               ?assertEqual(Expected, Team#team.name)
                       end,
                       [{<<"Gremio">>, <<"Grêmio"/utf8>>},
                        {<<"Sao Paulo">>, <<"São Paulo"/utf8>>},
                        {<<"Avai">>, <<"Avaí"/utf8>>},
                        {<<"Atletico Mineiro">>, <<"Atlético Mineiro"/utf8>>},
                        {<<"Vitoria">>, <<"Vitória"/utf8>>}])
             end),
    bdd:'and'("they are valid UTF-8 when encoded as JSON",
              fun() ->
                      {ok, Result} = br_query:standings(#{season => 2019}),
                      Json = br_json:encode(Result),
                      ?assertMatch(Bin when is_binary(Bin),
                                   unicode:characters_to_binary(Json, utf8, utf8)),
                      ?assertNotEqual(nomatch, binary:match(Json, <<"Grêmio"/utf8>>))
              end).

%%--------------------------------------------------------------------
team_ids_never_mix_two_clubs(_Config) ->
    bdd:scenario("Clubs that share a short name stay separate"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    bdd:then("America-MG and America-RN are different teams with different records",
             fun() ->
                     {ok, MG} = br_store:resolve_team(<<"America MG">>),
                     {ok, RN} = br_store:resolve_team(<<"América - RN"/utf8>>),
                     ?assertNotEqual(MG, RN),
                     {ok, TeamMG} = br_store:team(MG),
                     {ok, TeamRN} = br_store:team(RN),
                     ?assert(TeamMG#team.match_count > TeamRN#team.match_count)
             end),
    bdd:'and'("the three Atleticos are three teams",
              fun() ->
                      Ids = [begin {ok, Id} = br_store:resolve_team(N), Id end
                             || N <- [<<"Atletico-MG">>, <<"Atletico-GO">>,
                                      <<"Atletico-PR">>]],
                      ?assertEqual(3, length(lists:usort(Ids)))
              end),
    bdd:'and'("every team in the store has at least one match",
              fun() ->
                      Empty = [T#team.id || T <- br_store:all_teams(),
                                            T#team.match_count =:= 0],
                      ?assertEqual([], Empty)
              end).

%%--------------------------------------------------------------------
dates_are_parsed_from_every_format(_Config) ->
    bdd:scenario("Every date format in the data is understood"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    {WithDate, Total} =
        bdd:'when'("I count the matches that have a date",
                   fun() ->
                           br_store:fold_matches(
                             fun(#match{date = undefined}, {W, T}) -> {W, T + 1};
                                (_, {W, T}) -> {W + 1, T + 1}
                             end, {0, 0})
                   end),
    bdd:then("virtually every match should have one",
             fun() ->
                     ct:log("~p of ~p matches have a date", [WithDate, Total]),
                     ?assert(WithDate / Total > 0.999)
             end),
    bdd:'and'("the Brazilian format file should yield 2003 dates",
              fun() ->
                      {ok, #{matches := Ms}} =
                          br_query:find_matches(#{season => 2003, limit => 5,
                                                  sort => <<"date_asc">>}),
                      lists:foreach(fun(#{date := D}) ->
                                            ?assertMatch(<<"2003-", _/binary>>, D)
                                    end, Ms)
              end).

%%--------------------------------------------------------------------
players_are_linked_to_clubs(_Config) ->
    bdd:scenario("Players are indexed by club"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    bdd:then("a Brazilian club in both data sets has players and matches",
             fun() ->
                     {ok, Id} = br_store:resolve_team(<<"Internacional">>),
                     Players = br_store:players_of_club(Id),
                     {ok, Team} = br_store:team(Id),
                     ?assert(length(Players) > 10),
                     ?assert(Team#team.match_count > 500)
             end),
    bdd:'and'("player records keep their FIFA attributes",
              fun() ->
                      {ok, #{players := [#{player_id := Id} | _]}} =
                          br_query:search_players(#{nationality => <<"Brazil">>, limit => 1}),
                      {ok, P} = br_store:player(Id),
                      ?assert(map_size(P#player.skills) > 20)
              end).

%%--------------------------------------------------------------------
graph_is_consistent_with_the_tables(_Config) ->
    bdd:scenario("The knowledge graph mirrors the stored data"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    bdd:then("there is a node for every match, team and player",
             fun() ->
                     Stats = br_store:stats(),
                     Expected = maps:get(matches, Stats) + maps:get(players, Stats),
                     ?assert(br_graph:node_count() > Expected)
             end),
    bdd:'and'("a team node links back to exactly its matches",
              fun() ->
                      {ok, Id} = br_store:resolve_team(<<"Coritiba">>),
                      Node = br_graph:id(team, Id),
                      Home = br_graph:in(Node, home_team),
                      Away = br_graph:in(Node, away_team),
                      {ok, Team} = br_store:team(Id),
                      ?assertEqual(Team#team.match_count, length(Home) + length(Away))
              end),
    bdd:'and'("every match node points at two teams, a competition and a season",
              fun() ->
                      {ok, #{matches := [#{id := MatchId} | _]}} =
                          br_query:find_matches(#{season => 2019, limit => 1}),
                      Node = br_graph:id(match, MatchId),
                      ?assertMatch([_], br_graph:out(Node, home_team)),
                      ?assertMatch([_], br_graph:out(Node, away_team)),
                      ?assertMatch([_], br_graph:out(Node, in_competition)),
                      ?assertMatch([_], br_graph:out(Node, in_season))
              end).
