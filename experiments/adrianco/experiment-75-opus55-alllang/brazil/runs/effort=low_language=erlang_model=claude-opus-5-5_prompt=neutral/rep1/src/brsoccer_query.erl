%% Query engine over the loaded match and player data. Returns plain Erlang data.
-module(brsoccer_query).
-export([matches/1, team_record/2, head_to_head/3, standings/1, standings/2, relegated/1,
         league_summary/1, biggest_wins/2, best_records/3, goals_ranking/1, derbies/1,
         team_competitions/1, players/1, brazilian_club_players/0, last_match/2,
         is_team/2, result/2, competition_matches/2]).

-define(DERBIES,
        [{<<"Fla-Flu">>, <<"flamengo">>, <<"fluminense">>},
         {<<"Clássico dos Milhões"/utf8>>, <<"flamengo">>, <<"vasco">>},
         {<<"Clássico da Rivalidade"/utf8>>, <<"botafogo">>, <<"flamengo">>},
         {<<"Clássico dos Gigantes"/utf8>>, <<"fluminense">>, <<"vasco">>},
         {<<"Clássico Vovô"/utf8>>, <<"botafogo">>, <<"fluminense">>},
         {<<"Clássico Alvinegro"/utf8>>, <<"botafogo">>, <<"vasco">>},
         {<<"Derby Paulista">>, <<"corinthians">>, <<"palmeiras">>},
         {<<"Majestoso">>, <<"corinthians">>, <<"sao paulo">>},
         {<<"Choque-Rei">>, <<"palmeiras">>, <<"sao paulo">>},
         {<<"Clássico da Saudade"/utf8>>, <<"palmeiras">>, <<"santos">>},
         {<<"Clássico Alvinegro (SP)"/utf8>>, <<"corinthians">>, <<"santos">>},
         {<<"San-São"/utf8>>, <<"santos">>, <<"sao paulo">>},
         {<<"Grenal">>, <<"gremio">>, <<"internacional">>},
         {<<"Clássico Mineiro"/utf8>>, <<"atletico mg">>, <<"cruzeiro">>},
         {<<"Ba-Vi">>, <<"bahia">>, <<"vitoria">>},
         {<<"Atletiba">>, <<"atletico pr">>, <<"coritiba">>},
         {<<"Clássico-Rei"/utf8>>, <<"ceara">>, <<"fortaleza">>},
         {<<"Clássico dos Clássicos"/utf8>>, <<"nautico">>, <<"sport">>}]).

%% ---------------------------------------------------------------- helpers

toks(undefined) -> undefined;
toks(<<>>) -> undefined;
toks(Q) -> brsoccer_norm:tokens(Q).

tm(Q, T) -> lists:all(fun(X) -> lists:member(X, T) end, Q).

