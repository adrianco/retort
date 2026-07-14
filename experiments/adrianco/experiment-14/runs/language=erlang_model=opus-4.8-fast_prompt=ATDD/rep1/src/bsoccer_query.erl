%%% ===================================================================
%%% Brazilian Soccer MCP Server - query engine
%%%
%%% Context: Implements the domain logic behind every MCP tool. Each
%%% exported function takes a map of tool arguments (binary keys, as
%%% decoded from JSON) and returns a structured result map (also with
%%% binary keys) that is handed straight back to the MCP client as the
%%% tool's `structuredContent'. The `bsoccer_format' module renders the
%%% same data as human-readable text.
%%%
%%% Reads the ETS tables owned by `bsoccer_data' directly. Team-name
%%% matching is delegated to `bsoccer_norm' so that "Flamengo" finds
%%% "Flamengo-RJ" while keeping the three "Atlético" clubs distinct.
%%% Competition names are resolved to a single canonical label so the
%%% two overlapping Brasileirão sources are never double-counted.
%%% ===================================================================
-module(bsoccer_query).

-export([find_matches/1, head_to_head/1, team_statistics/1, search_players/1,
         competition_standings/1, aggregate_statistics/1, list_competitions/1]).

-define(DEFAULT_LIMIT, 25).

%%% -------------------------------------------------------------------
%%% find_matches
%%% -------------------------------------------------------------------

find_matches(Args) ->
    Team = get_bin(Args, <<"team">>),
    Opponent = get_bin(Args, <<"opponent">>),
    Season = get_int(Args, <<"season">>),
    CompPred = comp_predicate(get_bin(Args, <<"competition">>)),
    StartDate = get_bin(Args, <<"start_date">>),
    EndDate = get_bin(Args, <<"end_date">>),
    Limit = get_int(Args, <<"limit">>, ?DEFAULT_LIMIT),

    Pred =
        fun(M) ->
            CompPred(M)
              andalso season_ok(Season, M)
              andalso date_ok(StartDate, EndDate, M)
              andalso teams_ok(Team, Opponent, M)
        end,
    All = collect_matches(Pred),
    Sorted = lists:sort(fun by_date_desc/2, All),
    Shown = take(Limit, Sorted),
    #{<<"count">> => length(All),
      <<"returned">> => length(Shown),
      <<"matches">> => [match_out(M) || M <- Shown]}.

teams_ok(undefined, undefined, _M) -> true;
teams_ok(Team, undefined, M) -> involves(Team, M);
teams_ok(undefined, Opp, M) -> involves(Opp, M);
teams_ok(Team, Opp, M) ->
    H = maps:get(home, M), A = maps:get(away, M),
    (bsoccer_norm:team_matches(Team, H) andalso bsoccer_norm:team_matches(Opp, A))
        orelse
    (bsoccer_norm:team_matches(Team, A) andalso bsoccer_norm:team_matches(Opp, H)).

involves(Team, M) ->
    bsoccer_norm:team_matches(Team, maps:get(home, M))
        orelse bsoccer_norm:team_matches(Team, maps:get(away, M)).

%%% -------------------------------------------------------------------
%%% head_to_head
%%% -------------------------------------------------------------------

head_to_head(Args) ->
    Team1 = get_bin(Args, <<"team1">>),
    Team2 = get_bin(Args, <<"team2">>),
    Season = get_int(Args, <<"season">>),
    CompPred = comp_predicate(get_bin(Args, <<"competition">>)),
    Limit = get_int(Args, <<"limit">>, ?DEFAULT_LIMIT),
    Pred =
        fun(M) ->
            CompPred(M) andalso season_ok(Season, M)
              andalso teams_ok(Team1, Team2, M)
        end,
    Matches = lists:sort(fun by_date_desc/2, collect_matches(Pred)),
    {W1, W2, D} =
        lists:foldl(
          fun(M, {A1, A2, Dr}) ->
              case winner_side(Team1, M) of
                  team1 -> {A1 + 1, A2, Dr};
                  team2 -> {A1, A2 + 1, Dr};
                  draw -> {A1, A2, Dr + 1}
              end
          end, {0, 0, 0}, Matches),
    #{<<"team1">> => nn(Team1), <<"team2">> => nn(Team2),
      <<"total_matches">> => length(Matches),
      <<"team1_wins">> => W1, <<"team2_wins">> => W2, <<"draws">> => D,
      <<"matches">> => [match_out(M) || M <- take(Limit, Matches)]}.

%% Which side won, expressed relative to Team1.
winner_side(Team1, M) ->
    HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
    Team1IsHome = bsoccer_norm:team_matches(Team1, maps:get(home, M)),
    if
        HG =:= AG -> draw;
        HG > AG, Team1IsHome -> team1;
        AG > HG, not Team1IsHome -> team1;
        true -> team2
    end.

%%% -------------------------------------------------------------------
%%% team_statistics
%%% -------------------------------------------------------------------

team_statistics(Args) ->
    Team = get_bin(Args, <<"team">>),
    Season = get_int(Args, <<"season">>),
    Venue = get_bin(Args, <<"venue">>, <<"all">>),
    CompPred = comp_predicate(get_bin(Args, <<"competition">>)),
    Pred =
        fun(M) ->
            CompPred(M) andalso season_ok(Season, M)
              andalso venue_ok(Venue, Team, M)
        end,
    Matches = collect_matches(Pred),
    Acc = lists:foldl(fun(M, A) -> tally(Team, M, A) end,
                      #{w => 0, d => 0, l => 0, gf => 0, ga => 0, n => 0},
                      Matches),
    #{w := W, d := D, l := L, gf := GF, ga := GA, n := N} = Acc,
    Points = 3 * W + D,
    #{<<"team">> => nn(Team),
      <<"venue">> => Venue,
      <<"matches">> => N,
      <<"wins">> => W, <<"draws">> => D, <<"losses">> => L,
      <<"goals_for">> => GF, <<"goals_against">> => GA,
      <<"goal_difference">> => GF - GA,
      <<"points">> => Points,
      <<"win_rate">> => ratio(W, N)}.

venue_ok(<<"home">>, Team, M) -> bsoccer_norm:team_matches(Team, maps:get(home, M));
venue_ok(<<"away">>, Team, M) -> bsoccer_norm:team_matches(Team, maps:get(away, M));
venue_ok(_, Team, M) -> involves(Team, M).

tally(Team, M, A) ->
    HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
    IsHome = bsoccer_norm:team_matches(Team, maps:get(home, M)),
    {For, Against} = case IsHome of true -> {HG, AG}; false -> {AG, HG} end,
    Res = if For > Against -> w; For < Against -> l; true -> d end,
    A#{Res := maps:get(Res, A) + 1,
       gf := maps:get(gf, A) + For,
       ga := maps:get(ga, A) + Against,
       n := maps:get(n, A) + 1}.

%%% -------------------------------------------------------------------
%%% competition_standings
%%% -------------------------------------------------------------------

competition_standings(Args) ->
    Comp = get_bin(Args, <<"competition">>),
    Season = get_int(Args, <<"season">>),
    Limit = get_int(Args, <<"limit">>, 100),
    CompPred = comp_predicate(Comp),
    Pred = fun(M) -> CompPred(M) andalso season_ok(Season, M) end,
    Matches = collect_matches(Pred),
    Table0 = lists:foldl(fun standings_row/2, #{}, Matches),
    Rows = maps:values(Table0),
    Ranked = rank(lists:sort(fun standings_cmp/2, Rows)),
    Shown = take(Limit, Ranked),
    #{<<"competition">> => canonical_label(Comp),
      <<"season">> => nn(Season),
      <<"teams">> => length(Rows),
      <<"standings">> => [standings_out(R) || R <- Shown]}.

standings_row(M, Table) ->
    H = maps:get(home, M), A = maps:get(away, M),
    HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
    T1 = bump(H, HG, AG, Table),
    bump(A, AG, HG, T1).

%% Update one team's accumulated row with (goals_for, goals_against).
bump(Team, For, Against, Table) ->
    R0 = maps:get(Team, Table, new_row(Team)),
    Res = if For > Against -> w; For < Against -> l; true -> d end,
    R1 = R0#{played => maps:get(played, R0) + 1,
             Res => maps:get(Res, R0) + 1,
             gf => maps:get(gf, R0) + For,
             ga => maps:get(ga, R0) + Against,
             pts => maps:get(pts, R0) + points_for(Res)},
    Table#{Team => R1}.

new_row(Team) ->
    #{team => Team, played => 0, w => 0, d => 0, l => 0, gf => 0, ga => 0, pts => 0}.

points_for(w) -> 3;
points_for(d) -> 1;
points_for(l) -> 0.

standings_cmp(A, B) ->
    KA = {maps:get(pts, A), maps:get(gf, A) - maps:get(ga, A), maps:get(gf, A)},
    KB = {maps:get(pts, B), maps:get(gf, B) - maps:get(ga, B), maps:get(gf, B)},
    case {KA, KB} of
        {X, X} -> maps:get(team, A) =< maps:get(team, B);
        _ -> KA > KB
    end.

rank(Rows) ->
    {Out, _} = lists:foldl(fun(R, {Acc, Pos}) -> {[{Pos, R} | Acc], Pos + 1} end,
                           {[], 1}, Rows),
    lists:reverse(Out).

standings_out({Pos, R}) ->
    #{<<"position">> => Pos,
      <<"team">> => maps:get(team, R),
      <<"played">> => maps:get(played, R),
      <<"wins">> => maps:get(w, R),
      <<"draws">> => maps:get(d, R),
      <<"losses">> => maps:get(l, R),
      <<"goals_for">> => maps:get(gf, R),
      <<"goals_against">> => maps:get(ga, R),
      <<"goal_difference">> => maps:get(gf, R) - maps:get(ga, R),
      <<"points">> => maps:get(pts, R)}.

%%% -------------------------------------------------------------------
%%% aggregate_statistics
%%% -------------------------------------------------------------------

aggregate_statistics(Args) ->
    Season = get_int(Args, <<"season">>),
    CompPred = comp_predicate(get_bin(Args, <<"competition">>)),
    Pred = fun(M) -> CompPred(M) andalso season_ok(Season, M) end,
    Matches = collect_matches(Pred),
    Init = #{n => 0, goals => 0, hw => 0, aw => 0, dr => 0},
    Agg = lists:foldl(fun aggregate_one/2, Init, Matches),
    #{n := N, goals := Goals, hw := HW, aw := AW, dr := Dr} = Agg,
    Biggest = biggest_wins(Matches, 10),
    #{<<"total_matches">> => N,
      <<"total_goals">> => Goals,
      <<"avg_goals_per_match">> => ratio(Goals, N),
      <<"home_wins">> => HW, <<"away_wins">> => AW, <<"draws">> => Dr,
      <<"home_win_rate">> => ratio(HW, N),
      <<"away_win_rate">> => ratio(AW, N),
      <<"draw_rate">> => ratio(Dr, N),
      <<"biggest_wins">> => Biggest}.

aggregate_one(M, A) ->
    HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
    Res = if HG > AG -> hw; AG > HG -> aw; true -> dr end,
    A#{n := maps:get(n, A) + 1,
       goals := maps:get(goals, A) + HG + AG,
       Res := maps:get(Res, A) + 1}.

biggest_wins(Matches, K) ->
    Scored = [{abs(maps:get(home_goal, M) - maps:get(away_goal, M)),
               maps:get(home_goal, M) + maps:get(away_goal, M), M}
              || M <- Matches],
    Sorted = lists:sort(fun({M1, T1, _}, {M2, T2, _}) -> {M1, T1} >= {M2, T2} end, Scored),
    [ (match_out(M))#{<<"margin">> => Margin}
      || {Margin, _Total, M} <- take(K, Sorted) ].

%%% -------------------------------------------------------------------
%%% search_players
%%% -------------------------------------------------------------------

search_players(Args) ->
    Name = get_bin(Args, <<"name">>),
    Nationality = get_bin(Args, <<"nationality">>),
    Club = get_bin(Args, <<"club">>),
    Position = get_bin(Args, <<"position">>),
    MinOverall = get_int(Args, <<"min_overall">>),
    SortBy = get_bin(Args, <<"sort_by">>, <<"overall">>),
    Limit = get_int(Args, <<"limit">>, ?DEFAULT_LIMIT),
    Pred =
        fun(P) ->
            field_contains(Name, maps:get(name, P))
              andalso field_eq_fold(Nationality, maps:get(nationality, P))
              andalso field_contains(Club, maps:get(club, P))
              andalso field_contains(Position, maps:get(position, P))
              andalso overall_ok(MinOverall, P)
        end,
    All = collect_players(Pred),
    Sorted = lists:sort(player_cmp(SortBy), All),
    Shown = take(Limit, Sorted),
    #{<<"total_available">> => length(All),
      <<"count">> => length(Shown),
      <<"players">> => [player_out(P) || P <- Shown]}.

overall_ok(undefined, _) -> true;
overall_ok(Min, P) -> maps:get(overall, P) >= Min.

%% Nationality is matched exactly (accent/case-insensitive) so that
%% "Brazil" does not also match e.g. "Brazilian"-style free text.
field_eq_fold(undefined, _) -> true;
field_eq_fold(Want, Have) -> bsoccer_norm:fold(Want) =:= bsoccer_norm:fold(Have).

field_contains(undefined, _) -> true;
field_contains(Want, Have) -> bsoccer_norm:contains_fold(Have, Want).

player_cmp(<<"name">>) ->
    fun(A, B) -> maps:get(name, A) =< maps:get(name, B) end;
player_cmp(<<"age">>) ->
    fun(A, B) -> maps:get(age, A) =< maps:get(age, B) end;
player_cmp(<<"potential">>) ->
    fun(A, B) -> maps:get(potential, A) >= maps:get(potential, B) end;
player_cmp(_) ->  %% default: overall, highest first
    fun(A, B) ->
        case {maps:get(overall, A), maps:get(overall, B)} of
            {X, X} -> maps:get(name, A) =< maps:get(name, B);
            {OA, OB} -> OA >= OB
        end
    end.

player_out(P) ->
    #{<<"name">> => maps:get(name, P),
      <<"age">> => maps:get(age, P),
      <<"nationality">> => maps:get(nationality, P),
      <<"overall">> => maps:get(overall, P),
      <<"potential">> => maps:get(potential, P),
      <<"club">> => maps:get(club, P),
      <<"position">> => maps:get(position, P)}.

%%% -------------------------------------------------------------------
%%% list_competitions
%%% -------------------------------------------------------------------

list_competitions(_Args) ->
    Table = bsoccer_data:matches_table(),
    Grouped =
        ets:foldl(
          fun({_Id, M}, Acc) ->
              C = maps:get(competition, M),
              {Cnt, Seasons} = maps:get(C, Acc, {0, sets:new([{version, 2}])}),
              S2 = case maps:get(season, M) of
                       undefined -> Seasons;
                       Sea -> sets:add_element(Sea, Seasons)
                   end,
              Acc#{C => {Cnt + 1, S2}}
          end, #{}, Table),
    Comps = [ #{<<"name">> => Name,
                <<"matches">> => Cnt,
                <<"seasons">> => lists:sort(sets:to_list(Seasons))}
              || {Name, {Cnt, Seasons}} <- maps:to_list(Grouped) ],
    Sorted = lists:sort(fun(A, B) ->
                            maps:get(<<"matches">>, A) >= maps:get(<<"matches">>, B)
                        end, Comps),
    #{<<"competitions">> => Sorted,
      <<"total_matches">> => ets:info(Table, size)}.

%%% -------------------------------------------------------------------
%%% Shared helpers
%%% -------------------------------------------------------------------

collect_matches(Pred) ->
    Table = bsoccer_data:matches_table(),
    ets:foldl(fun({_Id, M}, Acc) ->
                  case Pred(M) of true -> [M | Acc]; false -> Acc end
              end, [], Table).

collect_players(Pred) ->
    Table = bsoccer_data:players_table(),
    ets:foldl(fun({_Id, P}, Acc) ->
                  case Pred(P) of true -> [P | Acc]; false -> Acc end
              end, [], Table).

match_out(M) ->
    HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
    H = maps:get(home, M), A = maps:get(away, M),
    Winner = if HG > AG -> H; AG > HG -> A; true -> <<"Draw">> end,
    #{<<"date">> => maps:get(date, M),
      <<"season">> => nn(maps:get(season, M)),
      <<"competition">> => maps:get(competition, M),
      <<"round">> => maps:get(round, M, <<>>),
      <<"stage">> => maps:get(stage, M, <<>>),
      <<"home">> => H,
      <<"away">> => A,
      <<"home_goal">> => HG,
      <<"away_goal">> => AG,
      <<"score">> => score_bin(H, HG, AG, A),
      <<"winner">> => Winner}.

score_bin(H, HG, AG, A) ->
    iolist_to_binary([H, " ", integer_to_list(HG), "-",
                      integer_to_list(AG), " ", A]).

%% Sort key: most recent first; empty dates sort last.
by_date_desc(M1, M2) ->
    D1 = maps:get(date, M1), D2 = maps:get(date, M2),
    case {D1, D2} of
        {<<>>, <<>>} -> true;
        {<<>>, _} -> false;
        {_, <<>>} -> true;
        _ -> D1 >= D2
    end.

season_ok(undefined, _M) -> true;
season_ok(Season, M) -> maps:get(season, M) =:= Season.

date_ok(undefined, undefined, _M) -> true;
date_ok(Start, End, M) ->
    case maps:get(date, M) of
        <<>> -> false;
        D -> ge(D, Start) andalso le(D, End)
    end.

ge(_D, undefined) -> true;
ge(D, Start) -> D >= Start.

le(_D, undefined) -> true;
le(D, End) -> D =< End.

%% Build a predicate matching a single canonical competition, or all
%% matches when no competition was supplied.
comp_predicate(undefined) ->
    fun(_M) -> true end;
comp_predicate(Input) ->
    case resolve(Input) of
        {exact, Label} ->
            Folded = bsoccer_norm:fold(Label),
            fun(M) -> bsoccer_norm:fold(maps:get(competition, M)) =:= Folded end;
        {fuzzy, Raw} ->
            fun(M) -> bsoccer_norm:contains_fold(maps:get(competition, M), Raw) end
    end.

%% Resolve a user competition string to a canonical stored label.
canonical_label(undefined) -> <<>>;
canonical_label(Input) when is_binary(Input) ->
    case resolve(Input) of
        {exact, Label} -> Label;
        {fuzzy, Raw} -> Raw
    end.

resolve(Input) ->
    F = bsoccer_norm:fold(Input),
    Has = fun(Sub) -> binary:match(F, Sub) =/= nomatch end,
    Serie = <<"Brasileirão Série A"/utf8>>,
    case Has(<<"libertadores">>) of
        true -> {exact, <<"Copa Libertadores"/utf8>>};
        false ->
            case Has(<<"copa do brasil">>) orelse F =:= <<"cup">> of
                true -> {exact, <<"Copa do Brasil"/utf8>>};
                false ->
                    %% An explicit "BR Football" or historic label is matched
                    %% loosely; otherwise the Série A synonyms collapse to one
                    %% canonical source to avoid double-counting.
                    case Has(<<"football">>) orelse Has(<<"histor">>) of
                        true -> {fuzzy, Input};
                        false ->
                            case Has(<<"brasileir">>) orelse Has(<<"serie a">>)
                                 orelse Has(<<"série a"/utf8>>) of
                                true -> {exact, Serie};
                                false -> {fuzzy, Input}
                            end
                    end
            end
    end.

%% argument coercion --------------------------------------------------

get_bin(Args, Key) -> get_bin(Args, Key, undefined).
get_bin(Args, Key, Default) ->
    case maps:get(Key, Args, undefined) of
        undefined -> Default;
        null -> Default;
        <<>> -> Default;
        V when is_binary(V) -> V;
        V when is_integer(V) -> integer_to_binary(V);
        V when is_list(V) -> unicode:characters_to_binary(V);
        _ -> Default
    end.

get_int(Args, Key) -> get_int(Args, Key, undefined).
get_int(Args, Key, Default) ->
    case maps:get(Key, Args, undefined) of
        undefined -> Default;
        null -> Default;
        V when is_integer(V) -> V;
        V when is_float(V) -> round(V);
        V when is_binary(V) ->
            case string:to_integer(V) of
                {I, _} when is_integer(I) -> I;
                _ -> Default
            end;
        _ -> Default
    end.

take(undefined, L) -> L;
take(N, L) when N >= 0 -> lists:sublist(L, N);
take(_, L) -> L.

ratio(_, 0) -> 0.0;
ratio(X, N) -> round_to(X / N, 4).

round_to(F, Digits) ->
    P = math:pow(10, Digits),
    round(F * P) / P.

%% normalise "no value" to null for JSON output
nn(undefined) -> null;
nn(V) -> V.
