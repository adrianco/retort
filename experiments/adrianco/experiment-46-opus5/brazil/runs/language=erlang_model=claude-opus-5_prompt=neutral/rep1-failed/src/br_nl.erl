%%%-------------------------------------------------------------------
%%% @doc A small natural language router.
%%%
%%% The MCP server is normally driven by an LLM, which picks the tool
%%% and fills in the arguments.  This module does the same job with
%%% keyword patterns so that the server can also be used - and tested -
%%% without a model: it extracts the entities mentioned in a question
%%% (teams, season, competition, position, nationality), decides which
%%% query answers it, and runs it.
%%%
%%% It is deliberately transparent: the result says which tool was
%%% chosen and with which arguments, so a caller can see how the
%%% question was interpreted.
%%% @end
%%%-------------------------------------------------------------------
-module(br_nl).

-include("br_soccer.hrl").

-export([answer/1, plan/1]).

%%--------------------------------------------------------------------
%% @doc Answer a question: pick a tool, run it, render the result.
-spec answer(term()) -> {ok, map()} | {error, map()}.
answer(Question) ->
    #{tool := Tool, arguments := Args} = Plan = plan(Question),
    case br_mcp_tools:invoke(Tool, Args) of
        {ok, Result} ->
            {ok, #{question => br_text:to_binary(Question),
                   tool => Tool,
                   arguments => Args,
                   interpretation => maps:get(interpretation, Plan),
                   answer => br_mcp_tools:render(Tool, Result),
                   data => Result}};
        {error, E} ->
            {error, E#{question => br_text:to_binary(Question),
                       tool => Tool,
                       arguments => Args}}
    end.

%%--------------------------------------------------------------------
%% @doc Which tool would answer this question, and with what arguments?
-spec plan(term()) -> map().
plan(Question) ->
    Q = br_text:normalize(Question),
    Entities = entities(Q),
    {Tool, Args} = route(Q, Entities),
    #{tool => Tool,
      arguments => Args,
      interpretation => interpretation(Tool, Args, Entities)}.

%%====================================================================
%% Entity extraction
%%====================================================================

entities(Q) ->
    Derby = derby_in(Q),
    Teams = case Derby of
                {_Name, A, B} -> [A, B];
                undefined -> teams_in(Q)
            end,
    #{teams => Teams,
      derby => Derby,
      season => season_in(Q),
      competition => competition_in(Q),
      position => position_in(Q),
      nationality => nationality_in(Q),
      quoted => quoted_in(Q)}.

%% "What was the score in the last Gre-Nal?" names the fixture, not the
%% clubs, so the derby names are entities in their own right.
derby_in(Q) ->
    case [R || {Name, _, _} = R <- br_names:rivalries(),
               contains(Q, br_text:normalize(Name))] of
        [Rivalry | _] -> Rivalry;
        [] -> undefined
    end.

%% Longest matching team names first, so that "atletico mineiro" is not
%% shadowed by "atletico" and "sao paulo" is found before "santos".
teams_in(Q) ->
    Tokens = binary:split(Q, <<" ">>, [global]),
    Candidates = ngrams(Tokens, 4),
    Found = lists:foldl(
              fun(Phrase, Acc) ->
                      case lists:any(fun({_, P}) -> overlaps(P, Phrase) end, Acc) of
                          true -> Acc;
                          false ->
                              case lookup_team(Phrase) of
                                  {ok, Id} -> [{Id, Phrase} | Acc];
                                  error -> Acc
                              end
                      end
              end, [], Candidates),
    lists:usort([Id || {Id, _} <- lists:reverse(Found)]).

%% Reject phrases that are part of an already matched, longer phrase.
overlaps(Longer, Shorter) ->
    binary:match(Longer, Shorter) =/= nomatch.

ngrams(Tokens, MaxN) ->
    N = length(Tokens),
    [br_text:join(lists:sublist(Tokens, Start, Len), <<" ">>)
     || Len <- lists:seq(min(MaxN, N), 1, -1),
        Start <- lists:seq(1, N - Len + 1)].

