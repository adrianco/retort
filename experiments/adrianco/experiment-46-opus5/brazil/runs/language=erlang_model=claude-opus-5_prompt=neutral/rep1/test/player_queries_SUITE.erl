%%%-------------------------------------------------------------------
%%% @doc Feature: Player Queries.
%%%
%%% Context: the FIFA file is the only player source and it has two
%%% quirks that these scenarios pin down: it only carries squads for the
%%% Brazilian clubs the game was licensed for, and it stores positions
%%% as codes (ST, GK, CDM) which the tools also accept as groups
%%% ("forward").  The cross-dataset link (player -> club -> match
%%% record) is asserted here too.
%%% @end
%%%-------------------------------------------------------------------
-module(player_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2,
                    call_tool/2, call_tool_error/2]).

all() ->
    [find_all_brazilian_players,
     highest_rated_players_at_a_club,
     forwards_at_a_club,
     player_profile_by_name,
     player_search_ignores_accents,
     club_ratings_grouping,
     unlicensed_club_explains_itself,
     players_link_to_match_data].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("Player Queries"),
    Config.

%%--------------------------------------------------------------------

find_all_brazilian_players(_Config) ->
    scenario("Find all Brazilian players in the dataset"),
    {Result, Text} = when_("I search players with nationality Brazil", fun() ->
        call_tool(<<"search_players">>, #{<<"nationality">> => <<"Brazil">>,
                                          <<"limit">> => 10})
    end),
    then("more than 800 Brazilians are found", fun() ->
        maps:get(total, Result) > 800
    end),
    and_("they are returned best rated first", fun() ->
        Overalls = [maps:get(overall, P) || P <- maps:get(players, Result)],
        Overalls =:= lists:reverse(lists:sort(Overalls))
    end),
    and_("the top rated Brazilian is Neymar", fun() ->
        maps:get(name, hd(maps:get(players, Result))) =:= <<"Neymar Jr">>
    end),
    and_("the text answer lists rating, position and club", fun() ->
        binary:match(Text, <<"overall 92">>) =/= nomatch
    end).

