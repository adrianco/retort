%% Context: pure query functions over the loaded match and player lists.
%% Team and competition filters match on name tokens, so "Corinthians" finds
%% "Sport Club Corinthians Paulista" and "Brasileirão" finds "Brasileirão Série A".
%% Filters are maps with optional keys: team, opponent, competition, stage, season,
%% from, to (YYYYMMDD), venue (home | away | any). Absent or undefined keys are ignored.
-module(soccer_stats).
-export([search/2, record/2, standings/3, league_summary/3, biggest_wins/3,
         search_players/2, club_summary/2]).

-spec search(list(), map()) -> [soccer_loader:match()].
search(Matches, Filter) ->
    Sorted = lists:sort(fun(A, B) -> maps:get(date, A) >= maps:get(date, B) end,
                        [M || {_, M} <- oriented(Matches, prepare(Filter))]),
    Sorted.

%% Win/draw/loss record from the perspective of the team filter.
-spec record(list(), map()) -> map().
record(Matches, Filter) ->
    Init = zero(),
    Sum = lists:foldl(fun({Side, M}, Acc) -> add(Acc, score(Side, M)) end,
                      Init, oriented(Matches, prepare(Filter))),
    Sum#{win_rate => percent(maps:get(wins, Sum), maps:get(played, Sum))}.

