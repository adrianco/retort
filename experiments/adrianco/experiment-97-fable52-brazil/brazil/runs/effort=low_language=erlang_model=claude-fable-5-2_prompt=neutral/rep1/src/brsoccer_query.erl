%%% Query layer over the loaded data: match search, team records,
%%% head-to-head, standings, rankings, aggregate statistics and player search.
%%% All functions take/return plain Erlang terms; text rendering lives in
%%% brsoccer_tools.
-module(brsoccer_query).
-export([resolve_team/1, find_matches/1, record/2, team_stats/2, head_to_head/3,
         standings/2, biggest_wins/2, competition_stats/1, team_rankings/1,
         team_competitions/1, derbies/1, rivalry_name/2, bracket/2,
         search_players/1, brazilian_club_summary/0, position_group/1,
         winner/1, seasons/1]).

%% ------------------------------------------------------------------ teams
%% Resolve free text to canonical team keys.  Exact canonical match first,
%% then substring match over all known teams.
-spec resolve_team(binary()) -> [binary()].
resolve_team(Name) ->
    Teams = brsoccer_data:teams(),
    Key = brsoccer_norm:team_key(Name),
    case maps:is_key(Key, Teams) of
        true -> [Key];
        false ->
            F = brsoccer_norm:fold(Name),
            case F of
                <<>> -> [];
                _ ->
                    lists:sort([K || {K, D} <- maps:to_list(Teams),
                                     binary:match(K, F) =/= nomatch orelse
                                         binary:match(brsoccer_norm:fold(D), F) =/= nomatch])
            end
    end.

