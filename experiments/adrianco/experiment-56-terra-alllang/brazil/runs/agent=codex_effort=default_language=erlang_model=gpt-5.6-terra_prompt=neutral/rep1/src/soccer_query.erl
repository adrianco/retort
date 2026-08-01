-module(soccer_query).
-export([find_matches/1, team_stats/1, head_to_head/2, find_players/1, standings/2, biggest_wins/1, answer/1]).

find_matches(Filters) ->
    lists:sort(fun(A,B) -> maps:get(date,A) >= maps:get(date,B) end,
      [M || M <- soccer_data:matches(), matches(M, Filters)]).
matches(M, F) ->
    Team = soccer_data:normalize_team(get(F, team, <<>>)), Team2 = soccer_data:normalize_team(get(F, opponent, <<>>)),
    Season = to_int(get(F, season, 0)), Comp = lower(get(F, competition, <<>>)),
    From = get(F, from, <<>>), To = get(F, to, <<>>), Round = lower(get(F, round, <<>>)),
    (Team =:= <<>> orelse maps:get(home_key,M) =:= Team orelse maps:get(away_key,M) =:= Team) andalso
    (Team2 =:= <<>> orelse (maps:get(home_key,M) =:= Team2 orelse maps:get(away_key,M) =:= Team2)) andalso
    (Season =:= 0 orelse maps:get(season,M) =:= Season) andalso
    (Comp =:= <<>> orelse contains(lower(maps:get(competition,M)), Comp)) andalso
    (Round =:= <<>> orelse contains(lower(maps:get(round,M)), Round)) andalso
    (From =:= <<>> orelse maps:get(date,M) >= From) andalso (To =:= <<>> orelse maps:get(date,M) =< To).

team_stats(F) ->
    Team = soccer_data:normalize_team(get(F, team, <<>>)), Scope = get(F, scope, <<"either">>),
    Ms = [M || M <- find_matches(F), (Scope =/= <<"home">> orelse maps:get(home_key,M)=:=Team), (Scope =/= <<"away">> orelse maps:get(away_key,M)=:=Team)],
    S = lists:foldl(fun(M, A) -> home_or_away(M, Team, A) end, #{matches=>0,wins=>0,draws=>0,losses=>0,goals_for=>0,goals_against=>0}, Ms),
    S#{team => get(F, team, <<>>), win_rate => rate(maps:get(wins,S), maps:get(matches,S))}.
home_or_away(M, Team, A) ->
    {GF,GA} = case maps:get(home_key,M)=:=Team of true -> {maps:get(home_goals,M),maps:get(away_goals,M)}; false -> {maps:get(away_goals,M),maps:get(home_goals,M)} end,
    Result = if GF > GA -> wins; GF =:= GA -> draws; true -> losses end,
    A#{matches := maps:get(matches,A)+1, goals_for := maps:get(goals_for,A)+GF, goals_against := maps:get(goals_against,A)+GA, Result := maps:get(Result,A)+1}.
head_to_head(A, B) ->
    AK = soccer_data:normalize_team(A), BK = soccer_data:normalize_team(B), Ms = [M || M <- soccer_data:matches(), (maps:get(home_key,M)=:=AK andalso maps:get(away_key,M)=:=BK) orelse (maps:get(home_key,M)=:=BK andalso maps:get(away_key,M)=:=AK)],
    R = lists:foldl(fun(M, X) ->
        HG=maps:get(home_goals,M), AG=maps:get(away_goals,M), HK=maps:get(home_key,M), AK0=maps:get(away_key,M),
        Winner = if HG=:=AG -> draws; (HK=:=AK andalso HG>AG) orelse (AK0=:=AK andalso AG>HG) -> team_a_wins; true -> team_b_wins end,
        X#{Winner := maps:get(Winner,X)+1}
    end, #{team_a_wins=>0,team_b_wins=>0,draws=>0}, Ms), R#{team_a=>A, team_b=>B, matches=>length(Ms)}.
find_players(F) ->
    Name=lower(get(F,name,<<>>)), Nationality=lower(get(F,nationality,<<>>)), Club=lower(get(F,club,<<>>)), Position=lower(get(F,position,<<>>)), Limit=to_int(get(F,limit,50)),
    P=[X || X <- soccer_data:players(), (Name=:=<<>> orelse contains(maps:get(name_key,X),Name)), (Nationality=:=<<>> orelse contains(lower(maps:get(nationality,X)),Nationality)), (Club=:=<<>> orelse contains(lower(maps:get(club,X)),Club)), (Position=:=<<>> orelse contains(lower(maps:get(position,X)),Position))],
    lists:sublist(lists:sort(fun(X,Y)->maps:get(overall,X)>=maps:get(overall,Y) end,P), max(0,Limit)).
standings(Competition, Season) ->
    Ms=find_matches(#{competition=>Competition, season=>Season}), T=lists:foldl(fun add_table/2,#{} ,Ms), lists:sort(fun(A,B)->{maps:get(points,A),maps:get(goal_difference,A),maps:get(goals_for,A)}>={maps:get(points,B),maps:get(goal_difference,B),maps:get(goals_for,B)} end,maps:values(T)).
add_table(M,T0) ->
    T1 = table_team(maps:get(home,M), maps:get(home_goals,M), maps:get(away_goals,M), T0),
    table_team(maps:get(away,M), maps:get(away_goals,M), maps:get(home_goals,M), T1).
table_team(Name, GF, GA, T) ->
    Old=maps:get(Name,T,#{team=>Name,matches=>0,wins=>0,draws=>0,losses=>0,goals_for=>0,goals_against=>0,points=>0}),
    Key=if GF>GA -> wins; GF=:=GA -> draws; true -> losses end,
    Points=if GF>GA -> 3; GF=:=GA -> 1; true -> 0 end,
    New=Old#{matches:=maps:get(matches,Old)+1,Key:=maps:get(Key,Old)+1,goals_for:=maps:get(goals_for,Old)+GF,goals_against:=maps:get(goals_against,Old)+GA,points:=maps:get(points,Old)+Points},
    maps:put(Name, New#{goal_difference=>maps:get(goals_for,New)-maps:get(goals_against,New)}, T).
biggest_wins(F) -> lists:sublist(lists:sort(fun(A,B)->abs(maps:get(home_goals,A)-maps:get(away_goals,A)) >= abs(maps:get(home_goals,B)-maps:get(away_goals,B)) end,find_matches(F)), to_int(get(F,limit,10))).
answer(#{intent := matches, filters := F}) -> find_matches(F); answer(#{intent := team_stats, filters := F}) -> team_stats(F); answer(#{intent := players, filters := F}) -> find_players(F); answer(#{intent := head_to_head, team_a := A, team_b := B}) -> head_to_head(A,B); answer(#{intent := standings, competition := C, season := S}) -> standings(C,S); answer(#{intent := biggest_wins, filters := F}) -> biggest_wins(F).
get(M,K,D)->maps:get(K,M,maps:get(atom_to_binary(K,utf8),M,D)). to_int(I) when is_integer(I)->I; to_int(B) when is_binary(B)->try binary_to_integer(B) catch _:_ -> 0 end; to_int(_)->0.
lower(B) when is_binary(B)-> Chars=case unicode:characters_to_list(B,utf8) of L when is_list(L)->L; {error,_,_}->unicode:characters_to_list(B,latin1) end, unicode:characters_to_binary(string:lowercase(Chars)); lower(A) when is_atom(A)->lower(atom_to_binary(A,utf8)); lower(_)-><<>>.
contains(A,B)->binary:match(A,B)=/=nomatch. rate(_,0)->0.0; rate(W,N)->W*100/N.
