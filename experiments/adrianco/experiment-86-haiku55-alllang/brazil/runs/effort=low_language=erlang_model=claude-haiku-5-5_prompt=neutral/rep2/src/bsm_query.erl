%% @doc Pure query and statistics functions over loaded matches and players.
%% Filters are maps with atom keys; every key is optional:
%%   team / opponent :: bsm_team:team()   competition :: binary() (substring)
%%   season :: integer()                  date_from / date_to :: ISO binary
%%   venue :: home | away | any           (applies to `team' only)
-module(bsm_query).
-export([find_matches/2, team_record/3, head_to_head/4, standings/2,
         league_stats/2, search_players/2, find_teams/2]).
-include("bsm.hrl").

%% @doc Matches passing the filters, newest first.
find_matches(Matches, F) ->
    Found = [M || M <- Matches, pass(M, F)],
    lists:sort(fun(A, B) -> maps:get(date, A) >= maps:get(date, B) end, Found).

team_record(Matches, Team, F) ->
    Ms = find_matches(Matches, F#{team => Team}),
    Tally = lists:foldl(fun(M, Acc) -> tally(M, Team, Acc) end, new_tally(), Ms),
    summarise(maps:get(name, Team), Tally).

head_to_head(Matches, A, B, F) ->
    Ms = find_matches(Matches, F#{team => A, opponent => B}),
    Start = #{team_a_wins => 0, draws => 0, team_b_wins => 0, team_a_goals => 0, team_b_goals => 0},
    T = lists:foldl(fun(M, Acc) -> h2h_tally(M, A, Acc) end, Start, Ms),
    T#{team_a => maps:get(name, A), team_b => maps:get(name, B),
       total => length(Ms), recent => Ms}.

%% Brasileirão Série A table for one season. Points 3/1/0; ties broken by
%% wins, goal difference, goals scored, then name.
standings(Matches, Season) ->
    Ms = [M || M <- Matches, maps:get(competition, M) =:= ?SERIE_A,
               maps:get(season, M) =:= Season],
    Table = lists:foldl(fun standing_update/2, #{}, Ms),
    Rows = lists:sort(fun cmp_row/2, maps:values(Table)),
    [R#{position => I} || {I, R} <- lists:zip(lists:seq(1, length(Rows)), Rows)].

league_stats(Matches, F) ->
    Ms = find_matches(Matches, F),
    N = length(Ms),
    Goals = lists:sum([maps:get(home_goals, M) + maps:get(away_goals, M) || M <- Ms]),
    Home = length([M || M <- Ms, outcome(M) =:= home]),
    Draws = length([M || M <- Ms, outcome(M) =:= draw]),
    Away = length([M || M <- Ms, outcome(M) =:= away]),
    Wins = lists:sort(fun(A, B) ->
                              margin(A) > margin(B)
                                  orelse (margin(A) =:= margin(B)
                                          andalso maps:get(date, A) >= maps:get(date, B))
                      end, [M || M <- Ms, margin(M) > 0]),
    #{matches => N,
      average_goals_per_match => avg(Goals, N),
      home_win_pct => pct(Home, N),
      draw_pct => pct(Draws, N),
      away_win_pct => pct(Away, N),
      biggest_wins => lists:sublist(Wins, 5)}.

search_players(Players, F) ->
    Ps = [P || P <- Players, player_ok(P, F)],
    lists:sort(fun(A, B) ->
                       {-maps:get(overall, A), maps:get(name, A)}
                           =< {-maps:get(overall, B), maps:get(name, B)}
               end, Ps).

%% Distinct teams whose name contains Query (all teams when Query is empty).
find_teams(Matches, Query) ->
    Teams = lists:foldl(fun(M, Acc) ->
                                add_team(maps:get(home, M), add_team(maps:get(away, M), Acc))
                        end, #{}, Matches),
    Hits = [T || T <- maps:values(Teams), bsm_text:contains(maps:get(name, T), Query)],
    lists:sort(fun(A, B) -> maps:get(name, A) =< maps:get(name, B) end, Hits).

%% --- match filtering -------------------------------------------------------

pass(M, F) ->
    competition_ok(M, maps:get(competition, F, <<>>))
        andalso season_ok(M, maps:get(season, F, undefined))
        andalso date_ok(M, maps:get(date_from, F, <<>>), maps:get(date_to, F, <<>>))
        andalso teams_ok(M, F).

competition_ok(M, Q) -> bsm_text:contains(maps:get(competition, M), Q).

season_ok(_M, undefined) -> true;
season_ok(M, S) -> maps:get(season, M) =:= S.

date_ok(M, From, To) ->
    D = maps:get(date, M),
    (From =:= <<>> orelse D >= From) andalso (To =:= <<>> orelse D =< To).

teams_ok(M, F) ->
    Venue = maps:get(venue, F, any),
    case {maps:get(team, F, none), maps:get(opponent, F, none)} of
        {none, none} -> true;
        {T, none} -> side(M, T, Venue) =/= none;
        {none, O} -> side(M, O, Venue) =/= none;
        {T, O} -> pair(M, T, O)
    end.

pair(#{home := H, away := A}, T, O) ->
    (bsm_team:same(H, T) andalso bsm_team:same(A, O))
        orelse (bsm_team:same(H, O) andalso bsm_team:same(A, T)).

%% Which side `Team' played on, honouring the venue restriction.
side(#{home := H, away := A}, Team, Venue) ->
    IsHome = Venue =/= away andalso bsm_team:same(H, Team),
    IsAway = Venue =/= home andalso bsm_team:same(A, Team),
    if IsHome -> home;
       IsAway -> away;
       true -> none
    end.

outcome(#{home_goals := H, away_goals := A}) when H > A -> home;
outcome(#{home_goals := H, away_goals := A}) when H < A -> away;
outcome(_) -> draw.

margin(#{home_goals := H, away_goals := A}) -> abs(H - A).

%% --- team records ----------------------------------------------------------

new_tally() ->
    #{played => 0, won => 0, drawn => 0, lost => 0, goals_for => 0, goals_against => 0}.

tally(M, Team, Acc) ->
    {GF, GA} = case side(M, Team, any) of
                   home -> {maps:get(home_goals, M), maps:get(away_goals, M)};
                   away -> {maps:get(away_goals, M), maps:get(home_goals, M)}
               end,
    Result = if GF > GA -> won; GF =:= GA -> drawn; true -> lost end,
    Acc1 = maps:update_with(played, fun(N) -> N + 1 end, Acc),
    Acc2 = maps:update_with(goals_for, fun(N) -> N + GF end, Acc1),
    Acc3 = maps:update_with(goals_against, fun(N) -> N + GA end, Acc2),
    maps:update_with(Result, fun(N) -> N + 1 end, Acc3).

summarise(Name, #{played := P, won := W, drawn := D, lost := L,
                  goals_for := GF, goals_against := GA}) ->
    #{team => Name, matches => P, wins => W, draws => D, losses => L,
      goals_for => GF, goals_against => GA, goal_difference => GF - GA,
      win_rate_pct => pct(W, P)}.

h2h_tally(M, A, Acc) ->
    {AG, BG} = case side(M, A, any) of
                   home -> {maps:get(home_goals, M), maps:get(away_goals, M)};
                   away -> {maps:get(away_goals, M), maps:get(home_goals, M)}
               end,
    Key = if AG > BG -> team_a_wins; AG =:= BG -> draws; true -> team_b_wins end,
    Acc1 = maps:update_with(Key, fun(N) -> N + 1 end, Acc),
    Acc2 = maps:update_with(team_a_goals, fun(N) -> N + AG end, Acc1),
    maps:update_with(team_b_goals, fun(N) -> N + BG end, Acc2).

%% --- standings -------------------------------------------------------------

standing_update(M, Table) ->
    H = maps:get(home, M),
    A = maps:get(away, M),
    HG = maps:get(home_goals, M),
    AG = maps:get(away_goals, M),
    add_result(A, AG, HG, add_result(H, HG, AG, Table)).

add_result(Team, GF, GA, Table) ->
    K = bsm_team:key(Team),
    Row = maps:get(K, Table, #{team => maps:get(name, Team), played => 0, won => 0, drawn => 0,
                               lost => 0, goals_for => 0, goals_against => 0, points => 0}),
    Row1 = Row#{played => maps:get(played, Row) + 1,
                goals_for => maps:get(goals_for, Row) + GF,
                goals_against => maps:get(goals_against, Row) + GA},
    Row2 = if GF > GA -> Row1#{won => maps:get(won, Row1) + 1,
                               points => maps:get(points, Row1) + 3};
              GF =:= GA -> Row1#{drawn => maps:get(drawn, Row1) + 1,
                                 points => maps:get(points, Row1) + 1};
              true -> Row1#{lost => maps:get(lost, Row1) + 1}
           end,
    Table#{K => Row2}.