%% ---------------------------------------------------------------- matches
%% Filters (all optional): team, opponent, venue (home|away|either),
%% competition, season, date_from, date_to, round, stage, source,
%% played_only (default false).  Result is sorted newest first.
-spec find_matches(map()) -> [map()].
find_matches(F) ->
    Team = keys(maps:get(team, F, undefined)),
    Opp = keys(maps:get(opponent, F, undefined)),
    Venue = maps:get(venue, F, either),
    Comp = maps:get(competition, F, undefined),
    Season = maps:get(season, F, undefined),
    From = maps:get(date_from, F, undefined),
    To = maps:get(date_to, F, undefined),
    Round = maps:get(round, F, undefined),
    Stage = case maps:get(stage, F, undefined) of
                undefined -> undefined;
                St -> brsoccer_norm:fold(St)
            end,
    Source = maps:get(source, F, undefined),
    Played = maps:get(played_only, F, false),
    Ms = [M || #{home := H, away := A, comp := C, season := S, date := D, dup := Dup} = M
                   <- brsoccer_data:matches(),
               (Source =:= undefined andalso not Dup) orelse maps:get(source, M) =:= Source,
               Comp =:= undefined orelse C =:= Comp,
               Season =:= undefined orelse S =:= Season,
               team_ok(Team, Opp, Venue, H, A),
               From =:= undefined orelse (D =/= undefined andalso D >= From),
               To =:= undefined orelse (D =/= undefined andalso D =< To),
               Round =:= undefined orelse maps:get(round, M) =:= Round,
               Stage =:= undefined orelse stage_ok(Stage, maps:get(stage, M)),
               not Played orelse is_integer(maps:get(hg, M)) andalso is_integer(maps:get(ag, M))],
    lists:sort(fun(#{date := D1, id := I1}, #{date := D2, id := I2}) -> {D1, I1} >= {D2, I2} end, Ms).

keys(undefined) -> any;
keys(L) when is_list(L) -> L;
keys(B) when is_binary(B) -> resolve_team(B).

team_ok(any, any, _, _, _) -> true;
team_ok(any, Opp, _, H, A) -> lists:member(H, Opp) orelse lists:member(A, Opp);
team_ok(T, Opp, Venue, H, A) ->
    IsH = lists:member(H, T), IsA = lists:member(A, T),
    OppOk = fun(O) -> Opp =:= any orelse lists:member(O, Opp) end,
    case Venue of
        home -> IsH andalso OppOk(A);
        away -> IsA andalso OppOk(H);
        _ -> (IsH andalso OppOk(A)) orelse (IsA andalso OppOk(H))
    end.

stage_ok(_, undefined) -> false;
stage_ok(Want, Have) ->
    H = brsoccer_norm:fold(Have),
    Norm = fun(<<"finals">>) -> <<"final">>;
              (<<"semifinal">>) -> <<"semifinals">>;
              (<<"semi-finals">>) -> <<"semifinals">>;
              (<<"quarterfinal">>) -> <<"quarterfinals">>;
              (<<"quarter-finals">>) -> <<"quarterfinals">>;
              (<<"groups">>) -> <<"group stage">>;
              (<<"group">>) -> <<"group stage">>;
              (X) -> X
           end,
    Norm(Want) =:= Norm(H).

winner(#{hg := HG, ag := AG}) when is_integer(HG), is_integer(AG) ->
    if HG > AG -> home; HG < AG -> away; true -> draw end;
winner(_) -> undefined.

%% --------------------------------------------------------------- records
%% W/D/L record of the team(s) `Keys` over the given matches.
-spec record([map()], [binary()]) -> map().
record(Ms, Keys) ->
    Z = #{matches => 0, wins => 0, draws => 0, losses => 0, gf => 0, ga => 0},
    R = lists:foldl(
          fun(#{home := H, hg := HG, ag := AG} = M, Acc) when is_integer(HG), is_integer(AG) ->
                  {GF, GA} = case lists:member(H, Keys) of
                                 true -> {HG, AG};
                                 false -> {AG, HG}
                             end,
                  _ = M,
                  Res = if GF > GA -> wins; GF < GA -> losses; true -> draws end,
                  Acc#{matches := maps:get(matches, Acc) + 1, Res := maps:get(Res, Acc) + 1,
                       gf := maps:get(gf, Acc) + GF, ga := maps:get(ga, Acc) + GA};
             (_, Acc) -> Acc
          end, Z, Ms),
    finish_record(R).

finish_record(#{matches := N, wins := W, draws := D, gf := GF, ga := GA} = R) ->
    R#{points => 3 * W + D, gd => GF - GA,
       win_rate => pct(W, N),
       goals_per_match => ratio(GF, N)}.

pct(_, 0) -> 0.0;
pct(A, B) -> 100 * A / B.
ratio(_, 0) -> 0.0;
ratio(A, B) -> A / B.

%% Team statistics; Filters as find_matches/1 (venue honoured).
-spec team_stats(binary(), map()) -> {ok, map()} | {error, term()}.
team_stats(Team, F) ->
    case resolve_team(Team) of
        [] -> {error, {unknown_team, Team}};
        Keys ->
            Ms = find_matches(F#{team => Keys, played_only => true}),
            Split = fun(V) -> record([M || #{home := H} = M <- Ms,
                                           lists:member(H, Keys) =:= (V =:= home)], Keys) end,
            ByComp = [{C, record([M || #{comp := C1} = M <- Ms, C1 =:= C], Keys)}
                      || C <- lists:usort([C || #{comp := C} <- Ms])],
            {ok, #{team => Keys, overall => record(Ms, Keys), home => Split(home),
                   away => Split(away), by_competition => ByComp,
                   extended => extended(find_matches(F#{team => Keys, played_only => true,
                                                         source => br_football}), Keys),
                   matches => Ms}}
    end.

%% Average corners/shots (only present in the BR-Football dataset records).
extended(Ms, Keys) ->
    {N, C, S} = lists:foldl(
        fun(#{home := H, stats := St}, {N0, C0, S0} = Acc) ->
                {CK, SK} = case lists:member(H, Keys) of
                               true -> {home_corners, home_shots};
                               false -> {away_corners, away_shots}
                           end,
                case St of
                    #{CK := Cv, SK := Sv} -> {N0 + 1, C0 + Cv, S0 + Sv};
                    _ -> Acc
                end
        end, {0, 0, 0}, Ms),
    #{matches => N, avg_corners => ratio(C, N), avg_shots => ratio(S, N)}.

-spec head_to_head(binary(), binary(), map()) -> {ok, map()} | {error, term()}.
head_to_head(A, B, F) ->
    case {resolve_team(A), resolve_team(B)} of
        {[], _} -> {error, {unknown_team, A}};
        {_, []} -> {error, {unknown_team, B}};
        {KA, KB} ->
            Ms = find_matches(F#{team => KA, opponent => KB}),
            {ok, #{a => KA, b => KB, matches => Ms, record => record(Ms, KA)}}
    end.

%% -------------------------------------------------------------- standings
%% League table computed from results: 3 pts win, 1 draw; tie-breakers are
%% wins, goal difference, goals for.
-spec standings(atom(), integer()) -> [map()].
standings(Comp, Season) ->
    Ms = find_matches(#{competition => Comp, season => Season, played_only => true}),
    table(Ms).

table(Ms) ->
    Add = fun(K, GF, GA, T) ->
                  R0 = maps:get(K, T, #{matches => 0, wins => 0, draws => 0, losses => 0,
                                        gf => 0, ga => 0}),
                  Res = if GF > GA -> wins; GF < GA -> losses; true -> draws end,
                  T#{K => R0#{matches := maps:get(matches, R0) + 1, Res := maps:get(Res, R0) + 1,
                              gf := maps:get(gf, R0) + GF, ga := maps:get(ga, R0) + GA}}
          end,
    T = lists:foldl(fun(#{home := H, away := A, hg := HG, ag := AG}, Acc) ->
                            Add(A, AG, HG, Add(H, HG, AG, Acc))
                    end, #{}, Ms),
    Rows = [(finish_record(R))#{team => K} || {K, R} <- maps:to_list(T), is_binary(K)],
    Sorted = lists:sort(fun(X, Y) -> rank_key(X) >= rank_key(Y) end, Rows),
    {Out, _} = lists:mapfoldl(fun(R, I) -> {R#{position => I}, I + 1} end, 1, Sorted),
    Out.

rank_key(#{points := P, wins := W, gd := GD, gf := GF, team := T}) ->
    {P, W, GD, GF, [-C || <<C>> <= T]}.

seasons(Comp) ->
    lists:usort([S || #{comp := C, season := S} <- brsoccer_data:matches(),
                      C =:= Comp, S =/= undefined]).

%% ------------------------------------------------------------- statistics
-spec biggest_wins(map(), pos_integer()) -> [map()].
biggest_wins(F, N) ->
    Ms = find_matches(F#{played_only => true}),
    Sorted = lists:sort(fun(#{hg := H1, ag := A1, date := D1}, #{hg := H2, ag := A2, date := D2}) ->
                                {abs(H1 - A1), H1 + A1, D1} >= {abs(H2 - A2), H2 + A2, D2}
                        end, Ms),
    lists:sublist(Sorted, N).

-spec competition_stats(map()) -> map().
competition_stats(F) ->
    Ms = find_matches(F#{played_only => true}),
    N = length(Ms),
    {G, HW, AW, D, HGs} = lists:foldl(
        fun(#{hg := HG, ag := AG}, {G0, H0, A0, D0, HG0}) ->
                {G0 + HG + AG,
                 H0 + if HG > AG -> 1; true -> 0 end,
                 A0 + if AG > HG -> 1; true -> 0 end,
                 D0 + if AG =:= HG -> 1; true -> 0 end,
                 HG0 + HG}
        end, {0, 0, 0, 0, 0}, Ms),
    #{matches => N, goals => G, goals_per_match => ratio(G, N),
      home_goals => HGs, away_goals => G - HGs,
      home_wins => HW, away_wins => AW, draws => D,
      home_win_rate => pct(HW, N), away_win_rate => pct(AW, N), draw_rate => pct(D, N)}.

%% Rank teams.  Options: filters as find_matches/1 plus
%%   venue (home|away|either), metric (win_rate|points|goals_for|
%%   goals_against|goal_difference|wins|points_per_match), min_matches.
-spec team_rankings(map()) -> [map()].
team_rankings(F) ->
    Venue = maps:get(venue, F, either),
    Metric = maps:get(metric, F, win_rate),
    Min = maps:get(min_matches, F, 1),
    Ms0 = find_matches((maps:without([venue, team], F))#{played_only => true}),
    Rows0 = table(lists:append([perspective(M, Venue) || M <- Ms0])),
    Val = fun(#{matches := N, points := P} = R) ->
                  case Metric of
                      win_rate -> maps:get(win_rate, R);
                      points -> P;
                      points_per_match -> ratio(P, N);
                      goals_for -> maps:get(gf, R);
                      goals_against -> -maps:get(ga, R);
                      goal_difference -> maps:get(gd, R);
                      wins -> maps:get(wins, R);
                      _ -> maps:get(win_rate, R)
                  end
          end,
    Rows = [R || #{matches := N} = R <- Rows0, N >= Min],
    lists:sort(fun(X, Y) -> {Val(X), maps:get(matches, X)} >= {Val(Y), maps:get(matches, Y)} end, Rows).

%% For venue-restricted tables a match only counts for one side: blank out
%% the other side by mapping it to a sentinel team that is dropped later.
perspective(M, either) -> [M];
perspective(M, home) -> [M#{away := '$skip'}];
perspective(M, away) -> [M#{home := '$skip'}].

-spec team_competitions(binary()) -> {ok, [map()]} | {error, term()}.
team_competitions(Team) ->
    case resolve_team(Team) of
        [] -> {error, {unknown_team, Team}};
        Keys ->
            Ms = find_matches(#{team => Keys}),
            Comps = lists:usort([C || #{comp := C} <- Ms]),
            {ok, [begin
                      CM = [M || #{comp := C1} = M <- Ms, C1 =:= C],
                      #{competition => C,
                        seasons => lists:usort([S || #{season := S} <- CM, S =/= undefined]),
                        record => record(CM, Keys)}
                  end || C <- Comps]}
    end.

%% ---------------------------------------------------------------- derbies
rivalries() ->
    [{<<"flamengo">>, <<"fluminense">>, <<"Fla-Flu">>},
     {<<"flamengo">>, <<"vasco">>, <<"Clássico dos Milhões"/utf8>>},
     {<<"botafogo">>, <<"flamengo">>, <<"Clássico da Rivalidade"/utf8>>},
     {<<"fluminense">>, <<"vasco">>, <<"Clássico dos Gigantes"/utf8>>},
     {<<"botafogo">>, <<"fluminense">>, <<"Clássico Vovô"/utf8>>},
     {<<"botafogo">>, <<"vasco">>, <<"Clássico da Amizade"/utf8>>},
     {<<"corinthians">>, <<"palmeiras">>, <<"Derby Paulista">>},
     {<<"corinthians">>, <<"sao paulo">>, <<"Majestoso">>},
     {<<"palmeiras">>, <<"sao paulo">>, <<"Choque-Rei">>},
     {<<"corinthians">>, <<"santos">>, <<"Clássico Alvinegro"/utf8>>},
     {<<"palmeiras">>, <<"santos">>, <<"Clássico da Saudade"/utf8>>},
     {<<"santos">>, <<"sao paulo">>, <<"San-São"/utf8>>},
     {<<"gremio">>, <<"internacional">>, <<"Grenal">>},
     {<<"atletico">>, <<"cruzeiro">>, <<"Clássico Mineiro"/utf8>>},
     {<<"america">>, <<"atletico">>, <<"Clássico das Multidões"/utf8>>},
     {<<"bahia">>, <<"vitoria">>, <<"Ba-Vi">>},
     {<<"athletico">>, <<"coritiba">>, <<"Atletiba">>},
     {<<"coritiba">>, <<"parana">>, <<"Paratiba">>},
     {<<"nautico">>, <<"sport">>, <<"Clássico dos Clássicos"/utf8>>},
     {<<"santa cruz">>, <<"sport">>, <<"Clássico das Multidões"/utf8>>},
     {<<"nautico">>, <<"santa cruz">>, <<"Clássico das Emoções"/utf8>>},
     {<<"ceara">>, <<"fortaleza">>, <<"Clássico-Rei"/utf8>>},
     {<<"goias">>, <<"vila nova">>, <<"Derby do Cerrado">>},
     {<<"atletico-go">>, <<"goias">>, <<"Clássico Goiano"/utf8>>},
     {<<"avai">>, <<"figueirense">>, <<"Clássico de Florianópolis"/utf8>>},
     {<<"paysandu">>, <<"remo">>, <<"Re-Pa">>},
     {<<"crb">>, <<"csa">>, <<"Clássico das Multidões"/utf8>>},
     {<<"guarani">>, <<"ponte preta">>, <<"Derby Campineiro">>}].

-spec rivalry_name(binary(), binary()) -> binary() | undefined.
rivalry_name(A, B) ->
    {X, Y} = if A =< B -> {A, B}; true -> {B, A} end,
    case [N || {P, Q, N} <- rivalries(), P =:= X, Q =:= Y] of
        [N | _] -> N;
        [] -> undefined
    end.

%% Matches between traditional rivals; returns [{RivalryName, Match}].
-spec derbies(map()) -> [{binary(), map()}].
derbies(F) ->
    [{N, M} || #{home := H, away := A} = M <- find_matches(F),
               N <- [rivalry_name(H, A)], N =/= undefined].

%% Knock-out view: matches of a cup season grouped by stage/round.
-spec bracket(atom(), integer()) -> [{binary(), [map()]}].
bracket(Comp, Season) ->
    Ms = lists:reverse(find_matches(#{competition => Comp, season => Season})),
    Label = fun(#{stage := S, round := R}) ->
                    case {S, R} of
                        {undefined, undefined} -> <<"matches">>;
                        {undefined, _} -> iolist_to_binary(io_lib:format("round ~p", [R]));
                        _ -> S
                    end
            end,
    Order = fun(L) ->
                    case L of
                        <<"group stage">> -> {1, L};
                        <<"round of 16">> -> {3, L};
                        <<"quarterfinals">> -> {4, L};
                        <<"semifinals">> -> {5, L};
                        <<"final">> -> {6, L};
                        _ -> {2, L}
                    end
            end,
    Groups = lists:foldl(fun(M, A) -> maps:update_with(Label(M), fun(L) -> L ++ [M] end, [M], A) end,
                         #{}, Ms),
    lists:sort(fun({L1, _}, {L2, _}) -> Order(L1) =< Order(L2) end, maps:to_list(Groups)).

%% ---------------------------------------------------------------- players
position_group(Pos) ->
    case lists:member(Pos, [<<"ST">>, <<"CF">>, <<"LF">>, <<"RF">>, <<"LS">>, <<"RS">>,
                            <<"LW">>, <<"RW">>]) of
        true -> forward;
        false ->
            case lists:member(Pos, [<<"CAM">>, <<"CM">>, <<"CDM">>, <<"LAM">>, <<"RAM">>, <<"LCM">>,
                                    <<"RCM">>, <<"LDM">>, <<"RDM">>, <<"LM">>, <<"RM">>]) of
                true -> midfielder;
                false ->
                    case lists:member(Pos, [<<"CB">>, <<"LB">>, <<"RB">>, <<"LCB">>, <<"RCB">>,
                                            <<"LWB">>, <<"RWB">>]) of
                        true -> defender;
                        false when Pos =:= <<"GK">> -> goalkeeper;
                        false -> unknown
                    end
            end
    end.

parse_position(P) ->
    F = brsoccer_norm:fold(P),
    Has = fun(X) -> binary:match(F, X) =/= nomatch end,
    case {Has(<<"forward">>) orelse Has(<<"atacante">>) orelse Has(<<"striker">>) orelse Has(<<"attack">>),
          Has(<<"midfield">>) orelse Has(<<"meia">>),
          Has(<<"defen">>) orelse Has(<<"zagueiro">>) orelse Has(<<"back">>),
          Has(<<"goalkeeper">>) orelse Has(<<"keeper">>) orelse Has(<<"goleiro">>)} of
        {true, _, _, _} -> {group, forward};
        {_, true, _, _} -> {group, midfielder};
        {_, _, true, _} -> {group, defender};
        {_, _, _, true} -> {group, goalkeeper};
        _ -> {exact, string:uppercase(string:trim(P))}
    end.

%% Filters: name, nationality, club, position (code or group name),
%% min_overall, max_age, min_age, sort (overall|potential|age|name).
%% Sorted by overall rating descending by default.
-spec search_players(map()) -> [map()].
search_players(F) ->
    Name = foldopt(name, F), Nat = foldopt(nationality, F), Club = foldopt(club, F),
    ClubKey = case maps:get(club, F, undefined) of
                  undefined -> undefined;
                  C -> brsoccer_norm:team_key(C)
              end,
    Pos = case maps:get(position, F, undefined) of
              undefined -> undefined;
              P -> parse_position(P)
          end,
    MinO = maps:get(min_overall, F, undefined),
    MaxA = maps:get(max_age, F, undefined),
    MinA = maps:get(min_age, F, undefined),
    All = brsoccer_data:players(),
    %% Prefer an exact (normalised) club match -- "Sport" must not return
    %% "Sporting CP" -- and fall back to substring search otherwise.
    ExactClub = ClubKey =/= undefined andalso
        lists:any(fun(#{club_key := CK0}) -> CK0 =:= ClubKey end, All),
    Ps = [P1 || #{name_fold := NF, nationality_fold := NatF, club_fold := CF, club_key := CK,
                  position := PP, overall := O, age := Age} = P1 <- All,
                Name =:= undefined orelse name_match(Name, NF),
                Nat =:= undefined orelse NatF =:= Nat orelse (Nat =:= <<"brasil">> andalso NatF =:= <<"brazil">>)
                    orelse (Nat =:= <<"brazilian">> andalso NatF =:= <<"brazil">>),
                Club =:= undefined orelse CK =:= ClubKey orelse
                    (not ExactClub andalso binary:match(CF, Club) =/= nomatch),
                case Pos of
                    undefined -> true;
                    {group, G} -> position_group(PP) =:= G;
                    {exact, E} -> PP =:= E
                end,
                MinO =:= undefined orelse (is_integer(O) andalso O >= MinO),
                MaxA =:= undefined orelse (is_integer(Age) andalso Age =< MaxA),
                MinA =:= undefined orelse (is_integer(Age) andalso Age >= MinA)],
    Sort = case maps:get(sort, F, overall) of
               potential -> fun(#{potential := A}, #{potential := B}) -> A >= B end;
               age -> fun(#{age := A}, #{age := B}) -> A =< B end;
               name -> fun(#{name_fold := A}, #{name_fold := B}) -> A =< B end;
               _ -> fun(#{overall := A, id := I}, #{overall := B, id := J}) -> {A, -nz(I)} >= {B, -nz(J)} end
           end,
    lists:sort(Sort, Ps).

nz(undefined) -> 0;
nz(I) -> I.

foldopt(K, F) ->
    case maps:get(K, F, undefined) of
        undefined -> undefined;
        <<>> -> undefined;
        V -> brsoccer_norm:fold(V)
    end.

%% Every word of the query must appear in the player's name.
name_match(Query, NameFold) ->
    lists:all(fun(W) -> binary:match(NameFold, W) =/= nomatch end,
              binary:split(Query, <<" ">>, [global, trim_all])).

%% Brazilian-league clubs present in the FIFA data = FIFA clubs whose
%% canonical key is a team of the national league files.  Returns
%% [#{club, players, brazilians, avg_overall}] sorted by avg rating.
-spec brazilian_club_summary() -> [map()].
brazilian_club_summary() ->
    League = sets:from_list(
               lists:append([[H, A] || #{home := H, away := A, comp := C} <- brsoccer_data:matches(),
                                       C =:= serie_a orelse C =:= serie_b])),
    Groups = lists:foldl(
        fun(#{club := Club, club_key := CK, nationality := Nat, overall := O}, Acc)
              when Club =/= <<>>, is_integer(O) ->
                case sets:is_element(CK, League) andalso brazil_club_guard(Club) of
                    true ->
                        {N, B, Sum} = maps:get(Club, Acc, {0, 0, 0}),
                        Acc#{Club => {N + 1, B + if Nat =:= <<"Brazil">> -> 1; true -> 0 end, Sum + O}};
                    false -> Acc
                end;
           (_, Acc) -> Acc
        end, #{}, brsoccer_data:players()),
    Rows = [#{club => C, players => N, brazilians => B, avg_overall => Sum / N}
            || {C, {N, B, Sum}} <- maps:to_list(Groups), B * 2 >= N],
    lists:sort(fun(#{avg_overall := A}, #{avg_overall := B}) -> A >= B end, Rows).

%% Guard against foreign namesakes whose key collides with a Brazilian club.
brazil_club_guard(Club) ->
    not lists:member(Club, [<<"Boavista FC">>, <<"Sport Club">>, <<"Guaraní"/utf8>>]).
