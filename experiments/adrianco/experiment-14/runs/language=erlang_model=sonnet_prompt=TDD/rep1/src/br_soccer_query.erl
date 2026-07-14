-module(br_soccer_query).
-export([filter_by_team/2, filter_by_season/2, head_to_head/3,
         team_stats/2, search_players/2, compute_standings/1,
         biggest_matches/2, avg_goals/1,
         team_name_matches/2]).

%% Check if a team field matches the query name (normalized, case-insensitive).
team_name_matches(FieldVal, QueryName) ->
    Normalized = br_soccer_csv:normalize_team(FieldVal),
    QNorm = string:lowercase(QueryName),
    NNorm = string:lowercase(Normalized),
    %% Check substring match
    binary:match(NNorm, QNorm) =/= nomatch.

match_has_team(Match, Team) ->
    Home = maps:get(<<"home_team">>, Match, maps:get(<<"home">>, Match, <<>>)),
    Away = maps:get(<<"away_team">>, Match, maps:get(<<"away">>, Match, <<>>)),
    team_name_matches(Home, Team) orelse team_name_matches(Away, Team).

filter_by_team(Matches, Team) ->
    [M || M <- Matches, match_has_team(M, Team)].

filter_by_season(Matches, Season) ->
    [M || M <- Matches, match_season(M, Season)].

match_season(M, Season) ->
    case maps:get(<<"season">>, M, undefined) of
        undefined ->
            %% Fallback: extract year from date/datetime field
            Date = maps:get(<<"date">>, M,
                   maps:get(<<"datetime">>, M, <<>>)),
            year_from_date(Date) =:= Season;
        S -> S =:= Season
    end.

year_from_date(<<Y:4/binary, _/binary>>) -> Y;
year_from_date(_) -> <<>>.

head_to_head(Matches, T1, T2) ->
    [M || M <- Matches,
          begin
              Home = maps:get(<<"home_team">>, M, maps:get(<<"home">>, M, <<>>)),
              Away = maps:get(<<"away_team">>, M, maps:get(<<"away">>, M, <<>>)),
              (team_name_matches(Home, T1) andalso team_name_matches(Away, T2))
              orelse
              (team_name_matches(Home, T2) andalso team_name_matches(Away, T1))
          end].

team_stats(Matches, Team) ->
    Filtered = filter_by_team(Matches, Team),
    lists:foldl(fun(M, Acc) ->
        Home = maps:get(<<"home_team">>, M, maps:get(<<"home">>, M, <<>>)),
        IsHome = team_name_matches(Home, Team),
        {HG, AG} = parse_goals(M),
        {TF, TC} = if IsHome -> {HG, AG}; true -> {AG, HG} end,
        Result = if TF > TC -> win; TF =:= TC -> draw; true -> loss end,
        Acc#{matches => maps:get(matches, Acc) + 1,
             wins    => maps:get(wins, Acc)    + (if Result =:= win  -> 1; true -> 0 end),
             draws   => maps:get(draws, Acc)   + (if Result =:= draw -> 1; true -> 0 end),
             losses  => maps:get(losses, Acc)  + (if Result =:= loss -> 1; true -> 0 end),
             goals_for     => maps:get(goals_for, Acc)     + TF,
             goals_against => maps:get(goals_against, Acc) + TC}
    end, #{matches => 0, wins => 0, draws => 0, losses => 0,
           goals_for => 0, goals_against => 0}, Filtered).

parse_goals(M) ->
    HG = to_int(maps:get(<<"home_goal">>, M, <<"0">>)),
    AG = to_int(maps:get(<<"away_goal">>, M, <<"0">>)),
    {HG, AG}.

to_int(B) when is_binary(B) ->
    try binary_to_integer(string:trim(B))
    catch _:_ -> 0
    end;
to_int(N) when is_integer(N) -> N;
to_int(_) -> 0.

search_players(Players, Filters) ->
    lists:filter(fun(P) -> player_matches(P, Filters) end, Players).

player_matches(P, Filters) ->
    maps:fold(fun(Key, Val, Acc) ->
        Acc andalso player_field_matches(P, Key, Val)
    end, true, Filters).