cmp_row(A, B) ->
    {-maps:get(points, A), -maps:get(won, A), -gd(A), -maps:get(goals_for, A), maps:get(team, A)}
        =< {-maps:get(points, B), -maps:get(won, B), -gd(B), -maps:get(goals_for, B), maps:get(team, B)}.

gd(R) -> maps:get(goals_for, R) - maps:get(goals_against, R).

%% --- players ---------------------------------------------------------------

player_ok(P, F) ->
    bsm_text:contains(maps:get(name, P), maps:get(name, F, <<>>))
        andalso bsm_text:contains(maps:get(club, P), maps:get(club, F, <<>>))
        andalso same_text(maps:get(nationality, P), maps:get(nationality, F, <<>>))
        andalso same_text(maps:get(position, P), maps:get(position, F, <<>>))
        andalso maps:get(overall, P) >= maps:get(min_overall, F, 0).

same_text(_Field, <<>>) -> true;
same_text(Field, Q) -> bsm_text:fold(Field) =:= bsm_text:fold(Q).

add_team(#{name := _} = T, Acc) -> Acc#{bsm_team:key(T) => T};
add_team(_, Acc) -> Acc.

%% --- helpers ---------------------------------------------------------------

avg(_Total, 0) -> 0.0;
avg(Total, N) -> ratio(Total, N, 100) / 100.

pct(_N, 0) -> 0.0;
pct(N, D) -> ratio(N, D, 1000) / 10.

ratio(N, D, Scale) -> round(N * Scale / D).
