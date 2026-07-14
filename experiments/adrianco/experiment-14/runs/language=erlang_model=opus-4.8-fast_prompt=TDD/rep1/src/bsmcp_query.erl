%% @doc Query and aggregation functions over loaded matches and players.
-module(bsmcp_query).

-export([find_matches/2, head_to_head/3, team_record/3]).
-export([find_players/2, top_players/3]).
-export([standings/3, avg_goals/1, home_win_rate/1, biggest_wins/2]).

%% --- match search -----------------------------------------------------

%% @doc Filter matches by an options map. Supported keys:
%%   team        - involves team on either side
%%   home_team   - team played at home
%%   away_team   - team played away
%%   opponent    - combined with `team', restrict to head-to-head pairs
%%   season      - exact season (integer)
%%   competition - exact competition name (binary)
-spec find_matches([map()], map()) -> [map()].
find_matches(Matches, Opts) ->
    [M || M <- Matches, match_ok(M, Opts)].

match_ok(M, Opts) ->
    lists:all(fun(Pred) -> Pred(M) end, predicates(Opts)).

predicates(Opts) ->
    maps:fold(fun(K, V, Acc) -> [pred(K, V) | Acc] end, [], Opts).

pred(team, T) ->
    N = bsmcp_normalize:normalize(T),
    fun(M) -> involves(M, N) end;
pred(opponent, T) ->
    N = bsmcp_normalize:normalize(T),
    fun(M) -> involves(M, N) end;
pred(home_team, T) ->
    N = bsmcp_normalize:normalize(T),
    fun(M) -> maps:get(home_norm, M) =:= N end;
pred(away_team, T) ->
    N = bsmcp_normalize:normalize(T),
    fun(M) -> maps:get(away_norm, M) =:= N end;
pred(season, S) ->
    fun(M) -> maps:get(season, M) =:= S end;
pred(competition, C) ->
    fun(M) -> maps:get(competition, M) =:= C end;
pred(_, _) ->
    fun(_) -> true end.

involves(M, N) ->
    maps:get(home_norm, M) =:= N orelse maps:get(away_norm, M) =:= N.

%% --- head to head -----------------------------------------------------

%% @doc Matches between two teams plus a win/draw record from A's view.
-spec head_to_head([map()], binary(), binary()) -> {[map()], map()}.
head_to_head(Matches, TeamA, TeamB) ->
    NA = bsmcp_normalize:normalize(TeamA),
    NB = bsmcp_normalize:normalize(TeamB),
    Ms = [M || M <- Matches,
               pair(M, NA, NB)],
    Rec = lists:foldl(fun(M, Acc) -> tally_h2h(M, NA, Acc) end,
                      #{a_wins => 0, b_wins => 0, draws => 0}, Ms),
    {Ms, Rec}.

pair(M, NA, NB) ->
    H = maps:get(home_norm, M), A = maps:get(away_norm, M),
    (H =:= NA andalso A =:= NB) orelse (H =:= NB andalso A =:= NA).

tally_h2h(M, NA, Acc) ->
    case outcome_for(M, NA) of
        win  -> bump(a_wins, Acc);
        loss -> bump(b_wins, Acc);
        draw -> bump(draws, Acc);
        unknown -> Acc
    end.

%% --- team record ------------------------------------------------------

%% @doc Aggregate a team's record. Opts may include home_only, away_only,
%% season and competition (the latter two reuse find_matches filtering).
-spec team_record([map()], binary(), map()) -> map().
team_record(Matches, Team, Opts) ->
    N = bsmcp_normalize:normalize(Team),
    Filtered = find_matches(Matches, filter_opts(Team, Opts)),
    Relevant = [M || M <- Filtered, side_ok(M, N, Opts)],
    Init = #{matches => 0, wins => 0, draws => 0, losses => 0,
             goals_for => 0, goals_against => 0},
    Rec = lists:foldl(fun(M, Acc) -> tally_record(M, N, Acc) end, Init, Relevant),
    add_win_rate(Rec).

filter_opts(Team, Opts) ->
    Base = #{team => Team},
    maps:fold(fun(season, V, A) -> A#{season => V};
                 (competition, V, A) -> A#{competition => V};
                 (_, _, A) -> A
              end, Base, Opts).

side_ok(M, N, Opts) ->
    case {maps:get(home_only, Opts, false), maps:get(away_only, Opts, false)} of
        {true, _} -> maps:get(home_norm, M) =:= N;
        {_, true} -> maps:get(away_norm, M) =:= N;
        _ -> true
    end.

tally_record(M, N, Acc) ->
    case goals_for_against(M, N) of
        {GF, GA} when is_integer(GF), is_integer(GA) ->
            Acc1 = Acc#{matches => maps:get(matches, Acc) + 1,
                        goals_for => maps:get(goals_for, Acc) + GF,
                        goals_against => maps:get(goals_against, Acc) + GA},
            if GF > GA -> bump(wins, Acc1);
               GF < GA -> bump(losses, Acc1);
               true -> bump(draws, Acc1)
            end;
        _ ->
            %% Missing score: count the fixture but not the outcome.
            Acc#{matches => maps:get(matches, Acc) + 1}
    end.

goals_for_against(M, N) ->
    HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
    case maps:get(home_norm, M) =:= N of
        true -> {HG, AG};
        false -> {AG, HG}
    end.

outcome_for(M, N) ->
    case goals_for_against(M, N) of
        {GF, GA} when is_integer(GF), is_integer(GA) ->
            if GF > GA -> win; GF < GA -> loss; true -> draw end;
        _ -> unknown
    end.

add_win_rate(#{matches := 0} = Rec) -> Rec#{win_rate => 0.0};
add_win_rate(#{matches := T, wins := W} = Rec) ->
    Rec#{win_rate => round1(W * 100 / T)}.

round1(F) -> round(F * 10) / 10.

bump(K, Acc) -> Acc#{K => maps:get(K, Acc) + 1}.

%% --- player search ----------------------------------------------------

%% @doc Filter players by an options map, sorted by overall rating desc.
%% Keys: name (substring), nationality, club, position (all normalized),
%% min_overall (integer).
-spec find_players([map()], map()) -> [map()].
find_players(Players, Opts) ->
    Filtered = [P || P <- Players, player_ok(P, Opts)],
    lists:sort(fun(A, B) -> overall(A) >= overall(B) end, Filtered).

%% @doc Top-N players matching Opts.
-spec top_players([map()], map(), non_neg_integer()) -> [map()].
top_players(Players, Opts, N) ->
    take(N, find_players(Players, Opts)).

player_ok(P, Opts) ->
    maps:fold(fun(K, V, true) -> player_pred(K, V, P);
                 (_, _, false) -> false
              end, true, Opts).

player_pred(name, V, P) ->
    contains(maps:get(name_norm, P), bsmcp_normalize:normalize(V));
player_pred(nationality, V, P) ->
    maps:get(nationality_norm, P) =:= bsmcp_normalize:normalize(V);
player_pred(club, V, P) ->
    contains(maps:get(club_norm, P), bsmcp_normalize:normalize(V));
player_pred(position, V, P) ->
    maps:get(position, P) =:= V;
player_pred(min_overall, V, P) ->
    is_integer(overall(P)) andalso overall(P) >= V;
player_pred(_, _, _) ->
    true.

overall(P) -> maps:get(overall, P).

contains(Hay, Needle) ->
    Needle =/= <<>> andalso binary:match(Hay, Needle) =/= nomatch.

%% --- standings --------------------------------------------------------

%% @doc League table for a competition/season computed from match results.
%% 3 points per win, 1 per draw. Sorted by points, then goal difference,
%% then goals for, then name.
-spec standings([map()], binary(), integer()) -> [map()].
standings(Matches, Comp, Season) ->
    Ms = find_matches(Matches, #{competition => Comp, season => Season}),
    Table = lists:foldl(fun accumulate_standing/2, #{}, Ms),
    Rows = [finalize_standing(R) || R <- maps:values(Table)],
    lists:sort(fun standing_order/2, Rows).

accumulate_standing(M, Table) ->
    case {maps:get(home_goal, M), maps:get(away_goal, M)} of
        {HG, AG} when is_integer(HG), is_integer(AG) ->
            T1 = add_result(Table, maps:get(home_norm, M), maps:get(home, M), HG, AG),
            add_result(T1, maps:get(away_norm, M), maps:get(away, M), AG, HG);
        _ ->
            Table
    end.

%% Group by the precomputed normalized key, not the display name (which has
%% already had its state suffix stripped and would re-collide distinct clubs).
add_result(Table, Key, Team, GF, GA) ->
    Cur = maps:get(Key, Table,
                   #{team => Team, played => 0, wins => 0, draws => 0,
                     losses => 0, goals_for => 0, goals_against => 0}),
    Cur1 = Cur#{played => maps:get(played, Cur) + 1,
                goals_for => maps:get(goals_for, Cur) + GF,
                goals_against => maps:get(goals_against, Cur) + GA},
    Cur2 = if GF > GA -> bump(wins, Cur1);
              GF < GA -> bump(losses, Cur1);
              true -> bump(draws, Cur1)
           end,
    Table#{Key => Cur2}.

finalize_standing(R) ->
    Pts = maps:get(wins, R) * 3 + maps:get(draws, R),
    R#{points => Pts,
       goal_diff => maps:get(goals_for, R) - maps:get(goals_against, R)}.

standing_order(A, B) ->
    KA = {maps:get(points, A), maps:get(goal_diff, A), maps:get(goals_for, A)},
    KB = {maps:get(points, B), maps:get(goal_diff, B), maps:get(goals_for, B)},
    case {KA, KB} of
        {X, X} -> maps:get(team, A) =< maps:get(team, B);
        {X, Y} -> X > Y
    end.

%% --- statistics -------------------------------------------------------

%% @doc Average total goals per match (matches with known scores).
-spec avg_goals([map()]) -> float().
avg_goals(Matches) ->
    Scored = [M || M <- Matches, scored(M)],
    case Scored of
        [] -> 0.0;
        _ ->
            Total = lists:sum([maps:get(home_goal, M) + maps:get(away_goal, M)
                               || M <- Scored]),
            round2(Total / length(Scored))
    end.

%% @doc Percentage of matches won by the home team.
-spec home_win_rate([map()]) -> float().
home_win_rate(Matches) ->
    Scored = [M || M <- Matches, scored(M)],
    case Scored of
        [] -> 0.0;
        _ ->
            Wins = length([M || M <- Scored,
                                maps:get(home_goal, M) > maps:get(away_goal, M)]),
            round1(Wins * 100 / length(Scored))
    end.

%% @doc The N matches with the largest goal margin.
-spec biggest_wins([map()], non_neg_integer()) -> [map()].
biggest_wins(Matches, N) ->
    Scored = [M || M <- Matches, scored(M)],
    Sorted = lists:sort(fun(A, B) -> margin(A) >= margin(B) end, Scored),
    take(N, Sorted).

scored(M) ->
    is_integer(maps:get(home_goal, M)) andalso is_integer(maps:get(away_goal, M)).

margin(M) ->
    abs(maps:get(home_goal, M) - maps:get(away_goal, M)).

round2(F) -> round(F * 100) / 100.

take(N, _) when N =< 0 -> [];
take(_, []) -> [];
take(N, [H | T]) -> [H | take(N - 1, T)].