%% League table: 3 points for a win, 1 for a draw.
-spec standings(list(), integer() | undefined, binary()) -> [map()].
standings(Matches, Season, Competition) ->
    Filter = #{season => Season, competition => Competition},
    Table = lists:foldl(fun(M, Acc) ->
                                HG = maps:get(home_goals, M),
                                AG = maps:get(away_goals, M),
                                Acc1 = tally(maps:get(home, M), {HG, AG}, Acc),
                                tally(maps:get(away, M), {AG, HG}, Acc1)
                        end, #{}, [M || M <- Matches, pass_context(M, Filter)]),
    Rows = [S#{team => Name} || {Name, S} <- maps:to_list(Table)],
    lists:sort(fun(A, B) -> row_key(A) =< row_key(B) end, Rows).

row_key(#{points := P, wins := W, gf := GF, ga := GA, team := T}) ->
    {-P, -W, -(GF - GA), -GF, T}.

-spec league_summary(list(), integer() | undefined, binary() | undefined) -> map().
league_summary(Matches, Season, Competition) ->
    Filter = #{season => Season, competition => Competition},
    Ms = [M || M <- Matches, pass_context(M, Filter)],
    N = length(Ms),
    Goals = lists:sum([maps:get(home_goals, M) + maps:get(away_goals, M) || M <- Ms]),
    Outcomes = [outcome(maps:get(home_goals, M), maps:get(away_goals, M)) || M <- Ms],
    Count = fun(O) -> length([x || X <- Outcomes, X =:= O]) end,
    #{matches => N,
      goals_per_match => ratio(Goals, N),
      home_win_rate => percent(Count(win), N),
      draw_rate => percent(Count(draw), N),
      away_win_rate => percent(Count(loss), N)}.

-spec biggest_wins(list(), map(), pos_integer()) -> [soccer_loader:match()].
biggest_wins(Matches, Filter, Limit) ->
    Decisive = [M || M <- Matches, pass_context(M, Filter),
                     maps:get(home_goals, M) =/= maps:get(away_goals, M)],
    Sorted = lists:sort(fun(A, B) -> {margin(A), total(A)} >= {margin(B), total(B)} end, Decisive),
    lists:sublist(Sorted, Limit).

-spec search_players(list(), map()) -> [soccer_loader:player()].
search_players(Players, Filter) ->
    Q = Filter#{name => tokens_or_undef(maps:get(name, Filter, undefined)),
                club => tokens_or_undef(maps:get(club, Filter, undefined)),
                nationality => tokens_or_undef(maps:get(nationality, Filter, undefined))},
    Hits = [P || P <- Players, player_ok(P, Q)],
    lists:sort(fun(A, B) -> maps:get(overall, A) >= maps:get(overall, B) end, Hits).

%% Average overall per club for players of one nationality, largest squads first.
-spec club_summary(list(), binary()) -> [{binary(), pos_integer(), float()}].
club_summary(Players, Nationality) ->
    NatTokens = soccer_util:tokens(Nationality),
    Groups = lists:foldl(fun(P, Acc) ->
                                 case subset(NatTokens, maps:get(nationality_tokens, P)) of
                                     true ->
                                         Club = maps:get(club, P),
                                         maps:update_with(Club, fun(L) -> [maps:get(overall, P) | L] end,
                                                          [maps:get(overall, P)], Acc);
                                     false -> Acc
                                 end
                         end, #{}, Players),
    Rows = [{Club, length(Os), ratio(lists:sum(Os), length(Os))} || {Club, Os} <- maps:to_list(Groups)],
    lists:sort(fun({CA, NA, _}, {CB, NB, _}) -> {-NA, CA} =< {-NB, CB} end, Rows).

%% ---- filtering helpers ----

prepare(Filter) ->
    Filter#{team => tokens_or_undef(maps:get(team, Filter, undefined)),
            opponent => tokens_or_undef(maps:get(opponent, Filter, undefined))}.

tokens_or_undef(undefined) -> undefined;
tokens_or_undef(Bin) -> soccer_util:tokens(Bin).

%% Each match paired with the side ("home" or "away") that the team filter points at.
oriented(Matches, Filter) ->
    lists:filtermap(fun(M) ->
                            case pass_context(M, Filter) of
                                false -> false;
                                true ->
                                    case [S || S <- [home, away],
                                               venue_ok(S, Filter),
                                               name_ok(maps:get(team, Filter, undefined), side_tokens(M, S)),
                                               name_ok(maps:get(opponent, Filter, undefined), side_tokens(M, other(S)))] of
                                        [] -> false;
                                        [S | _] -> {true, {S, M}}
                                    end
                            end
                    end, Matches).

pass_context(M, Filter) ->
    opt(season, Filter, fun(S) -> S =:= maps:get(season, M) end) andalso
    opt(competition, Filter, fun(C) ->
                                     subset(soccer_util:tokens(C), soccer_util:tokens(maps:get(competition, M)))
                             end) andalso
    opt(stage, Filter, fun(St) ->
                               subset(soccer_util:tokens(St), soccer_util:tokens(maps:get(stage, M)))
                       end) andalso
    opt(from, Filter, fun(D) -> maps:get(date, M) >= D end) andalso
    opt(to, Filter, fun(D) -> maps:get(date, M) =< D end).

opt(Key, Filter, Pred) ->
    case maps:get(Key, Filter, undefined) of
        undefined -> true;
        V -> Pred(V)
    end.

venue_ok(Side, Filter) ->
    case maps:get(venue, Filter, any) of
        any -> true;
        undefined -> true;
        Venue -> Venue =:= Side
    end.

name_ok(undefined, _) -> true;
name_ok(Query, Tokens) -> subset(Query, Tokens).

side_tokens(M, home) -> maps:get(home_tokens, M);
side_tokens(M, away) -> maps:get(away_tokens, M).

other(home) -> away;
other(away) -> home.

subset(Query, Tokens) ->
    lists:all(fun(T) -> lists:member(T, Tokens) end, Query).

player_ok(P, Q) ->
    opt(name, Q, fun(N) -> name_ok(N, maps:get(name_tokens, P)) end) andalso
    opt(nationality, Q, fun(N) -> name_ok(N, maps:get(nationality_tokens, P)) end) andalso
    opt(club, Q, fun(C) -> name_ok(C, maps:get(club_tokens, P)) end) andalso
    opt(position, Q, fun(X) -> maps:get(position, P) =:= X end) andalso
    opt(min_overall, Q, fun(X) -> maps:get(overall, P) >= X end).

%% ---- result helpers ----

zero() ->
    #{played => 0, wins => 0, draws => 0, losses => 0, gf => 0, ga => 0, points => 0}.

score(home, M) -> {maps:get(home_goals, M), maps:get(away_goals, M)};
score(away, M) -> {maps:get(away_goals, M), maps:get(home_goals, M)}.

add(Acc, {GF, GA} = Score) ->
    Key = case outcome(GF, GA) of
              win -> wins;
              draw -> draws;
              loss -> losses
          end,
    Acc#{played => maps:get(played, Acc) + 1,
         gf => maps:get(gf, Acc) + GF,
         ga => maps:get(ga, Acc) + GA,
         Key => maps:get(Key, Acc) + 1,
         points => maps:get(points, Acc) + points(Score)}.

tally(Name, Score, Table) ->
    Current = maps:get(Name, Table, zero()),
    Table#{Name => add(Current, Score)}.

points({GF, GA}) when GF > GA -> 3;
points({GF, GA}) when GF =:= GA -> 1;
points(_) -> 0.

outcome(H, A) when H > A -> win;
outcome(H, A) when H =:= A -> draw;
outcome(_, _) -> loss.

margin(M) -> abs(maps:get(home_goals, M) - maps:get(away_goals, M)).
total(M) -> maps:get(home_goals, M) + maps:get(away_goals, M).

percent(_, 0) -> 0.0;
percent(N, D) -> round(N * 1000 / D) / 10.

ratio(_, 0) -> 0.0;
ratio(N, D) -> round(N * 100 / D) / 100.
