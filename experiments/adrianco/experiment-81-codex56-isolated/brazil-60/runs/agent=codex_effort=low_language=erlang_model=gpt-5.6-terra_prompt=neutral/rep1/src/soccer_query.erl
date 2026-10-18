-module(soccer_query).
-export([find_matches/2, team_stats/2, head_to_head/3, standings/3, search_players/2, aggregate/2, answer/2]).

find_matches(Data, Filters) ->
    Limit = maps:get(limit, Filters, 100),
    Found = [M || M <- soccer_data:matches(Data), match_filters(M, Filters)],
    lists:sublist(lists:sort(fun(A,B) -> maps:get(date_sort,A) >= maps:get(date_sort,B) end, Found), Limit).

match_filters(M, F) ->
    Team = norm_opt(maps:get(team, F, undefined)), Home = norm_opt(maps:get(home_team, F, undefined)), Away = norm_opt(maps:get(away_team, F, undefined)),
    TeamOK = Team =:= undefined orelse maps:get(home_normalized,M) =:= Team orelse maps:get(away_normalized,M) =:= Team,
    HomeOK = Home =:= undefined orelse maps:get(home_normalized,M) =:= Home,
    AwayOK = Away =:= undefined orelse maps:get(away_normalized,M) =:= Away,
    SeasonOK = not maps:is_key(season,F) orelse maps:get(season,M) =:= to_int(maps:get(season,F)),
    CompOK = not maps:is_key(competition,F) orelse contains(maps:get(competition,M), maps:get(competition,F)),
    Date = maps:get(date_sort,M), FromOK = not maps:is_key(from,F) orelse Date >= soccer_data:parse_date(to_bin(maps:get(from,F))),
    ToOK = not maps:is_key(to,F) orelse Date =< soccer_data:parse_date(to_bin(maps:get(to,F))),
    TeamOK andalso HomeOK andalso AwayOK andalso SeasonOK andalso CompOK andalso FromOK andalso ToOK.