player_field_matches(P, name, Val) ->
    Name = maps:get(<<"Name">>, P, <<>>),
    binary:match(string:lowercase(Name), string:lowercase(Val)) =/= nomatch;
player_field_matches(P, nationality, Val) ->
    Nat = maps:get(<<"Nationality">>, P, <<>>),
    binary:match(string:lowercase(Nat), string:lowercase(Val)) =/= nomatch;
player_field_matches(P, club, Val) ->
    Club = maps:get(<<"Club">>, P, <<>>),
    binary:match(string:lowercase(Club), string:lowercase(Val)) =/= nomatch;
player_field_matches(P, position, Val) ->
    Pos = maps:get(<<"Position">>, P, <<>>),
    string:lowercase(Pos) =:= string:lowercase(Val);
player_field_matches(P, min_overall, Val) ->
    Overall = to_int(maps:get(<<"Overall">>, P, <<"0">>)),
    MinVal = if is_binary(Val) -> to_int(Val); true -> Val end,
    Overall >= MinVal;
player_field_matches(_P, _Key, _Val) -> true.

compute_standings(Matches) ->
    Table = lists:foldl(fun(M, Acc) ->
        %% Use raw team names to keep e.g. "Atletico-MG" and "Atletico-PR" separate.
        Home = maps:get(<<"home_team">>, M,
               maps:get(<<"home">>, M,
               maps:get(<<"Equipe_mandante">>, M, <<>>))),
        Away = maps:get(<<"away_team">>, M,
               maps:get(<<"away">>, M,
               maps:get(<<"Equipe_visitante">>, M, <<>>))),
        {HG, AG} = parse_goals(M),
        {HW, HD, HL, AW, AD, AL} =
            if HG > AG  -> {1,0,0, 0,0,1};
               HG =:= AG -> {0,1,0, 0,1,0};
               true       -> {0,0,1, 1,0,0}
            end,
        Acc1 = update_standing(Acc, Home, HW, HD, HL, HG, AG),
        update_standing(Acc1, Away, AW, AD, AL, AG, HG)
    end, #{}, Matches),
    Sorted = lists:sort(fun({_, A}, {_, B}) ->
        maps:get(points, A) > maps:get(points, B)
    end, maps:to_list(Table)),
    Sorted.

update_standing(Table, Team, W, D, L, GF, GA) ->
    Old = maps:get(Team, Table, #{points => 0, wins => 0, draws => 0,
                                   losses => 0, gf => 0, ga => 0}),
    Pts = maps:get(points, Old) + W*3 + D,
    maps:put(Team, Old#{points => Pts,
                        wins   => maps:get(wins, Old) + W,
                        draws  => maps:get(draws, Old) + D,
                        losses => maps:get(losses, Old) + L,
                        gf     => maps:get(gf, Old) + GF,
                        ga     => maps:get(ga, Old) + GA},
             Table).

biggest_matches(Matches, N) ->
    Annotated = lists:map(fun(M) ->
        Home = br_soccer_csv:normalize_team(
                 maps:get(<<"home_team">>, M, maps:get(<<"home">>, M, <<>>))),
        Away = br_soccer_csv:normalize_team(
                 maps:get(<<"away_team">>, M, maps:get(<<"away">>, M, <<>>))),
        {HG, AG} = parse_goals(M),
        Date = maps:get(<<"datetime">>, M,
               maps:get(<<"date">>, M, <<>>)),
        {abs(HG - AG), Date, Home, Away, HG, AG}
    end, Matches),
    Sorted = lists:sort(fun({D1,_,_,_,_,_}, {D2,_,_,_,_,_}) -> D1 > D2 end, Annotated),
    Top = lists:sublist(Sorted, N),
    [{Date, Home, Away, HG, AG} || {_Diff, Date, Home, Away, HG, AG} <- Top].

avg_goals(Matches) ->
    case length(Matches) of
        0 -> 0.0;
        Len ->
            Total = lists:sum([begin {HG, AG} = parse_goals(M), HG + AG end
                               || M <- Matches]),
            Total / Len
    end.