%% Only accept a phrase if it names a team exactly - a substring search
%% would match far too much ("the" -> "Athletico").
lookup_team(Phrase) ->
    case lists:member(Phrase, stopwords()) of
        true -> error;
        false ->
            Id = br_names:canonical_id(Phrase),
            case br_store:team(Id) of
                {ok, #team{match_count = C}} when C > 0 -> {ok, Id};
                _ ->
                    case exact_team_name(Phrase) of
                        {ok, TeamId} -> {ok, TeamId};
                        error -> error
                    end
            end
    end.

exact_team_name(Phrase) ->
    case [T || T <- br_store:search_teams(Phrase),
               lists:any(fun(N) -> br_text:normalize(N) =:= Phrase end,
                         [T#team.name | T#team.aliases])] of
        [#team{id = Id} | _] -> {ok, Id};
        [] -> error
    end.

stopwords() ->
    [<<"the">>, <<"a">>, <<"in">>, <<"of">>, <<"and">>, <<"or">>, <<"vs">>, <<"versus">>,
     <<"is">>, <<"was">>, <<"who">>, <<"what">>, <<"when">>, <<"where">>, <<"how">>,
     <<"me">>, <<"all">>, <<"show">>, <<"find">>, <<"list">>, <<"do">>, <<"does">>,
     <<"did">>, <<"play">>, <<"played">>, <<"match">>, <<"matches">>, <<"game">>,
     <<"games">>, <<"team">>, <<"teams">>, <<"season">>, <<"best">>, <<"most">>,
     <<"record">>, <<"records">>, <<"goals">>, <<"score">>, <<"scored">>, <<"players">>,
     <<"player">>, <<"cup">>, <<"copa">>, <<"serie">>, <<"real">>, <<"between">>].

season_in(Q) ->
    case re_years(Q) of
        [Y | _] -> Y;
        [] -> undefined
    end.

re_years(Q) ->
    [binary_to_integer(Tok)
     || Tok <- binary:split(Q, <<" ">>, [global]),
        byte_size(Tok) =:= 4,
        is_digits(Tok),
        binary_to_integer(Tok) >= 1950,
        binary_to_integer(Tok) =< 2100].

is_digits(<<>>) -> false;
is_digits(Bin) ->
    lists:all(fun(C) -> C >= $0 andalso C =< $9 end, binary_to_list(Bin)).

competition_in(Q) ->
    Checks = [{<<"libertadores">>, <<"libertadores">>},
              {<<"copa do brasil">>, <<"copa_do_brasil">>},
              {<<"brazilian cup">>, <<"copa_do_brasil">>},
              {<<"serie b">>, <<"brasileirao_serie_b">>},
              {<<"serie c">>, <<"brasileirao_serie_c">>},
              {<<"serie a">>, <<"brasileirao_serie_a">>},
              {<<"brasileirao">>, <<"brasileirao_serie_a">>},
              {<<"brasileirao serie a">>, <<"brasileirao_serie_a">>},
              {<<"campeonato brasileiro">>, <<"brasileirao_serie_a">>}],
    case [C || {Needle, C} <- Checks, contains(Q, Needle)] of
        [C | _] -> C;
        [] -> undefined
    end.

position_in(Q) ->
    Words = [<<"forward">>, <<"striker">>, <<"winger">>, <<"midfielder">>, <<"defender">>,
             <<"goalkeeper">>],
    case [W || W <- Words, contains(Q, W)] of
        [W | _] -> W;
        [] -> undefined
    end.

nationality_in(Q) ->
    Map = [{<<"brazilian">>, <<"Brazil">>}, {<<"argentin">>, <<"Argentina">>},
           {<<"uruguayan">>, <<"Uruguay">>}, {<<"portuguese">>, <<"Portugal">>},
           {<<"colombian">>, <<"Colombia">>}, {<<"chilean">>, <<"Chile">>},
           {<<"spanish">>, <<"Spain">>}, {<<"french">>, <<"France">>},
           {<<"english">>, <<"England">>}, {<<"german">>, <<"Germany">>},
           {<<"italian">>, <<"Italy">>}],
    case [N || {Needle, N} <- Map, contains(Q, Needle)] of
        [N | _] -> N;
        [] -> undefined
    end.

%% Text after "who is" / "find" that is not a known team is treated as a
%% player name.
quoted_in(Q) ->
    Prefixes = [<<"who is ">>, <<"tell me about ">>, <<"profile of ">>],
    case [Rest || P <- Prefixes,
                  {Pos, Len} <- [safe_match(Q, P)],
                  Pos =/= nomatch,
                  Rest <- [binary:part(Q, Pos + Len, byte_size(Q) - Pos - Len)]] of
        [Rest | _] -> br_text:trim(Rest);
        [] -> undefined
    end.

safe_match(Q, P) ->
    case binary:match(Q, P) of
        nomatch -> {nomatch, 0};
        Match -> Match
    end.

contains(Q, Needle) -> binary:match(Q, Needle) =/= nomatch.

contains_any(Q, Needles) -> lists:any(fun(N) -> contains(Q, N) end, Needles).

%%====================================================================
%% Routing
%%====================================================================

route(Q, E) ->
    #{teams := Teams, season := Season, competition := Comp} = E,
    Base = base_args(Season, Comp),
    case classify(Q, E) of
        standings ->
            {<<"standings">>,
             Base#{competition => default(Comp, <<"brasileirao_serie_a">>),
                   season => Season}};
        relegated ->
            {<<"standings">>,
             Base#{competition => default(Comp, <<"brasileirao_serie_a">>),
                   season => Season}};
        head_to_head ->
            [A, B | _] = Teams,
            {<<"head_to_head">>, Base#{team_a => A, team_b => B, limit => 10}};
        derbies ->
            {<<"derbies">>, Base};
        team_rankings ->
            {<<"team_rankings">>, Base#{metric => metric_of(Q), venue => venue_of(Q),
                                        limit => 10}};
        competition_stats ->
            {<<"competition_stats">>, Base};
        biggest_wins ->
            Args = case Teams of
                       [T | _] -> Base#{team => T};
                       [] -> Base
                   end,
            {<<"biggest_wins">>, Args#{limit => 10}};
        compare_seasons ->
            case re_years(Q) of
                [A, B | _] -> {<<"compare_seasons">>,
                               #{competition => default(Comp, <<"brasileirao_serie_a">>),
                                 season_a => A, season_b => B}};
                _ -> {<<"competition_stats">>, Base}
            end;
        team_stats ->
            [T | _] = Teams,
            {<<"team_stats">>, Base#{team => T, venue => venue_of(Q)}};
        team_profile ->
            [T | _] = Teams,
            {<<"team_profile">>, #{team => T}};
        club_squad ->
            [T | _] = Teams,
            {<<"club_squad">>, #{club => T, limit => 20}};
        player_club_summary ->
            {<<"players_by_club">>,
             #{nationality => default(maps:get(nationality, E), <<"Brazil">>),
               only_clubs_in_match_data => true, limit => 20}};
        player_profile ->
            {<<"player_profile">>, #{name => player_name(Q, E)}};
        search_players ->
            Args0 = #{limit => 10, sort => <<"overall_desc">>},
            Args1 = maybe_put(nationality, maps:get(nationality, E), Args0),
            Args2 = maybe_put(position, maps:get(position, E), Args1),
            Args3 = case Teams of
                        [T | _] -> Args2#{club => T};
                        [] -> Args2
                    end,
            {<<"search_players">>, Args3};
        last_match ->
            [A, B | _] = Teams,
            {<<"search_matches">>, Base#{team => A, opponent => B, limit => 1,
                                         sort => <<"date_desc">>}};
        find_matches ->
            Args = case Teams of
                       [A, B | _] -> Base#{team => A, opponent => B};
                       [A] -> Base#{team => A};
                       [] -> Base
                   end,
            {<<"search_matches">>, Args#{limit => 10}};
        dataset_summary ->
            {<<"dataset_summary">>, #{}}
    end.

%% The first matching rule wins, so the order below is the routing
%% policy: specific phrasings first, generic fallbacks last.
classify(Q, #{teams := Teams} = E) ->
    N = length(Teams),
    Player = looks_like_player_question(Q, E),
    Has = fun(Needles) -> contains_any(Q, Needles) end,
    Rules =
        %% "in the dataset" appears in many questions, so only phrases
        %% that ask *about* the data route to the summary.
        [{fun() -> Has([<<"data sets are loaded">>, <<"data set is loaded">>,
                        <<"what data">>, <<"which files">>, <<"how much data">>,
                        <<"dataset summary">>, <<"data set summary">>,
                        <<"what is loaded">>]) end, dataset_summary},
         {fun() -> Has([<<"relegated">>, <<"relegation">>]) end, relegated},
         {fun() -> Has([<<"standings">>, <<"final table">>, <<"league table">>,
                        <<"who won the">>, <<"champion">>, <<"winner of">>]) end, standings},
         {fun() -> Has([<<"derby">>, <<"derbies">>, <<"classico">>, <<"clasico">>]) end,
          derbies},
         {fun() -> Has([<<"compare the">>, <<"compare seasons">>])
                       andalso length(re_years(Q)) >= 2 end, compare_seasons},
         {fun() -> Has([<<"biggest win">>, <<"biggest victor">>, <<"biggest defeat">>,
                        <<"heaviest">>, <<"highest scoring">>]) end, biggest_wins},
         {fun() -> not Player
                       andalso Has([<<"which team">>, <<"which club">>,
                                    <<"who has the best">>, <<"best home record">>,
                                    <<"best away record">>, <<"most goals">>,
                                    <<"best defence">>, <<"best defense">>]) end,
          team_rankings},
         {fun() -> Has([<<"average goals">>, <<"goals per match">>, <<"goals per game">>,
                        <<"home win rate">>, <<"how many goals were">>]) end,
          competition_stats},
         {fun() -> Player andalso Has([<<"who is">>, <<"tell me about">>,
                                       <<"profile of">>]) end, player_profile},
         {fun() -> Player andalso N >= 1
                       andalso Has([<<"play for">>, <<"plays for">>, <<"squad">>,
                                    <<"players at">>, <<"players of">>,
                                    <<"players from">>, <<"roster">>]) end, club_squad},
         {fun() -> Player andalso Has([<<"by club">>, <<"at brazilian clubs">>,
                                       <<"per club">>]) end, player_club_summary},
         {fun() -> Player end, search_players},
         {fun() -> N >= 2 andalso Has([<<"last play">>, <<"last played">>,
                                       <<"last meet">>, <<"most recent">>,
                                       <<"last time">>, <<"the last ">>,
                                       <<"latest">>]) end, last_match},
         {fun() -> N >= 2 end, head_to_head},
         {fun() -> N =:= 1 andalso Has([<<"competitions">>, <<"profile">>,
                                        <<"tell me about">>, <<"history">>]) end,
          team_profile},
         {fun() -> N =:= 1 andalso Has([<<"record">>, <<"statistics">>, <<"stats">>,
                                        <<"how did">>, <<"how many points">>,
                                        <<"win rate">>, <<"form">>]) end, team_stats},
         {fun() -> N =:= 1 end, find_matches},
         {fun() -> Has([<<"average">>, <<"how many matches">>, <<"goals">>]) end,
          competition_stats}],
    first_rule(Rules, find_matches).

first_rule([], Default) -> Default;
first_rule([{Predicate, Result} | Rest], Default) ->
    case Predicate() of
        true -> Result;
        false -> first_rule(Rest, Default)
    end.

looks_like_player_question(Q, #{position := Pos, nationality := Nat}) ->
    contains_any(Q, [<<"player">>, <<"players">>, <<"rated">>, <<"rating">>,
                     <<"who is">>, <<"squad">>, <<"striker">>, <<"forward">>,
                     <<"midfielder">>, <<"defender">>, <<"goalkeeper">>, <<"roster">>])
        orelse (Pos =/= undefined andalso Nat =/= undefined).

metric_of(Q) ->
    case contains_any(Q, [<<"most goals">>, <<"scored the most">>, <<"best attack">>]) of
        true -> <<"goals_for">>;
        false ->
            case contains_any(Q, [<<"best defence">>, <<"best defense">>,
                                  <<"fewest goals">>, <<"conceded">>]) of
                true -> <<"goals_against">>;
                false ->
                    case contains(Q, <<"win rate">>) of
                        true -> <<"win_rate">>;
                        false -> <<"points">>
                    end
            end
    end.

venue_of(Q) ->
    case {contains(Q, <<"home">>), contains(Q, <<"away">>)} of
        {true, false} -> <<"home">>;
        {false, true} -> <<"away">>;
        _ -> <<"any">>
    end.

%% "Who is Gabriel Barbosa?" -> "gabriel barbosa"
player_name(Q, #{quoted := Quoted}) ->
    case Quoted of
        undefined -> Q;
        <<>> -> Q;
        Name -> Name
    end.

base_args(undefined, undefined) -> #{};
base_args(Season, undefined) -> #{season => Season};
base_args(undefined, Comp) -> #{competition => Comp};
base_args(Season, Comp) -> #{season => Season, competition => Comp}.

default(undefined, Default) -> Default;
default(V, _) -> V.

maybe_put(_Key, undefined, Map) -> Map;
maybe_put(Key, Value, Map) -> Map#{Key => Value}.

interpretation(Tool, Args, #{teams := Teams}) ->
    Parts = [<<"tool=">>, Tool,
             case Teams of
                 [] -> <<>>;
                 _ -> <<" teams=", (br_text:join(Teams, <<","/utf8>>))/binary>>
             end,
             case maps:get(season, Args, undefined) of
                 undefined -> <<>>;
                 S -> <<" season=", (br_text:to_binary(S))/binary>>
             end,
             case maps:get(competition, Args, undefined) of
                 undefined -> <<>>;
                 C -> <<" competition=", (br_text:to_binary(C))/binary>>
             end],
    iolist_to_binary(Parts).