team_stats(Data, Filters) ->
    Team = norm_opt(maps:get(team, Filters)), Scope = case maps:get(venue, Filters, any) of <<"home">> -> home; "home" -> home; home -> home; _ -> any end,
    Ms = find_matches(Data, maps:put(limit, 100000, Filters)),
    S = lists:foldl(fun(M, A) -> update_stats(M, Team, Scope, A) end, #{team => to_bin(maps:get(team, Filters)), matches => 0,wins=>0,draws=>0,losses=>0,goals_for=>0,goals_against=>0}, Ms),
    N = maps:get(matches,S), S#{win_rate => case N of 0 -> 0.0; _ -> maps:get(wins,S) * 100 / N end}.
update_stats(M, Team, Scope, A) ->
    IsHome = maps:get(home_normalized,M) =:= Team,
    case (IsHome orelse maps:get(away_normalized,M) =:= Team) andalso (Scope =:= any orelse IsHome) of
        false -> A;
        true -> GF = if IsHome -> maps:get(home_goals,M); true -> maps:get(away_goals,M) end,
                GA = if IsHome -> maps:get(away_goals,M); true -> maps:get(home_goals,M) end,
                Result = if GF > GA -> wins; GF =:= GA -> draws; true -> losses end,
                A#{matches := maps:get(matches,A)+1, Result := maps:get(Result,A)+1, goals_for := maps:get(goals_for,A)+GF, goals_against := maps:get(goals_against,A)+GA}
    end.

head_to_head(Data, TeamA, TeamB) ->
    A = norm_opt(TeamA), B = norm_opt(TeamB), Ms = find_matches(Data, #{limit => 100000}),
    Pair = [M || M <- Ms, (maps:get(home_normalized,M) =:= A andalso maps:get(away_normalized,M) =:= B) orelse (maps:get(home_normalized,M) =:= B andalso maps:get(away_normalized,M) =:= A)],
    Base = #{team_a=>to_bin(TeamA),team_b=>to_bin(TeamB),matches=>length(Pair),team_a_wins=>0,team_b_wins=>0,draws=>0,matches_list=>Pair},
    lists:foldl(fun(M,X) -> H=maps:get(home_normalized,M), HG=maps:get(home_goals,M), AG=maps:get(away_goals,M), K=if HG=:=AG -> draws; (HG>AG andalso H=:=A) orelse (HG<AG andalso H=:=B) -> team_a_wins; true -> team_b_wins end, X#{K := maps:get(K,X)+1} end, Base, Pair).

standings(Data, Competition, Season) ->
    Ms = find_matches(Data, #{competition=>Competition,season=>Season,limit=>100000}),
    Table = lists:foldl(fun add_table/2, #{}, Ms),
    Ranked = maps:values(Table), lists:sort(fun(A,B) -> {maps:get(points,A),maps:get(goal_difference,A),maps:get(goals_for,A)} >= {maps:get(points,B),maps:get(goal_difference,B),maps:get(goals_for,B)} end, Ranked).
add_table(M, T) -> add_side(maps:get(away,M), maps:get(away_goals,M), maps:get(home_goals,M), add_side(maps:get(home,M), maps:get(home_goals,M), maps:get(away_goals,M), T)).
add_side(Name, GF, GA, T) ->
    Old = maps:get(Name,T,#{team=>Name,played=>0,wins=>0,draws=>0,losses=>0,goals_for=>0,goals_against=>0,points=>0,goal_difference=>0}),
    K=if GF>GA->wins; GF=:=GA->draws; true->losses end, P=if GF>GA->3; GF=:=GA->1; true->0 end,
    New=Old#{played:=maps:get(played,Old)+1,K:=maps:get(K,Old)+1,goals_for:=maps:get(goals_for,Old)+GF,goals_against:=maps:get(goals_against,Old)+GA,points:=maps:get(points,Old)+P}, maps:put(Name,New#{goal_difference:=maps:get(goals_for,New)-maps:get(goals_against,New)},T).

search_players(Data, Filters) ->
    P0 = [P || P <- soccer_data:players(Data), player_ok(P, Filters)],
    lists:sublist(lists:sort(fun(A,B)->maps:get(overall,A)>=maps:get(overall,B) end,P0),maps:get(limit,Filters,100)).
player_ok(P,F) -> field_ok(maps:get(name,F,undefined),maps:get(name,P)) andalso field_ok(maps:get(nationality,F,undefined),maps:get(nationality,P)) andalso field_ok(maps:get(club,F,undefined),maps:get(club,P)) andalso field_ok(maps:get(position,F,undefined),maps:get(position,P)).
field_ok(undefined,_) -> true; field_ok(V,F) -> contains(F,V).
aggregate(Data, Filters) ->
    Ms=find_matches(Data,maps:put(limit,100000,Filters)), N=length(Ms), Goals=lists:sum([maps:get(home_goals,M)+maps:get(away_goals,M)||M<-Ms]), HW=length([ok||M<-Ms,maps:get(home_goals,M)>maps:get(away_goals,M)]),
    #{matches=>N,total_goals=>Goals,goals_per_match=>case N of 0->0.0;_->Goals/N end,home_win_rate=>case N of 0->0.0;_->HW*100/N end}.

answer(Data, Q) ->
    L=string:lowercase(unicode:characters_to_list(Q)),
    case re:run(L,"(?:compare|vs|versus)\\s+(.+?)\\s+(?:and|vs|versus)\\s+(.+)$",[{capture,[1,2],list}]) of
      {match,[A,B]} -> head_to_head(Data,A,B);
      nomatch -> #{message => <<"Use the structured MCP tools (search_matches, team_stats, head_to_head, standings, search_players, aggregate_stats).">>}
    end.

norm_opt(undefined)->undefined; norm_opt(V)->soccer_data:normalize_team(to_bin(V)).
to_bin(V) when is_binary(V)->V; to_bin(V) when is_list(V)->unicode:characters_to_binary(V); to_bin(V) when is_integer(V)->integer_to_binary(V).
to_int(V) when is_integer(V)->V; to_int(V)->binary_to_integer(to_bin(V)).
contains(A,B) -> binary:match(lower(A),lower(B))=/=nomatch.
lower(V) -> B=to_bin(V), << <<(if C >= $A, C =< $Z -> C + 32; true -> C end)>> || <<C>> <= B >>.
