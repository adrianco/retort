%% Query layer: all searching, filtering and statistics over the loaded data.
%% Team arguments are raw user strings; they are resolved to canonical names
%% here (loose matching plus substring fallback) so name variations work.
-module(bsmcp_query).

-export([find_team/1, search_matches/1, head_to_head/2, team_stats/2,
         standings/2, league_stats/1, biggest_wins/1, search_players/1,
         data_summary/0, match_date_sort_desc/1]).

%%% Team resolution ------------------------------------------------------------

%% -> {ok, [CanonicalName], DisplayName} | {error, {unknown_team, binary()}}
find_team(Query) ->
    Q = bsmcp_names:canonical(Query),
    Teams = bsmcp_data:teams(),
    Exact = [C || {C, _} <- Teams, bsmcp_names:same_team(Q, C)],
    Canons =
        case Exact of
            [] ->
                QN = bsmcp_names:norm_text(Query),
                case QN of
                    <<>> -> [];
                    _ -> [C || {C, _} <- Teams,
                               binary:match(C, QN) =/= nomatch]
                end;
            _ -> Exact
        end,
    case Canons of
        [] -> {error, {unknown_team, unicode:characters_to_binary(Query)}};
        [First | _] -> {ok, Canons, bsmcp_data:team_display(First)}
    end.

involves(M, Canons) ->
    lists:member(maps:get(home_canon, M), Canons) orelse
        lists:member(maps:get(away_canon, M), Canons).

%%% Match search ---------------------------------------------------------------

%% Opts: #{team1 => binary(), team2 => binary(), competition => binary(),
%%         season => integer(), stage => binary(),
%%         date_from => binary(), date_to => binary()}   (all optional)
search_matches(Opts) ->
    case resolve_teams(Opts) of
        {error, E} ->
            {error, E};
        {ok, T1, T2} ->
            Ms0 = filter_matches(Opts),
            Ms1 = case {T1, T2} of
                      {undefined, _} -> Ms0;
                      {{C1, _}, undefined} ->
                          [M || M <- Ms0, involves(M, C1)];
                      {{C1, _}, {C2, _}} ->
                          [M || M <- Ms0, between(M, C1, C2)]
                  end,
            Sorted = match_date_sort_desc(Ms1),
            Result = #{matches => Sorted, total => length(Sorted)},
            Result2 = case {T1, T2} of
                          {{C1a, D1}, {C2a, D2}} ->
                              Result#{h2h => h2h_summary(Sorted, C1a, C2a),
                                      team1_display => D1,
                                      team2_display => D2};
                          {{_, D1}, undefined} ->
                              Result#{team1_display => D1};
                          _ -> Result
                      end,
            {ok, Result2}
    end.

resolve_teams(Opts) ->
    case resolve(maps:get(team1, Opts, undefined)) of
        {error, E} -> {error, E};
        {ok, T1} ->
            case resolve(maps:get(team2, Opts, undefined)) of
                {error, E} -> {error, E};
                {ok, T2} -> {ok, T1, T2}
            end
    end.

resolve(undefined) -> {ok, undefined};
resolve(Name) ->
    case find_team(Name) of
        {ok, Canons, Display} -> {ok, {Canons, Display}};
        {error, E} -> {error, E}
    end.

between(M, C1, C2) ->
    H = maps:get(home_canon, M),
    A = maps:get(away_canon, M),
    (lists:member(H, C1) andalso lists:member(A, C2)) orelse
        (lists:member(H, C2) andalso lists:member(A, C1)).

%% Apply the non-team filters common to most queries.
filter_matches(Opts) ->
    Comp = bsmcp_names:competition(maps:get(competition, Opts, undefined)),
    Season = maps:get(season, Opts, undefined),
    Stage = case maps:get(stage, Opts, undefined) of
                undefined -> undefined;
                S -> bsmcp_names:norm_text(S)
            end,
    From = parse_opt_date(maps:get(date_from, Opts, undefined)),
    To = parse_opt_date(maps:get(date_to, Opts, undefined)),
    [M || M <- bsmcp_data:matches(),
          comp_ok(M, Comp), season_ok(M, Season), stage_ok(M, Stage),
          date_ok(M, From, To)].

parse_opt_date(undefined) -> undefined;
parse_opt_date(B) -> bsmcp_names:parse_date(B).