%% Is the team (query) involved in match M?  home | away | false
is_team(Q, M) when is_binary(Q) -> is_team(toks(Q), M);
is_team(Q, #{ht := H, at := A}) ->
    case tm(Q, H) of
        true -> home;
        false -> case tm(Q, A) of true -> away; false -> false end
    end.

%% Result of match M from the point of view of team query Q.
result(Q, M = #{hg := HG, ag := AG}) ->
    {GF, GA} = case is_team(Q, M) of
                   home -> {HG, AG};
                   away -> {AG, HG}
               end,
    if GF > GA -> win; GF < GA -> loss; true -> draw end.

comp_match(undefined, _) -> true;
comp_match(<<>>, _) -> true;
comp_match(Q, C) ->
    Norm = fun(B) ->
                   A = brsoccer_norm:ascii(B),
                   case A of
                       <<"serie a">> -> <<"brasileirao">>;
                       <<"brasileirao serie a">> -> <<"brasileirao">>;
                       <<"campeonato brasileiro">> -> <<"brasileirao">>;
                       <<"copa libertadores">> -> <<"libertadores">>;
                       <<"brazilian cup">> -> <<"copa do brasil">>;
                       _ -> A
                   end
           end,
    binary:match(Norm(C), Norm(Q)) =/= nomatch.

opt(K, O) ->
    case maps:get(K, O, undefined) of
        null -> undefined;
        <<>> -> undefined;
        V -> V
    end.

int_opt(K, O) ->
    case opt(K, O) of
        undefined -> undefined;
        V -> brsoccer_norm:int(V)
    end.

%% ---------------------------------------------------------------- matches

%% Filters: team, opponent, home_team, away_team, competition, season,
%% date_from, date_to, stage.  Most recent first.
matches(O) ->
    Team = toks(opt(team, O)), Opp = toks(opt(opponent, O)),
    Home = toks(opt(home_team, O)), Away = toks(opt(away_team, O)),
    Comp = opt(competition, O), Season = int_opt(season, O),
    From = date_opt(date_from, O), To = date_opt(date_to, O),
    Stage = opt(stage, O),
    [M || M = #{ht := H, at := A, date := D, season := S, competition := C, stage := St}
              <- brsoccer_data:matches(),
          Season =:= undefined orelse S =:= Season,
          From =:= undefined orelse D >= From,
          To =:= undefined orelse D =< To,
          comp_match(Comp, C),
          Stage =:= undefined orelse
              binary:match(brsoccer_norm:ascii(St), brsoccer_norm:ascii(Stage)) =/= nomatch,
          Home =:= undefined orelse tm(Home, H),
          Away =:= undefined orelse tm(Away, A),
          Team =:= undefined orelse tm(Team, H) orelse tm(Team, A),
          Opp =:= undefined orelse
              (Team =:= undefined andalso (tm(Opp, H) orelse tm(Opp, A))) orelse
              (Team =/= undefined andalso ((tm(Team, H) andalso tm(Opp, A)) orelse
                                           (tm(Team, A) andalso tm(Opp, H))))].

date_opt(K, O) ->
    case opt(K, O) of
        undefined -> undefined;
        V -> brsoccer_norm:date(V)
    end.

competition_matches(Comp, Season) -> matches(#{competition => Comp, season => Season}).

last_match(A, B) ->
    case matches(#{team => A, opponent => B}) of
        [M | _] -> M;
        [] -> undefined
    end.

%% ---------------------------------------------------------------- records

%% Venue: all | home | away.
team_record(Team, O) ->
    Venue = case opt(venue, O) of undefined -> <<"all">>; V -> V end,
    Q = toks(Team),
    Ms = [M || M <- matches(O#{team => Team}),
               Venue =:= <<"all">> orelse atom_to_binary(is_team(Q, M)) =:= Venue],
    tally(Q, Ms).

tally(Q, Ms) ->
    R0 = #{matches => 0, wins => 0, draws => 0, losses => 0, goals_for => 0, goals_against => 0},
    R = lists:foldl(
          fun(M = #{hg := HG, ag := AG}, Acc) ->
                  {GF, GA} = case is_team(Q, M) of home -> {HG, AG}; away -> {AG, HG} end,
                  K = case result(Q, M) of win -> wins; draw -> draws; loss -> losses end,
                  Acc#{matches := maps:get(matches, Acc) + 1,
                       K := maps:get(K, Acc) + 1,
                       goals_for := maps:get(goals_for, Acc) + GF,
                       goals_against := maps:get(goals_against, Acc) + GA}
          end, R0, Ms),
    R#{win_rate => pct(maps:get(wins, R), maps:get(matches, R))}.

pct(_, 0) -> 0.0;
pct(N, D) -> round(1000 * N / D) / 10.

head_to_head(A, B, O) ->
    Ms = matches(O#{team => A, opponent => B}),
    QA = toks(A),
    T = tally(QA, Ms),
    #{matches => Ms, a_wins => maps:get(wins, T), b_wins => maps:get(losses, T),
      draws => maps:get(draws, T), a_goals => maps:get(goals_for, T),
      b_goals => maps:get(goals_against, T)}.

%% ---------------------------------------------------------------- standings

%% Table computed from the de-duplicated matches of all sources for that season.
standings(Season) -> standings(Season, <<"Brasileirão"/utf8>>).

standings(Season, Comp) ->
    S = brsoccer_norm:int(Season),
    All = [M || M = #{season := MS, competition := C} <- brsoccer_data:matches(),
                MS =:= S, comp_match(Comp, C)],
    Ms = case [M || M = #{source := X} <- All, X =/= br_football] of
             [] -> All;
             Primary ->
                 %% Supplement the primary source with fixtures between the same teams
                 %% (some seasons have gaps in the primary data).
                 Keys = maps:from_list([{K, true} || #{hk := K} <- Primary]),
                 Primary ++ [M || M = #{source := br_football, hk := H, ak := A} <- All,
                                  maps:is_key(H, Keys), maps:is_key(A, Keys)]
         end,
    Table = lists:foldl(
              fun(#{hk := HK, ak := AK, home := H, away := A, hg := HG, ag := AG}, T0) ->
                      T1 = add(T0, HK, H, HG, AG),
                      add(T1, AK, A, AG, HG)
              end, #{}, Ms),
    Rows = [R#{goal_diff => GF - GA} || R = #{goals_for := GF, goals_against := GA} <- maps:values(Table)],
    Sorted = lists:sort(fun(X, Y) -> sort_key(X) >= sort_key(Y) end, Rows),
    lists:zipwith(fun(P, R) -> R#{position => P} end, lists:seq(1, length(Sorted)), Sorted).

sort_key(#{points := P, wins := W, goal_diff := GD, goals_for := GF}) -> {P, W, GD, GF}.

add(T, K, Name, GF, GA) ->
    R = maps:get(K, T, #{team => Name, played => 0, wins => 0, draws => 0, losses => 0,
                         goals_for => 0, goals_against => 0, points => 0}),
    {W, D, L, P} = if GF > GA -> {1, 0, 0, 3}; GF < GA -> {0, 0, 1, 0}; true -> {0, 1, 0, 1} end,
    T#{K => R#{played := maps:get(played, R) + 1, wins := maps:get(wins, R) + W,
               draws := maps:get(draws, R) + D, losses := maps:get(losses, R) + L,
               points := maps:get(points, R) + P,
               goals_for := maps:get(goals_for, R) + GF,
               goals_against := maps:get(goals_against, R) + GA}}.

%% Bottom four of a (20-team) Brasileirão table.
relegated(Season) ->
    case standings(Season) of
        [] -> [];
        T -> lists:nthtail(max(0, length(T) - 4), T)
    end.

%% ---------------------------------------------------------------- aggregates

league_summary(O) ->
    Ms = matches(O),
    N = length(Ms),
    Goals = lists:sum([HG + AG || #{hg := HG, ag := AG} <- Ms]),
    HW = length([1 || #{hg := HG, ag := AG} <- Ms, HG > AG]),
    AW = length([1 || #{hg := HG, ag := AG} <- Ms, HG < AG]),
    #{matches => N, goals => Goals,
      avg_goals => case N of 0 -> 0.0; _ -> round(100 * Goals / N) / 100 end,
      home_win_rate => pct(HW, N), away_win_rate => pct(AW, N), draw_rate => pct(N - HW - AW, N)}.

biggest_wins(O, Limit) ->
    Ms = matches(O),
    Sorted = lists:sort(fun(A, B) -> margin(A) >= margin(B) end, Ms),
    lists:sublist(Sorted, Limit).

margin(#{hg := HG, ag := AG}) -> {abs(HG - AG), HG + AG}.

%% Teams ranked by win rate at a venue (home|away|all).
best_records(Venue, O, MinMatches) ->
    Ms = matches(O),
    Add = fun(K, Name, GF, GA, Acc) ->
                  R = maps:get(K, Acc, #{team => Name, matches => 0, wins => 0, draws => 0,
                                         losses => 0, goals_for => 0, goals_against => 0}),
                  {W, D, L} = if GF > GA -> {1, 0, 0}; GF < GA -> {0, 0, 1}; true -> {0, 1, 0} end,
                  Acc#{K => R#{matches := maps:get(matches, R) + 1, wins := maps:get(wins, R) + W,
                               draws := maps:get(draws, R) + D, losses := maps:get(losses, R) + L,
                               goals_for := maps:get(goals_for, R) + GF,
                               goals_against := maps:get(goals_against, R) + GA}}
          end,
    Table = lists:foldl(
              fun(#{hk := HK, ak := AK, home := H, away := A, hg := HG, ag := AG}, T0) ->
                      T1 = case Venue of <<"away">> -> T0; _ -> Add(HK, H, HG, AG, T0) end,
                      case Venue of <<"home">> -> T1; _ -> Add(AK, A, AG, HG, T1) end
              end, #{}, Ms),
    Rows = [R#{win_rate => pct(W, N)} || R = #{matches := N, wins := W} <- maps:values(Table),
                                         N >= MinMatches],
    lists:sort(fun(#{win_rate := X, matches := NX}, #{win_rate := Y, matches := NY}) ->
                       {X, NX} >= {Y, NY}
               end, Rows).

%% Teams ranked by goals scored.
goals_ranking(O) ->
    Rows = best_records(<<"all">>, O, 1),
    lists:sort(fun(#{goals_for := A}, #{goals_for := B}) -> A >= B end, Rows).

derbies(O) ->
    [{Name, M} || M = #{hk := HK, ak := AK} <- matches(O),
                  {Name, X, Y} <- ?DERBIES,
                  {HK, AK} =:= {X, Y} orelse {HK, AK} =:= {Y, X}].

team_competitions(Team) ->
    Ms = matches(#{team => Team}),
    Counts = lists:foldl(fun(#{competition := C, season := S}, Acc) ->
                                 {N, Ss} = maps:get(C, Acc, {0, []}),
                                 Acc#{C => {N + 1, lists:usort([S | Ss])}}
                         end, #{}, Ms),
    lists:sort([{C, N, Ss} || {C, {N, Ss}} <- maps:to_list(Counts)]).

%% ---------------------------------------------------------------- players

%% Filters: name, nationality, club, position, min_overall. Sorted by overall desc.
players(O) ->
    Name = case opt(name, O) of undefined -> undefined; N -> brsoccer_norm:ascii(N) end,
    Nat = case opt(nationality, O) of undefined -> undefined; X -> brsoccer_norm:ascii(X) end,
    Club = toks(opt(club, O)),
    Pos = case opt(position, O) of undefined -> undefined; P -> positions(P) end,
    Min = int_opt(min_overall, O),
    BrClubs = case opt(brazilian_clubs_only, O) of true -> brazilian_club_keys(); _ -> undefined end,
    Ps = [P || P = #{name := PN, nationality := PNat, club_toks := CT, position := PP,
                     overall := Ov, club_key := CK} <- brsoccer_data:players(),
               name_ok(Name, maps:get(name_any, O, false), brsoccer_norm:ascii(PN)),
               Nat =:= undefined orelse brsoccer_norm:ascii(PNat) =:= Nat,
               Club =:= undefined orelse (CT =/= [] andalso tm(Club, CT)),
               Pos =:= undefined orelse lists:member(PP, Pos),
               Min =:= undefined orelse (is_integer(Ov) andalso Ov >= Min),
               BrClubs =:= undefined orelse maps:is_key(CK, BrClubs)],
    lists:sort(fun(#{overall := A}, #{overall := B}) -> A >= B end, Ps).

%% All words of the query must occur in the name (or any word, when Any is true).
name_ok(undefined, _, _) -> true;
name_ok(Q, Any, PN) ->
    Ws = binary:split(Q, <<" ">>, [global, trim_all]),
    F = fun(W) -> binary:match(PN, W) =/= nomatch end,
    case Any of
        true -> lists:any(F, Ws);
        false -> lists:all(F, Ws)
    end.

positions(P) ->
    case brsoccer_norm:ascii(P) of
        <<"forward", _/binary>> -> [<<"ST">>, <<"CF">>, <<"LW">>, <<"RW">>, <<"LF">>, <<"RF">>, <<"LS">>, <<"RS">>];
        <<"attacker", _/binary>> -> positions(<<"forward">>);
        <<"striker", _/binary>> -> [<<"ST">>, <<"CF">>, <<"LS">>, <<"RS">>];
        <<"midfield", _/binary>> -> [<<"CM">>, <<"CAM">>, <<"CDM">>, <<"LM">>, <<"RM">>, <<"LCM">>,
                                     <<"RCM">>, <<"LAM">>, <<"RAM">>, <<"LDM">>, <<"RDM">>];
        <<"defender", _/binary>> -> [<<"CB">>, <<"LB">>, <<"RB">>, <<"LCB">>, <<"RCB">>, <<"LWB">>, <<"RWB">>];
        <<"goalkeeper", _/binary>> -> [<<"GK">>];
        Other -> [string:uppercase(Other)]
    end.

%% Club keys of teams that appear as Brazilian league teams in the match data.
brazilian_club_keys() ->
    maps:from_list([{K, true} || #{competition := C, hk := K, source := S} <- brsoccer_data:matches(),
                                 S =/= libertadores, C =:= <<"Brasileirão"/utf8>>]).

%% Players at Brazilian clubs grouped per club: [{Club, Count, AvgOverall}].
brazilian_club_players() ->
    Ps = players(#{brazilian_clubs_only => true}),
    G = lists:foldl(fun(#{club := C, overall := O}, Acc) ->
                            {N, S} = maps:get(C, Acc, {0, 0}),
                            Acc#{C => {N + 1, S + O}}
                    end, #{}, Ps),
    lists:sort(fun({_, A, _}, {_, B, _}) -> A >= B end,
               [{C, N, round(S / N)} || {C, {N, S}} <- maps:to_list(G)]).
