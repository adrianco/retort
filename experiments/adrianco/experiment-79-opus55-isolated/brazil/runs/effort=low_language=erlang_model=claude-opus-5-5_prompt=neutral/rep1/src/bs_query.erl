%% Query and aggregation functions over the loaded data.
%% Teams are passed as canonical keys (see bs_team:resolve/1).
-module(bs_query).
-export([matches/1, played/1, record/2, record/3, head_to_head/3, standings/1,
         league_stats/1, biggest_wins/2, rankings/4, team_competitions/1,
         derbies/1, players/1, position_group/1, parse_competition/1, parse_stage/1]).

%% Opts: team, opponent, venue (home|away|either), competition, season,
%%       date_from, date_to, stage, round, source, include_duplicates
%% Result is sorted newest first.
matches(Opts) ->
    Ms = case maps:get(include_duplicates, Opts, false) of
             true -> bs_data:all_matches();
             false -> bs_data:matches()
         end,
    lists:sort(fun(A, B) -> sort_key(A) >= sort_key(B) end,
               [M || M <- Ms, keep(M, Opts)]).

sort_key(#{date := undefined, season := S}) when is_integer(S) -> {{S, 0, 0}, 0};
sort_key(#{date := undefined}) -> {{0, 0, 0}, 0};
sort_key(#{date := D, round := R}) -> {D, R}.

played(Ms) -> [M || #{hg := H, ag := A} = M <- Ms, is_integer(H), is_integer(A)].

keep(#{home := H, away := A} = M, O) ->
    T = opt(team, O), Opp = opt(opponent, O),
    team_ok(T, maps:get(venue, O, either), H, A)
        andalso opp_ok(T, Opp, H, A)
        andalso eq(opt(competition, O), maps:get(comp, M))
        andalso eq(opt(season, O), maps:get(season, M))
        andalso eq(opt(round, O), maps:get(round, M))
        andalso eq(opt(stage, O), maps:get(stage, M))
        andalso eq(opt(source, O), maps:get(source, M))
        andalso date_ok(opt(date_from, O), opt(date_to, O), maps:get(date, M)).

opt(K, O) -> maps:get(K, O, undefined).

eq(undefined, _) -> true;
eq(X, Y) -> X =:= Y.

team_ok(undefined, _, _, _) -> true;
team_ok(T, home, H, _) -> H =:= T;
team_ok(T, away, _, A) -> A =:= T;
team_ok(T, _, H, A) -> H =:= T orelse A =:= T.

opp_ok(_, undefined, _, _) -> true;
opp_ok(undefined, O, H, A) -> H =:= O orelse A =:= O;
opp_ok(T, O, H, A) -> (H =:= T andalso A =:= O) orelse (H =:= O andalso A =:= T).

date_ok(undefined, undefined, _) -> true;
date_ok(_, _, undefined) -> false;
date_ok(From, To, D) ->
    (From =:= undefined orelse D >= From) andalso (To =:= undefined orelse D =< To).

%% Win/draw/loss record of Team over the given matches.
record(Team, Ms) -> record(Team, Ms, either).

record(Team, Ms, Venue) ->
    lists:foldl(
      fun(#{home := H, away := A, hg := Hg, ag := Ag}, Acc) ->
              if H =:= Team, Venue =/= away -> add(Acc, Hg, Ag);
                 A =:= Team, Venue =/= home -> add(Acc, Ag, Hg);
                 true -> Acc
              end
      end, zero(), played(Ms)).

zero() -> #{matches => 0, wins => 0, draws => 0, losses => 0, gf => 0, ga => 0, points => 0}.

add(#{matches := P, wins := W, draws := D, losses := L, gf := F, ga := A, points := Pts}, Gf, Ga) ->
    {W1, D1, L1, P1} = if Gf > Ga -> {W + 1, D, L, Pts + 3};
                          Gf =:= Ga -> {W, D + 1, L, Pts + 1};
                          true -> {W, D, L + 1, Pts}
                       end,
    #{matches => P + 1, wins => W1, draws => D1, losses => L1, gf => F + Gf, ga => A + Ga,
      points => P1}.

%% -> #{matches => [Match], a => Record, b => Record}
head_to_head(A, B, Opts) ->
    Ms = matches(Opts#{team => A, opponent => B}),
    #{matches => Ms, a => record(A, Ms), b => record(B, Ms)}.

%% League table from match results: 3 points per win; ties broken by wins,
%% goal difference, goals scored. -> [{TeamKey, Record}]
standings(Ms) -> table(Ms, either).

table(Ms, Venue) ->
    Tab = lists:foldl(
            fun(#{home := H, away := A, hg := Hg, ag := Ag}, Acc) ->
                    Acc1 = case Venue of
                               away -> Acc;
                               _ -> maps:put(H, add(maps:get(H, Acc, zero()), Hg, Ag), Acc)
                           end,
                    case Venue of
                        home -> Acc1;
                        _ -> maps:put(A, add(maps:get(A, Acc1, zero()), Ag, Hg), Acc1)
                    end
            end, #{}, played(Ms)),
    lists:sort(fun({_, X}, {_, Y}) -> rank(X) >= rank(Y) end, maps:to_list(Tab)).

rank(#{points := P, wins := W, gf := F, ga := A}) -> {P, W, F - A, F}.

league_stats(Ms) ->
    P = played(Ms),
    N = length(P),
    {G, HW, D, AW} =
        lists:foldl(fun(#{hg := H, ag := A}, {G0, HW0, D0, AW0}) ->
                            if H > A -> {G0 + H + A, HW0 + 1, D0, AW0};
                               H =:= A -> {G0 + H + A, HW0, D0 + 1, AW0};
                               true -> {G0 + H + A, HW0, D0, AW0 + 1}
                            end
                    end, {0, 0, 0, 0}, P),
    #{matches => N, goals => G, home_wins => HW, draws => D, away_wins => AW,
      avg_goals => ratio(G, N), home_win_rate => ratio(100 * HW, N),
      draw_rate => ratio(100 * D, N), away_win_rate => ratio(100 * AW, N)}.

ratio(_, 0) -> 0.0;
ratio(A, B) -> A / B.

biggest_wins(Ms, Limit) ->
    Sorted = lists:sort(
               fun(#{hg := H1, ag := A1} = X, #{hg := H2, ag := A2} = Y) ->
                       {abs(H1 - A1), H1 + A1, sort_key(X)} >= {abs(H2 - A2), H2 + A2, sort_key(Y)}
               end, played(Ms)),
    lists:sublist(Sorted, Limit).

%% Metric: win_rate | goals_for | goals_against | wins | points
rankings(Ms, Venue, Metric, MinMatches) ->
    Rows = [R || {_, #{matches := N}} = R <- table(Ms, Venue), N >= MinMatches],
    Score = fun(#{matches := N, wins := W, points := P, gf := F, ga := A}) ->
                    case Metric of
                        win_rate -> {W / N, P / N, N};
                        goals_for -> {F, -N, 0};
                        goals_against -> {-(A / N), N, 0};
                        wins -> {W, -N, 0};
                        points -> {P, F - A, F}
                    end
            end,
    lists:sort(fun({_, X}, {_, Y}) -> Score(X) >= Score(Y) end, Rows).

%% -> [{Comp, [Season], Record}]
team_competitions(Team) ->
    Ms = matches(#{team => Team}),
    Comps = lists:usort([C || #{comp := C} <- Ms]),
    [begin
         CMs = [M || #{comp := C0} = M <- Ms, C0 =:= C],
         {C, lists:usort([S || #{season := S} <- CMs, S =/= undefined]), record(Team, CMs)}
     end || C <- Comps].

%% Matches between traditional rivals. -> [{RivalryName, Match}]
derbies(Opts) ->
    Pairs = maps:from_list([{{A, B}, N} || {N, A, B} <- bs_team:rivalries()]),
    [{maps:get(pair(H, A), Pairs), M}
     || #{home := H, away := A} = M <- matches(Opts), is_map_key(pair(H, A), Pairs)].

pair(A, B) when A =< B -> {A, B};
pair(A, B) -> {B, A}.

%% Opts: name, nationality, club, position, min_overall, max_age
%% Sorted by overall rating (best first).
players(Opts) ->
    Name = fold_opt(name, Opts), Nat = fold_opt(nationality, Opts), Club = fold_opt(club, Opts),
    ClubKey = case opt(club, Opts) of
                  undefined -> undefined;
                  C -> case bs_team:classify(C) of {club, K} -> K; _ -> undefined end
              end,
    Pos = case opt(position, Opts) of
              undefined -> undefined;
              P -> position_group(P)
          end,
    Min = opt(min_overall, Opts), MaxAge = opt(max_age, Opts),
    Sel = [Pl || #{name_f := NF, nat_f := NatF, club_f := CF, club_key := CK,
                   position := Position, overall := Ov, age := Age} = Pl <- bs_data:players(),
                 contains(NF, Name),
                 Nat =:= undefined orelse NatF =:= Nat orelse is_brazil(Nat, NatF),
                 Club =:= undefined orelse (ClubKey =/= undefined andalso CK =:= ClubKey)
                     orelse (ClubKey =:= undefined andalso contains(CF, Club)),
                 Pos =:= undefined orelse lists:member(Position, Pos),
                 Min =:= undefined orelse (is_integer(Ov) andalso Ov >= Min),
                 MaxAge =:= undefined orelse (is_integer(Age) andalso Age =< MaxAge)],
    lists:sort(fun(#{overall := A, name := NA}, #{overall := B, name := NB}) ->
                       {num(A), NB} >= {num(B), NA}
               end, Sel).

num(undefined) -> -1;
num(N) -> N.

is_brazil(In, NatF) ->
    NatF =:= <<"brazil">> andalso lists:member(In, [<<"brasil">>, <<"brazilian">>, <<"brasileiro">>]).

fold_opt(K, O) ->
    case opt(K, O) of
        undefined -> undefined;
        V -> bs_team:fold(V)
    end.

contains(_, undefined) -> true;
contains(_, <<>>) -> true;
contains(Hay, Needle) ->
    %% every word of the query must appear ("gabriel barbosa" ~ "Gabriel Barbosa Almeida")
    lists:all(fun(W) -> binary:match(Hay, W) =/= nomatch end,
              binary:split(Needle, <<" ">>, [global, trim_all])).

%% "forward" -> FIFA position codes; a plain code matches itself.
position_group(P) ->
    case bs_team:fold(P) of
        <<"forward", _/binary>> -> fw();
        <<"attack", _/binary>> -> fw();
        <<"striker", _/binary>> -> [<<"ST">>, <<"CF">>, <<"LS">>, <<"RS">>];
        <<"wing", _/binary>> -> [<<"LW">>, <<"RW">>, <<"LM">>, <<"RM">>];
        <<"midfield", _/binary>> ->
            [<<"CM">>, <<"CDM">>, <<"CAM">>, <<"LM">>, <<"RM">>, <<"LCM">>, <<"RCM">>,
             <<"LDM">>, <<"RDM">>, <<"LAM">>, <<"RAM">>];
        <<"defen", _/binary>> ->
            [<<"CB">>, <<"LB">>, <<"RB">>, <<"LCB">>, <<"RCB">>, <<"LWB">>, <<"RWB">>];
        <<"goal", _/binary>> -> [<<"GK">>];
        <<"keeper", _/binary>> -> [<<"GK">>];
        F -> [string:uppercase(F)]
    end.

fw() -> [<<"ST">>, <<"CF">>, <<"LF">>, <<"RF">>, <<"LW">>, <<"RW">>, <<"LS">>, <<"RS">>].

-spec parse_competition(binary()) -> atom() | undefined.
parse_competition(B) ->
    F = bs_team:fold(B),
    Has = fun(S) -> binary:match(F, S) =/= nomatch end,
    case {Has(<<"libertadores">>), Has(<<"copa">>) orelse Has(<<"cup">>),
          Has(<<"serie b">>) orelse F =:= <<"serie_b">>, Has(<<"serie c">>) orelse F =:= <<"serie_c">>,
          Has(<<"brasileir">>) orelse Has(<<"serie a">>) orelse Has(<<"serie_a">>)
              orelse Has(<<"campeonato">>) orelse Has(<<"league">>)} of
        {true, _, _, _, _} -> libertadores;
        {_, true, _, _, _} -> copa_do_brasil;
        {_, _, true, _, _} -> serie_b;
        {_, _, _, true, _} -> serie_c;
        {_, _, _, _, true} -> serie_a;
        _ -> undefined
    end.

%% Normalises a knockout stage name to the values stored on matches.
parse_stage(B) ->
    F = bs_team:fold(B),
    Has = fun(S) -> binary:match(F, S) =/= nomatch end,
    case {Has(<<"semi">>), Has(<<"quarter">>), Has(<<"16">>), Has(<<"group">>), Has(<<"final">>)} of
        {true, _, _, _, _} -> <<"semifinals">>;
        {_, true, _, _, _} -> <<"quarterfinals">>;
        {_, _, true, _, _} -> <<"round of 16">>;
        {_, _, _, true, _} -> <<"group stage">>;
        {_, _, _, _, true} -> <<"final">>;
        _ -> F
    end.
