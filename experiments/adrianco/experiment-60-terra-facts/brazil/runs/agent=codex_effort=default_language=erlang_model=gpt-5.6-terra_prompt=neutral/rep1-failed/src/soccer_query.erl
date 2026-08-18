-module(soccer_query).
-export([matches/2, team_stats/3, head_to_head/3, players/2, standings/3, biggest_wins/2, answer/2]).

matches(Data, Filters) ->
    lists:sort(fun newer/2, [M || M <- maps:get(matches, Data), match_filter(M, Filters)]).
team_stats(Data, Team, Filters) ->
    Key = soccer_data:normalize_team(Team), Ms = [M || M <- matches(Data, Filters), involved(M, Key)],
    lists:foldl(fun(M, A) -> add_record(M, Key, A) end, #{team => Team, matches => 0, wins => 0, draws => 0, losses => 0, goals_for => 0, goals_against => 0}, Ms).
head_to_head(Data, A, B) ->
    AK = soccer_data:normalize_team(A), BK = soccer_data:normalize_team(B),
    Ms = [M || M <- maps:get(matches,Data), (maps:get(home_key,M)=:=AK andalso maps:get(away_key,M)=:=BK) orelse (maps:get(home_key,M)=:=BK andalso maps:get(away_key,M)=:=AK)],
    Base = #{team_a => A, team_b => B, team_a_wins => 0, team_b_wins => 0, draws => 0, matches => Ms},
    lists:foldl(fun(M, R) ->
        HG=maps:get(home_goals,M), AG=maps:get(away_goals,M), Home=maps:get(home_key,M), Away=maps:get(away_key,M),
        Winner = if HG=:=AG -> draw; (Home=:=AK andalso HG>AG) orelse (Away=:=AK andalso AG>HG) -> a; true -> b end,
        maps:update_with(case Winner of a->team_a_wins;b->team_b_wins;draw->draws end, fun(X)->X+1 end, R)
    end, Base, Ms).
players(Data, Filters) ->
    lists:sort(fun(A,B)->maps:get(overall,A)>=maps:get(overall,B) end, [P || P <- maps:get(players,Data), player_filter(P,Filters)]).
standings(Data, Competition, Season) ->
    Ms = matches(Data, #{competition=>Competition, season=>Season}),
    Table = lists:foldl(fun table_match/2, #{}, Ms),
    lists:sort(fun(A,B) -> {maps:get(points,A),maps:get(goal_difference,A),maps:get(goals_for,A)} >= {maps:get(points,B),maps:get(goal_difference,B),maps:get(goals_for,B)} end, maps:values(Table)).
biggest_wins(Data, Filters) -> lists:sort(fun(A,B)->margin(A)>=margin(B) end, matches(Data, Filters)).

answer(Data, Question) ->
    Q = soccer_data:normalize_text(Question),
    case {contains(Q,"highest-rated"), contains(Q,"player")} of
      {true,_} -> #{kind=>players, results=>lists:sublist(players(Data, #{}), 10)};
      _ -> case contains(Q,"biggest win") of
        true -> #{kind=>matches, results=>lists:sublist(biggest_wins(Data,#{}),10)};
        false -> #{kind=>matches, results=>lists:sublist(matches(Data, #{}),20)}
      end
    end.

match_filter(M, F) ->
    Team = maps:get(team,F,undefined), Opp = maps:get(opponent,F,undefined), Competition=maps:get(competition,F,undefined), Season=maps:get(season,F,undefined),
    Date = normalized_date(maps:get(date,M)), From = maps:get(date_from,F,undefined), To = maps:get(date_to,F,undefined),
    (Team=:=undefined orelse involved(M,soccer_data:normalize_team(Team))) andalso
    (Opp=:=undefined orelse involved(M,soccer_data:normalize_team(Opp))) andalso
    (Competition=:=undefined orelse maps:get(competition,M)=:=Competition) andalso (Season=:=undefined orelse maps:get(season,M)=:=Season) andalso
    (From=:=undefined orelse Date >= normalized_date(From)) andalso (To=:=undefined orelse Date =< normalized_date(To)).
player_filter(P,F) ->
    text_filter(maps:get(name_key,P), maps:get(name,F,undefined)) andalso text_filter(soccer_data:normalize_text(maps:get(nationality,P)),maps:get(nationality,F,undefined)) andalso text_filter(maps:get(club_key,P),maps:get(club,F,undefined)) andalso text_filter(soccer_data:normalize_text(maps:get(position,P)),maps:get(position,F,undefined)).
text_filter(_,undefined)->true; text_filter(Value,Query)->contains(Value,soccer_data:normalize_text(Query)).
involved(M,K)->maps:get(home_key,M)=:=K orelse maps:get(away_key,M)=:=K.
newer(A,B)->maps:get(date,A)>=maps:get(date,B).
margin(M)->abs(maps:get(home_goals,M)-maps:get(away_goals,M)).
add_record(M,K,A) ->
    Home=maps:get(home_key,M)=:=K, GF=if Home->maps:get(home_goals,M);true->maps:get(away_goals,M) end, GA=if Home->maps:get(away_goals,M);true->maps:get(home_goals,M) end,
    Result=if GF>GA->wins;GF=:=GA->draws;true->losses end,
    maps:update_with(goals_against,fun(X)->X+GA end,maps:update_with(goals_for,fun(X)->X+GF end,maps:update_with(Result,fun(X)->X+1 end,maps:update_with(matches,fun(X)->X+1 end,A)))).
table_match(M,T) -> add_table(maps:get(away,M),maps:get(away_goals,M),maps:get(home_goals,M), add_table(maps:get(home,M),maps:get(home_goals,M),maps:get(away_goals,M),T)).
add_table(Name,GF,GA,T) -> Old=maps:get(Name,T,#{team=>Name,matches=>0,wins=>0,draws=>0,losses=>0,goals_for=>0,goals_against=>0,points=>0,goal_difference=>0}), Result=if GF>GA->wins;GF=:=GA->draws;true->losses end, P=case Result of wins->3;draws->1;_->0 end, New=maps:put(goal_difference,maps:get(goals_for,Old)+GF-maps:get(goals_against,Old)-GA,maps:update_with(points,fun(X)->X+P end,maps:update_with(goals_against,fun(X)->X+GA end,maps:update_with(goals_for,fun(X)->X+GF end,maps:update_with(Result,fun(X)->X+1 end,maps:update_with(matches,fun(X)->X+1 end,Old)))))), maps:put(Name,New,T).
contains(S,Sub) -> string:find(S,Sub) =/= nomatch.
normalized_date(S) ->
    case re:run(S, "^([0-9]{2})/([0-9]{2})/([0-9]{4})", [{capture,[1,2,3],list}]) of
        {match,[D,M,Y]} -> Y ++ "-" ++ M ++ "-" ++ D;
        _ -> lists:sublist(S, min(10, length(S)))
    end.