highest_rated_players_at_a_club(_Config) ->
    scenario("Who are the highest rated players at Gremio?"),
    {Result, _} = when_("I ask for the Gremio squad", fun() ->
        call_tool(<<"club_squad">>, #{<<"club">> => <<"Gremio">>, <<"limit">> => 5})
    end),
    then("a squad with an average rating is returned", fun() ->
        maps:get(squad_size, Result) >= 15
            andalso maps:get(avg_overall, maps:get(summary, Result)) > 60
    end),
    and_("players are ordered by overall rating", fun() ->
        Overalls = [maps:get(overall, P) || P <- maps:get(players, Result)],
        Overalls =:= lists:reverse(lists:sort(Overalls))
    end),
    and_("the club was resolved to the club in the match data", fun() ->
        maps:get(name, maps:get(team, Result)) =:= <<"Grêmio"/utf8>>
    end).

forwards_at_a_club(_Config) ->
    scenario("Show me all forwards from Atletico Mineiro"),
    {Result, _} = when_("I search players by club and position group", fun() ->
        call_tool(<<"search_players">>, #{<<"club">> => <<"Atletico Mineiro">>,
                                          <<"position">> => <<"forward">>})
    end),
    then("at least one forward is found", fun() ->
        maps:get(total, Result) >= 1
    end),
    and_("every returned player plays in an attacking position", fun() ->
        lists:all(fun(#{position := P}) ->
                          lists:member(P, [<<"ST">>, <<"CF">>, <<"LW">>, <<"RW">>,
                                           <<"LF">>, <<"RF">>, <<"LS">>, <<"RS">>])
                  end, maps:get(players, Result))
    end),
    and_("every returned player is at that club", fun() ->
        lists:all(fun(#{club := C}) -> C =:= <<"Atlético Mineiro"/utf8>> end,
                  maps:get(players, Result))
    end).

player_profile_by_name(_Config) ->
    scenario("Who is Neymar?"),
    {Result, Text} = when_("I ask for the player profile", fun() ->
        call_tool(<<"player_profile">>, #{<<"name">> => <<"Neymar">>})
    end),
    P = maps:get(player, Result),
    then("the profile carries ratings, club and position", fun() ->
        maps:get(overall, P) >= 90
            andalso maps:get(nationality, P) =:= <<"Brazil">>
            andalso is_binary(maps:get(club, P))
    end),
    and_("the detailed attributes are present", fun() ->
        map_size(maps:get(skills, P)) > 20
    end),
    and_("the text answer summarises him", fun() ->
        binary:match(Text, <<"Overall">>) =/= nomatch
    end).

player_search_ignores_accents(_Config) ->
    scenario("Accents and case do not matter when searching names"),
    {WithAccent, _} = when_("I search for \"Thiago Silva\"", fun() ->
        call_tool(<<"search_players">>, #{<<"name">> => <<"Thiago Silva">>})
    end),
    {Lower, _} = and_("I search for \"thiago silva\" in lower case", fun() ->
        call_tool(<<"search_players">>, #{<<"name">> => <<"thiago silva">>})
    end),
    then("both searches find the same players", fun() ->
        maps:get(total, WithAccent) =:= maps:get(total, Lower)
            andalso maps:get(total, Lower) >= 1
    end),
    %% take a real accented name out of the data and look it up in ASCII
    AccentedName = given("a player whose name carries accents", fun() ->
        [Name | _] = bsmcp_data:fold_players(
                       fun(#{name := N}, Acc) ->
                               case bsmcp_text:fold_accents(N) =:= N of
                                   true -> Acc;
                                   false -> [N | Acc]
                               end
                       end, []),
        Name
    end),
    Ascii = bsmcp_text:fold_accents(AccentedName),
    {Found, _} = and_("I search for the same name written without accents", fun() ->
        call_tool(<<"search_players">>, #{<<"name">> => Ascii, <<"limit">> => 50})
    end),
    then("the accented record is still found", fun() ->
        lists:member(AccentedName, [maps:get(name, P) || P <- maps:get(players, Found)])
    end).

club_ratings_grouping(_Config) ->
    scenario("Brazilian players grouped by Brazilian club"),
    {Result, Text} = when_("I group Brazilian players by club", fun() ->
        call_tool(<<"club_ratings">>, #{<<"nationality">> => <<"Brazil">>,
                                        <<"brazilian_clubs_only">> => true,
                                        <<"min_players">> => 5,
                                        <<"limit">> => 20})
    end),
    then("at least ten Brazilian clubs have squads", fun() ->
        maps:get(total_clubs, Result) >= 10
    end),
    and_("each row has a squad size and an average rating", fun() ->
        lists:all(fun(C) ->
                          maps:get(players, C) >= 5
                              andalso is_number(maps:get(avg_overall, C))
                  end, maps:get(clubs, Result))
    end),
    and_("the rows are ordered by average rating", fun() ->
        Avgs = [maps:get(avg_overall, C) || C <- maps:get(clubs, Result)],
        Avgs =:= lists:reverse(lists:sort(Avgs))
    end),
    and_("the text answer reads like the specification example", fun() ->
        binary:match(Text, <<"avg rating">>) =/= nomatch
    end).

unlicensed_club_explains_itself(_Config) ->
    scenario("A club with no FIFA squad explains why and offers alternatives"),
    {Error, Text} = when_("I ask for the Flamengo squad", fun() ->
        call_tool_error(<<"club_squad">>, #{<<"club">> => <<"Flamengo">>})
    end),
    then("the tool reports missing squad data, not an unknown club", fun() ->
        maps:get(error, Error) =:= no_squad_data
    end),
    and_("the club is still resolved in the match data", fun() ->
        maps:get(name, maps:get(team, Error)) =:= <<"Flamengo-RJ">>
    end),
    and_("clubs that do have squads are suggested", fun() ->
        length(maps:get(clubs_with_squads, Error)) >= 10
            andalso binary:match(Text, <<"Grêmio"/utf8>>) =/= nomatch
    end).

players_link_to_match_data(_Config) ->
    scenario("Player records link across to the match knowledge graph"),
    {Squad, _} = when_("I fetch the Internacional squad", fun() ->
        call_tool(<<"club_squad">>, #{<<"club">> => <<"Internacional">>, <<"limit">> => 3})
    end),
    TeamId = maps:get(id, maps:get(team, Squad)),
    then("the squad is attached to a team id", fun() ->
        TeamId =:= <<"internacional|RS">>
    end),
    {Profile, _} = and_("I fetch that club's profile", fun() ->
        call_tool(<<"team_profile">>, #{<<"team">> => <<"Internacional">>})
    end),
    then("the profile knows both the matches and the squad", fun() ->
        maps:get(squad_size, Profile) >= 15
            andalso maps:get(played, maps:get(record, Profile)) > 500
    end),
    and_("the top players are listed on the profile", fun() ->
        length(maps:get(top_players, Profile)) =:= 5
    end).