comp_ok(_, any) -> true;
comp_ok(#{competition := C}, C) -> true;
comp_ok(_, _) -> false.

season_ok(_, undefined) -> true;
season_ok(#{season := S}, S) -> true;
season_ok(_, _) -> false.

stage_ok(_, undefined) -> true;
stage_ok(#{stage := undefined}, _) -> false;
stage_ok(#{stage := S}, Q) ->
    %% Exact match or query-as-prefix ("quarter" ~ "quarterfinals"); substring
    %% is deliberately not used so "final" does not match "semifinals".
    N = bsmcp_names:norm_text(S),
    N =:= Q orelse
        (byte_size(N) >= byte_size(Q) andalso
         binary:part(N, 0, byte_size(Q)) =:= Q).

date_ok(#{date := undefined}, From, To) ->
    From =:= undefined andalso To =:= undefined;
date_ok(#{date := D}, From, To) ->
    (From =:= undefined orelse D >= From) andalso
        (To =:= undefined orelse D =< To).

match_date_sort_desc(Ms) ->
    lists:sort(fun(A, B) -> sort_date(A) >= sort_date(B) end, Ms).

sort_date(#{date := undefined}) -> {0, 0, 0};
sort_date(#{date := D}) -> D.

%%% Head to head ---------------------------------------------------------------

head_to_head(Team1, Team2) ->
    case search_matches(#{team1 => Team1, team2 => Team2}) of
        {ok, R} -> {ok, R};
        {error, E} -> {error, E}
    end.

h2h_summary(Ms, C1, _C2) ->
    lists:foldl(
      fun(M, Acc = #{t1_wins := W1, t2_wins := W2, draws := Dr,
                     t1_goals := G1, t2_goals := G2}) ->
              case goals_for(M, C1) of
                  undefined -> Acc;
                  {GF, GA} ->
                      Acc2 = Acc#{t1_goals := G1 + GF, t2_goals := G2 + GA},
                      if GF > GA -> Acc2#{t1_wins := W1 + 1};
                         GF < GA -> Acc2#{t2_wins := W2 + 1};
                         true -> Acc2#{draws := Dr + 1}
                      end
              end
      end,
      #{t1_wins => 0, t2_wins => 0, draws => 0, t1_goals => 0, t2_goals => 0},
      Ms).

%% Goals from the perspective of a team (by canon set); undefined if no score
%% or the team was on neither side.
goals_for(#{hg := HG, ag := AG}, _) when HG =:= undefined; AG =:= undefined ->
    undefined;
goals_for(M = #{hg := HG, ag := AG}, Canons) ->
    case lists:member(maps:get(home_canon, M), Canons) of
        true -> {HG, AG};
        false ->
            case lists:member(maps:get(away_canon, M), Canons) of
                true -> {AG, HG};
                false -> undefined
            end
    end.

%%% Team statistics ------------------------------------------------------------

%% Opts: #{season, competition, venue (<<"home">>|<<"away">>|<<"all">>)}
team_stats(Team, Opts) ->
    case find_team(Team) of
        {error, E} ->
            {error, E};
        {ok, Canons, Display} ->
            Ms0 = filter_matches(Opts),
            Ms = [M || M <- Ms0, involves(M, Canons)],
            Venue = maps:get(venue, Opts, <<"all">>),
            Selected = [M || M <- Ms, venue_ok(M, Canons, Venue)],
            Overall = accumulate(Selected, Canons),
            Home = accumulate([M || M <- Selected, at_home(M, Canons)], Canons),
            Away = accumulate([M || M <- Selected, not at_home(M, Canons)], Canons),
            Comps = lists:usort([maps:get(competition, M) || M <- Selected]),
            {ok, #{team => Display, canons => Canons,
                   overall => Overall, home => Home, away => Away,
                   competitions => Comps, venue => Venue}}
    end.

at_home(M, Canons) -> lists:member(maps:get(home_canon, M), Canons).

venue_ok(_, _, <<"all">>) -> true;
venue_ok(M, Canons, <<"home">>) -> at_home(M, Canons);
venue_ok(M, Canons, <<"away">>) -> not at_home(M, Canons);
venue_ok(_, _, _) -> true.

accumulate(Ms, Canons) ->
    lists:foldl(
      fun(M, Acc = #{played := P, wins := W, draws := D, losses := L,
                     gf := GF0, ga := GA0}) ->
              case goals_for(M, Canons) of
                  undefined -> Acc;
                  {GF, GA} ->
                      Acc2 = Acc#{played := P + 1, gf := GF0 + GF,
                                  ga := GA0 + GA},
                      if GF > GA -> Acc2#{wins := W + 1};
                         GF < GA -> Acc2#{losses := L + 1};
                         true -> Acc2#{draws := D + 1}
                      end
              end
      end,
      #{played => 0, wins => 0, draws => 0, losses => 0, gf => 0, ga => 0},
      Ms).

%%% Standings ------------------------------------------------------------------

standings(Competition, Season) ->
    Comp = case bsmcp_names:competition(Competition) of
               any -> <<"Brasileirão Série A"/utf8>>;
               C -> C
           end,
    Ms = [M || M <- bsmcp_data:matches(),
               comp_ok(M, Comp), season_ok(M, Season),
               maps:get(hg, M) =/= undefined, maps:get(ag, M) =/= undefined],
    Table = lists:foldl(fun standings_fold/2, #{}, Ms),
    Rows = [Row#{team => T, display => bsmcp_data:team_display(T),
                 gd => maps:get(gf, Row) - maps:get(ga, Row),
                 pts => 3 * maps:get(wins, Row) + maps:get(draws, Row)}
            || {T, Row} <- maps:to_list(Table)],
    Sorted = lists:sort(fun standings_order/2, Rows),
    {ok, #{competition => Comp, season => Season, rows => Sorted,
           matches => length(Ms)}}.

standings_fold(M = #{hg := HG, ag := AG}, Acc0) ->
    H = maps:get(home_canon, M),
    A = maps:get(away_canon, M),
    Acc1 = bump(H, HG, AG, Acc0),
    bump(A, AG, HG, Acc1).

bump(Team, GF, GA, Acc) ->
    Row0 = maps:get(Team, Acc,
                    #{played => 0, wins => 0, draws => 0, losses => 0,
                      gf => 0, ga => 0}),
    Row1 = Row0#{played := maps:get(played, Row0) + 1,
                 gf := maps:get(gf, Row0) + GF,
                 ga := maps:get(ga, Row0) + GA},
    Row2 = if GF > GA -> Row1#{wins := maps:get(wins, Row1) + 1};
              GF < GA -> Row1#{losses := maps:get(losses, Row1) + 1};
              true -> Row1#{draws := maps:get(draws, Row1) + 1}
           end,
    Acc#{Team => Row2}.

standings_order(A, B) ->
    KA = {maps:get(pts, A), maps:get(wins, A), maps:get(gd, A), maps:get(gf, A)},
    KB = {maps:get(pts, B), maps:get(wins, B), maps:get(gd, B), maps:get(gf, B)},
    KA >= KB.

%%% League-wide statistics -----------------------------------------------------

league_stats(Opts) ->
    Ms = [M || M <- filter_matches(Opts),
               maps:get(hg, M) =/= undefined, maps:get(ag, M) =/= undefined],
    N = length(Ms),
    {Goals, HW, Dr, AW} =
        lists:foldl(
          fun(#{hg := HG, ag := AG}, {G, H, D, A}) ->
                  {G + HG + AG,
                   H + b2i(HG > AG), D + b2i(HG =:= AG), A + b2i(HG < AG)}
          end, {0, 0, 0, 0}, Ms),
    {ok, #{matches => N, goals => Goals,
           avg_goals => ratio(Goals, N),
           home_wins => HW, draws => Dr, away_wins => AW,
           home_win_pct => pct(HW, N), draw_pct => pct(Dr, N),
           away_win_pct => pct(AW, N)}}.

b2i(true) -> 1;
b2i(false) -> 0.

ratio(_, 0) -> 0.0;
ratio(A, B) -> A / B.

pct(_, 0) -> 0.0;
pct(A, B) -> 100.0 * A / B.

%%% Biggest wins ---------------------------------------------------------------

biggest_wins(Opts) ->
    Ms = [M || M <- filter_matches(Opts),
               maps:get(hg, M) =/= undefined, maps:get(ag, M) =/= undefined,
               maps:get(hg, M) =/= maps:get(ag, M)],
    Sorted = lists:sort(fun(A, B) -> win_key(A) >= win_key(B) end, Ms),
    {ok, Sorted}.

win_key(M = #{hg := HG, ag := AG}) ->
    {abs(HG - AG), HG + AG, sort_date(M)}.

%%% Player search --------------------------------------------------------------

%% Opts: #{name, nationality, club, position, min_overall} (all optional)
search_players(Opts) ->
    Name = norm_opt(maps:get(name, Opts, undefined)),
    Nat = norm_opt(maps:get(nationality, Opts, undefined)),
    Club = norm_opt(maps:get(club, Opts, undefined)),
    Positions = expand_position(maps:get(position, Opts, undefined)),
    MinOv = maps:get(min_overall, Opts, undefined),
    Ps = [P || P <- bsmcp_data:players(),
               contains_opt(maps:get(name_canon, P), Name),
               nat_ok(P, Nat),
               contains_opt(maps:get(club_canon, P), Club),
               position_ok(P, Positions),
               overall_ok(P, MinOv)],
    Sorted = lists:sort(
               fun(A, B) ->
                       {ov(A), maps:get(potential, A, 0)} >=
                           {ov(B), maps:get(potential, B, 0)}
               end, Ps),
    {ok, Sorted}.

ov(P) ->
    case maps:get(overall, P, undefined) of
        undefined -> 0;
        V -> V
    end.

norm_opt(undefined) -> undefined;
norm_opt(B) ->
    case bsmcp_names:norm_text(B) of
        <<>> -> undefined;
        N -> N
    end.

contains_opt(_, undefined) -> true;
contains_opt(Hay, Needle) -> binary:match(Hay, Needle) =/= nomatch.

nat_ok(_, undefined) -> true;
nat_ok(P, Nat) ->
    NC = maps:get(nat_canon, P),
    NC =:= Nat orelse
        %% "brazilian" should match "brazil"
        binary:match(Nat, NC) =/= nomatch orelse
        binary:match(NC, Nat) =/= nomatch.

position_ok(_, undefined) -> true;
position_ok(P, Positions) ->
    Pos = string:uppercase(maps:get(position, P, <<>>)),
    lists:member(Pos, Positions).

overall_ok(_, undefined) -> true;
overall_ok(P, Min) -> ov(P) >= Min.

%% Position filter accepts a FIFA position code or a role keyword.
expand_position(undefined) -> undefined;
expand_position(Text) ->
    N = bsmcp_names:norm_text(Text),
    case N of
        <<>> -> undefined;
        <<"forward", _/binary>> ->
            [<<"ST">>, <<"CF">>, <<"LF">>, <<"RF">>, <<"LW">>, <<"RW">>,
             <<"LS">>, <<"RS">>];
        <<"striker", _/binary>> -> [<<"ST">>, <<"CF">>, <<"LS">>, <<"RS">>];
        <<"attacker", _/binary>> ->
            [<<"ST">>, <<"CF">>, <<"LF">>, <<"RF">>, <<"LW">>, <<"RW">>,
             <<"LS">>, <<"RS">>, <<"CAM">>];
        <<"winger", _/binary>> -> [<<"LW">>, <<"RW">>, <<"LM">>, <<"RM">>];
        <<"midfielder", _/binary>> ->
            [<<"CM">>, <<"CDM">>, <<"CAM">>, <<"LM">>, <<"RM">>, <<"LCM">>,
             <<"RCM">>, <<"LDM">>, <<"RDM">>, <<"LAM">>, <<"RAM">>];
        <<"defender", _/binary>> ->
            [<<"CB">>, <<"LB">>, <<"RB">>, <<"LCB">>, <<"RCB">>, <<"LWB">>,
             <<"RWB">>];
        <<"goalkeeper", _/binary>> -> [<<"GK">>];
        <<"keeper", _/binary>> -> [<<"GK">>];
        _ -> [string:uppercase(unicode:characters_to_binary(Text))]
    end.

%%% Dataset summary ------------------------------------------------------------

data_summary() ->
    Base = bsmcp_data:summary(),
    PerComp = lists:foldl(
                fun(M, Acc) ->
                        C = maps:get(competition, M),
                        S = maps:get(season, M),
                        {Cnt, Smin, Smax} = maps:get(C, Acc, {0, undefined, undefined}),
                        Acc#{C => {Cnt + 1, min_def(S, Smin), max_def(S, Smax)}}
                end, #{}, bsmcp_data:matches()),
    Base#{competitions => PerComp}.

min_def(undefined, B) -> B;
min_def(A, undefined) -> A;
min_def(A, B) -> min(A, B).

max_def(undefined, B) -> B;
max_def(A, undefined) -> A;
max_def(A, B) -> max(A, B).
