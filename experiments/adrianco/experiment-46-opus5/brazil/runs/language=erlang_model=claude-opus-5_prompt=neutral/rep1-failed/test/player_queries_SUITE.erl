%%%-------------------------------------------------------------------
%%% @doc Feature: Player Queries
%%%
%%% Search by name, nationality, club and position over the FIFA data,
%%% and the cross-file join from a player to his club's match record.
%%% @end
%%%-------------------------------------------------------------------
-module(player_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

all() ->
    [find_brazilian_players,
     highest_rated_players_of_a_club,
     search_by_position_word,
     player_profile_by_name,
     unknown_player_suggests_alternatives,
     players_grouped_by_club,
     cross_file_player_to_match_data,
     squad_of_a_club_without_fifa_licence].

init_per_suite(Config) ->
    bdd:feature("Player Queries"),
    bdd:data_is_loaded(),
    Config.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
find_brazilian_players(_Config) ->
    bdd:scenario("Find all Brazilian players in the data set"),
    bdd:given("the player data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I search for players with nationality Brazil",
                        fun() ->
                                {ok, R} = br_query:search_players(
                                            #{nationality => <<"Brazil">>, limit => 10}),
                                R
                        end),
    bdd:then("I should get several hundred players",
             fun() -> ?assert(maps:get(total, Result) > 700) end),
    bdd:'and'("they should be sorted by rating, best first",
              fun() ->
                      Overalls = [maps:get(overall, P) || P <- maps:get(players, Result)],
                      ?assertEqual(lists:reverse(lists:sort(Overalls)), Overalls)
              end),
    bdd:'and'("the best rated Brazilian should be Neymar",
              fun() ->
                      [#{name := Name, overall := Overall} | _] = maps:get(players, Result),
                      ?assertNotEqual(nomatch, binary:match(Name, <<"Neymar">>)),
                      ?assertEqual(92, Overall)
              end),
    bdd:'and'("every returned player should be Brazilian",
              fun() ->
                      lists:foreach(fun(#{nationality := N}) ->
                                            ?assertEqual(<<"Brazil">>, N)
                                    end, maps:get(players, Result))
              end).

%%--------------------------------------------------------------------
highest_rated_players_of_a_club(_Config) ->
    bdd:scenario("Who are the highest rated players at a club?"),
    bdd:given("the player data is loaded", fun bdd:data_is_loaded/0),
    Squad = bdd:'when'("I ask for the Gremio squad",
                       fun() ->
                               {ok, S} = br_query:club_squad(#{club => <<"Gremio">>}),
                               S
                       end),
    bdd:then("the squad should be sorted by overall rating",
             fun() ->
                     Overalls = [maps:get(overall, P) || P <- maps:get(players, Squad)],
                     ?assert(length(Overalls) > 10),
                     ?assertEqual(lists:reverse(lists:sort(Overalls)), Overalls)
             end),
    bdd:'and'("an average rating should be reported",
              fun() ->
                      Avg = maps:get(average_overall, Squad),
                      ?assert(is_number(Avg)),
                      ?assert(Avg > 50 andalso Avg < 100)
              end).

%%--------------------------------------------------------------------
search_by_position_word(_Config) ->
    bdd:scenario("Show me all forwards from a club"),
    bdd:given("the player data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I search for forwards at Santos",
                        fun() ->
                                {ok, R} = br_query:search_players(#{club => <<"Santos">>,
                                                                    position => <<"forward">>,
                                                                    limit => 50}),
                                R
                        end),
    bdd:then("only attacking positions should be returned",
             fun() ->
                     Positions = [maps:get(position, P) || P <- maps:get(players, Result)],
                     ?assert(length(Positions) > 0),
                     lists:foreach(
                       fun(Pos) ->
                               ?assert(lists:member(Pos, [<<"ST">>, <<"CF">>, <<"LW">>,
                                                          <<"RW">>, <<"LS">>, <<"RS">>,
                                                          <<"LF">>, <<"RF">>]))
                       end, Positions)
             end),
    bdd:'and'("a FIFA position code should work as well",
              fun() ->
                      {ok, #{players := Keepers}} =
                          br_query:search_players(#{position => <<"GK">>, limit => 5}),
                      lists:foreach(fun(#{position := P}) -> ?assertEqual(<<"GK">>, P) end,
                                    Keepers)
              end).

%%--------------------------------------------------------------------
player_profile_by_name(_Config) ->
    bdd:scenario("Who is Neymar?"),
    bdd:given("the player data is loaded", fun bdd:data_is_loaded/0),
    Profile = bdd:'when'("I ask for the profile of Neymar",
                         fun() ->
                                 {ok, P} = br_query:player_profile(#{name => <<"Neymar">>}),
                                 P
                         end),
    bdd:then("I should get his ratings and attributes",
             fun() ->
                     ?assertEqual(<<"Brazil">>, maps:get(nationality, Profile)),
                     ?assertEqual(92, maps:get(overall, Profile)),
                     ?assert(is_map(maps:get(skills, Profile))),
                     ?assert(length(maps:get(top_skills, Profile)) > 0)
             end),
    bdd:'and'("the profile can also be fetched by FIFA id",
              fun() ->
                      Id = maps:get(player_id, Profile),
                      {ok, ById} = br_query:player_profile(#{player_id => Id}),
                      ?assertEqual(maps:get(name, Profile), maps:get(name, ById))
              end).

%%--------------------------------------------------------------------
unknown_player_suggests_alternatives(_Config) ->
    bdd:scenario("A player who is not in the FIFA data"),
    bdd:given("the player data is loaded", fun bdd:data_is_loaded/0),
    Error = bdd:'when'("I ask about a player who is not in fifa_data.csv",
                       fun() ->
                               {error, E} = br_query:player_profile(
                                              #{name => <<"Gabriel Barbosa">>}),
                               E
                       end),
    bdd:then("the answer should say so and suggest similar names",
             fun() ->
                     ?assertEqual(unknown_player, maps:get(code, Error)),
                     Suggestions = maps:get(suggestions, Error),
                     ?assert(length(Suggestions) > 0),
                     ct:log("suggestions: ~p", [Suggestions])
             end).

%%--------------------------------------------------------------------
players_grouped_by_club(_Config) ->
    bdd:scenario("Brazilian players at Brazilian clubs"),
    bdd:given("the player data is loaded", fun bdd:data_is_loaded/0),
    Summary = bdd:'when'("I group Brazilian players by club",
                         fun() ->
                                 {ok, S} = br_query:player_club_summary(
                                             #{nationality => <<"Brazil">>,
                                               only_clubs_in_match_data => true,
                                               limit => 30}),
                                 S
                         end),
    bdd:then("each club should have a count and an average rating",
             fun() ->
                     Clubs = maps:get(by_club, Summary),
                     ?assert(length(Clubs) > 5),
                     lists:foreach(
                       fun(C) ->
                               ?assert(is_integer(maps:get(players, C))),
                               ?assert(is_number(maps:get(average_overall, C))),
                               ?assertMatch(#{best := #{name := <<_/binary>>}}, C)
                       end, Clubs)
             end),
    bdd:'and'("the clubs should be the ones that also appear in the match data",
              fun() ->
                      lists:foreach(
                        fun(#{club := ClubId}) ->
                                ?assertNotEqual(error, br_store:team(ClubId))
                        end, maps:get(by_club, Summary))
              end).

%%--------------------------------------------------------------------
cross_file_player_to_match_data(_Config) ->
    bdd:scenario("A player links to his club's match record (cross-file query)"),
    bdd:given("both data sets are loaded", fun bdd:data_is_loaded/0),
    Profile = bdd:'when'("I look at a player of a club that plays in the Brasileirao",
                         fun() ->
                                 {ok, #{players := [P | _]}} =
                                     br_query:search_players(#{club => <<"Cruzeiro">>,
                                                               limit => 1}),
                                 {ok, Detail} = br_query:player_profile(
                                                  #{player_id => maps:get(player_id, P)}),
                                 Detail
                         end),
    bdd:then("his club should carry its match record from the other files",
             fun() ->
                     Club = maps:get(club_in_match_data, Profile),
                     ?assertNotEqual(null, Club),
                     ?assert(maps:get(matches_in_dataset, Club) > 100),
                     ?assert(lists:member(<<"brasileirao_serie_a">>,
                                          maps:get(competitions, Club)))
             end),
    bdd:'and'("the knowledge graph should connect the player to the competition",
              fun() ->
                      PlayerNode = br_graph:id(player, maps:get(player_id, Profile)),
                      {ok, Path} = br_query:graph_path(
                                     #{from => PlayerNode,
                                       to => <<"competition:brasileirao_serie_a">>,
                                       max_depth => 4}),
                      ?assertEqual(true, maps:get(found, Path)),
                      ?assert(maps:get(length, Path) =< 3)
              end).

%%--------------------------------------------------------------------
squad_of_a_club_without_fifa_licence(_Config) ->
    bdd:scenario("A club with match data but no FIFA squad says so"),
    bdd:given("both data sets are loaded", fun bdd:data_is_loaded/0),
    Squad = bdd:'when'("I ask for the Flamengo squad",
                       fun() ->
                               {ok, S} = br_query:club_squad(#{club => <<"Flamengo">>}),
                               S
                       end),
    bdd:then("the result should be empty but explain why",
             fun() ->
                     ?assertEqual(0, maps:get(squad_size, Squad)),
                     Note = maps:get(note, Squad),
                     ?assertNotEqual(nomatch, binary:match(Note, <<"fifa_data.csv">>))
             end),
    bdd:'and'("a player search filtered by that club explains it too",
              fun() ->
                      {ok, Result} = br_query:search_players(#{club => <<"Sao Paulo">>,
                                                               position => <<"forward">>}),
                      ?assertEqual(0, maps:get(total, Result)),
                      Text = br_format:render(search_players, Result),
                      ?assertNotEqual(nomatch, binary:match(Text, <<"fifa_data.csv">>)),
                      ?assertNotEqual(nomatch, binary:match(Text, <<"matches">>))
              end),
    bdd:'and'("a search that legitimately finds nothing carries no such note",
              fun() ->
                      {ok, Result} = br_query:search_players(#{name => <<"Zzzz">>}),
                      ?assertEqual(0, maps:get(total, Result)),
                      ?assertEqual(null, maps:get(note, Result))
              end).
