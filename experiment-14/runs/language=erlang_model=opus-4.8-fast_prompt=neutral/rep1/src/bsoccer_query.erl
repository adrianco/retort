%%% =====================================================================
%%% bsoccer_query — query + formatting layer over the knowledge graph.
%%%
%%% Each exported function answers one family of natural-language questions
%%% from the specification (match lookups, team records, head-to-head, league
%%% standings, player search, aggregate statistics, dataset summary). They all
%%% take an argument map (the decoded MCP tool arguments, with binary keys)
%%% and return `#{text := binary(), data := term()}` where:
%%%   * `text` is a human-readable answer in the format the spec illustrates,
%%%     suitable to hand straight to an LLM, and
%%%   * `data` is the structured result for programmatic use / tests.
%%%
%%% All scanning is done with ets:foldl over the protected tables owned by
%%% bsoccer_data, so queries never mutate state and can run concurrently.
%%% Team-name arguments are matched through bsoccer_util keys, transparently
%%% handling state suffixes ("Palmeiras-SP"), accents ("Grêmio") and aliases.
%%% =====================================================================
-module(bsoccer_query).

-export([search_matches/1, head_to_head/1, team_record/1, standings/1,
         search_players/1, match_stats/1, data_summary/1]).

-define(DEFAULT_LIMIT, 30).

%% =====================================================================
%% Match search
%% =====================================================================

search_matches(Args) ->
    Pred = match_predicate(Args),
    Matches = sort_recent(canonical(collect_matches(Pred))),
    Limit = int_arg(Args, <<"limit">>, ?DEFAULT_LIMIT),
    Shown = take(Limit, Matches),
    Total = length(Matches),
    Header = search_header(Args, Total),
    Lines = [format_match_line(M) || M <- Shown],
    H2H = maybe_h2h_summary(Args, Matches),
    Text = join_lines([Header | Lines] ++ trailer(Total, Limit) ++ H2H),
    #{text => Text,
      data => #{total => Total, returned => length(Shown),
                matches => [match_to_data(M) || M <- Shown]}}.

search_header(Args, Total) ->
    Team = str_arg(Args, <<"team">>),
    Opp = str_arg(Args, <<"opponent">>),
    Desc = case {Team, Opp} of
               {undefined, undefined} -> <<"Matches">>;
               {T, undefined} -> <<"Matches for ", T/binary>>;
               {undefined, O} -> <<"Matches against ", O/binary>>;
               {T, O} -> <<T/binary, " vs ", O/binary>>
           end,
    Filt = describe_filters(Args),
    fmt("~ts~ts (~p found):", [Desc, Filt, Total]).

describe_filters(Args) ->
    Parts = lists:append(
              [case str_arg(Args, <<"competition">>) of
                   undefined -> []; C -> [fmt("competition=~ts", [C])] end,
               case int_arg(Args, <<"season">>, undefined) of
                   undefined -> []; S -> [fmt("season=~p", [S])] end,
               case int_arg(Args, <<"season_from">>, undefined) of
                   undefined -> []; S -> [fmt("from=~p", [S])] end,
               case int_arg(Args, <<"season_to">>, undefined) of
                   undefined -> []; S -> [fmt("to=~p", [S])] end,
               case str_arg(Args, <<"venue">>) of
                   undefined -> []; V -> [fmt("venue=~ts", [V])] end]),
    case Parts of
        [] -> <<>>;
        _ -> fmt(" [~ts]", [lists:join(<<", ">>, Parts)])
    end.

trailer(Total, Limit) when Total > Limit ->
    [fmt("... (~p more matches in dataset)", [Total - Limit])];
trailer(_, _) -> [].

maybe_h2h_summary(Args, Matches) ->
    case {str_arg(Args, <<"team">>), str_arg(Args, <<"opponent">>)} of
        {T, O} when T =/= undefined, O =/= undefined ->
            Key = bsoccer_util:team_key(T),
            {W, D, L, GF, GA} = h2h_tally(Key, canonical(Matches)),
            ["",
             fmt("Head-to-head in dataset (from ~ts's perspective): "
                 "~p wins, ~p draws, ~p losses; goals ~p-~p",
                 [bsoccer_util:clean_team(T), W, D, L, GF, GA])];
        _ ->
            []
    end.

%% =====================================================================
%% Head-to-head
%% =====================================================================

head_to_head(Args) ->
    T1 = require_arg(Args, <<"team1">>),
    T2 = require_arg(Args, <<"team2">>),
    K1 = bsoccer_util:team_key(T1),
    K2 = bsoccer_util:team_key(T2),
    Pred = fun(M) ->
                   both_teams(M, K1, K2) andalso has_score(M)
                   andalso comp_ok(Args, M)
           end,
    Matches = canonical(collect_matches(Pred)),
    {W1, D, W2, GF1, GF2} = h2h_pair_tally(K1, Matches),
    Recent = take(10, sort_recent(Matches)),
    Name1 = bsoccer_util:clean_team(T1),
    Name2 = bsoccer_util:clean_team(T2),
    Header = fmt("~ts vs ~ts — head-to-head (~p matches in dataset):",
                 [Name1, Name2, length(Matches)]),
    Summary = fmt("~ts ~p wins, ~ts ~p wins, ~p draws | goals: ~ts ~p - ~p ~ts",
                  [Name1, W1, Name2, W2, D, Name1, GF1, GF2, Name2]),
    RecentLines = case Recent of
                      [] -> [];
                      _ -> ["", "Most recent meetings:"
                            | [format_match_line(M) || M <- Recent]]
                  end,
    Text = join_lines([Header, Summary | RecentLines]),
    #{text => Text,
      data => #{matches => length(Matches),
                team1 => Name1, team2 => Name2,
                team1_wins => W1, team2_wins => W2, draws => D,
                team1_goals => GF1, team2_goals => GF2}}.

%% =====================================================================
%% Team record
%% =====================================================================

team_record(Args) ->
    Team = require_arg(Args, <<"team">>),
    Key = bsoccer_util:team_key(Team),
    Venue = venue_arg(Args),
    Pred = fun(M) ->
                   team_in(M, Key, Venue) andalso has_score(M)
                   andalso comp_ok(Args, M) andalso season_ok(Args, M)
           end,
    Matches = canonical(collect_matches(Pred)),
    Rec = compute_record(Key, Matches),
    Name = bsoccer_util:clean_team(Team),
    Scope = record_scope(Args, Venue),
    #{played := P, wins := W, draws := D, losses := L,
      gf := GF, ga := GA} = Rec,
    WinRate = pct(W, P),
    Text = join_lines(
             [fmt("~ts record~ts:", [Name, Scope]),
              fmt("- Matches: ~p", [P]),
              fmt("- Wins: ~p, Draws: ~p, Losses: ~p", [W, D, L]),
              fmt("- Goals For: ~p, Goals Against: ~p (diff ~ts)",
                  [GF, GA, signed(GF - GA)]),
              fmt("- Win rate: ~ts", [WinRate])]),
    #{text => Text, data => Rec#{team => Name, win_rate => WinRate}}.

record_scope(Args, Venue) ->
    Parts = lists:append(
              [case Venue of either -> []; home -> [<<"home">>]; away -> [<<"away">>] end,
               case int_arg(Args, <<"season">>, undefined) of
                   undefined -> []; S -> [fmt("~p", [S])] end,
               case str_arg(Args, <<"competition">>) of
                   undefined -> []; C -> [C] end]),
    case Parts of
        [] -> <<>>;
        _ -> fmt(" (~ts)", [lists:join(<<" ">>, Parts)])
    end.

%% =====================================================================
%% Standings (league table calculated from results)
%% =====================================================================

standings(Args) ->
    Season = require_int(Args, <<"season">>),
    Comp = str_arg_default(Args, <<"competition">>, <<"Brasileirão Série A"/utf8>>),
    CompKey = bsoccer_util:norm_key(Comp),
    Pred = fun(M) ->
                   maps:get(season, M) =:= Season
                   andalso has_score(M)
                   andalso key_contains(bsoccer_util:norm_key(maps:get(competition, M)), CompKey)
           end,
    Matches = canonical(collect_matches(Pred)),
    Table = build_table(Matches),
    Ranked = rank_table(Table),
    Limit = int_arg(Args, <<"limit">>, 20),
    Shown = take(Limit, Ranked),
    Header = fmt("~ts ~p — final standings (calculated from ~p matches):",
                 [Comp, Season, length(Matches)]),
    Lines = [format_standing_row(Row) || Row <- Shown],
    Text = join_lines([Header | Lines]),
    #{text => Text,
      data => #{season => Season, competition => Comp,
                matches => length(Matches),
                table => [standing_to_data(R) || R <- Shown]}}.

format_standing_row({Rank, Name, S}) ->
    #{points := Pts, wins := W, draws := D, losses := L,
      gf := GF, ga := GA} = S,
    Tag = case Rank of 1 -> <<" — Champion"/utf8>>; _ -> <<>> end,
    fmt("~p. ~ts — ~p pts (~pW ~pD ~pL, GF ~p GA ~p, GD ~ts)~ts",
        [Rank, Name, Pts, W, D, L, GF, GA, signed(GF - GA), Tag]).

%% =====================================================================
%% Player search
%% =====================================================================

search_players(Args) ->
    Pred = player_predicate(Args),
    Players = collect_players(Pred),
    Sorted = sort_players(Args, Players),
    Limit = int_arg(Args, <<"limit">>, 15),
    Shown = take(Limit, Sorted),
    Header = fmt("Players~ts (~p match~ts, showing ~p):",
                 [player_filter_desc(Args), length(Sorted),
                  plural(length(Sorted)), length(Shown)]),
    Lines = [format_player_line(I, P)
             || {I, P} <- lists:zip(lists:seq(1, length(Shown)), Shown)],
    Text = join_lines([Header | Lines]),
    #{text => Text,
      data => #{total => length(Sorted),
                players => [player_to_data(P) || P <- Shown]}}.

player_filter_desc(Args) ->
    Parts = lists:append(
              [case str_arg(Args, <<"name">>) of undefined -> []; N -> [fmt("name~~\"~ts\"", [N])] end,
               case str_arg(Args, <<"nationality">>) of undefined -> []; N -> [fmt("nationality=~ts", [N])] end,
               case str_arg(Args, <<"club">>) of undefined -> []; C -> [fmt("club~~\"~ts\"", [C])] end,
               case str_arg(Args, <<"position">>) of undefined -> []; P -> [fmt("position=~ts", [P])] end,
               case int_arg(Args, <<"min_overall">>, undefined) of undefined -> []; O -> [fmt("overall>=~p", [O])] end]),
    case Parts of
        [] -> <<>>;
        _ -> fmt(" [~ts]", [lists:join(<<", ">>, Parts)])
    end.

format_player_line(I, P) ->
    fmt("~p. ~ts — Overall: ~ts, Potential: ~ts, Position: ~ts, Club: ~ts, "
        "Nationality: ~ts, Age: ~ts",
        [I, gv(P, name), num(maps:get(overall, P)), num(maps:get(potential, P)),
         blank(maps:get(position, P)), blank(maps:get(club, P)),
         blank(maps:get(nationality, P)), num(maps:get(age, P))]).

%% =====================================================================
%% Aggregate statistics
%% =====================================================================

match_stats(Args) ->
    Pred = fun(M) -> has_score(M) andalso comp_ok(Args, M)
                     andalso season_ok(Args, M) andalso team_opt_ok(Args, M)
           end,
    Matches = canonical(collect_matches(Pred)),
    N = length(Matches),
    {TotalGoals, HomeW, Draw, AwayW} = aggregate(Matches),
    Avg = case N of 0 -> 0.0; _ -> TotalGoals / N end,
    Biggest = take(5, sort_by_margin(Matches)),
    Scope = describe_filters(Args),
    Lines =
        [fmt("Aggregate statistics~ts:", [Scope]),
         fmt("- Matches analysed: ~p", [N]),
         fmt("- Total goals: ~p", [TotalGoals]),
         fmt("- Average goals per match: ~ts", [f2(Avg)]),
         fmt("- Home wins: ~p (~ts), Draws: ~p (~ts), Away wins: ~p (~ts)",
             [HomeW, pct(HomeW, N), Draw, pct(Draw, N), AwayW, pct(AwayW, N)]),
         "",
         "Biggest victories (by margin):"]
        ++ [format_match_line(M) || M <- Biggest],
    Text = join_lines(Lines),
    #{text => Text,
      data => #{matches => N, total_goals => TotalGoals,
                avg_goals_per_match => Avg,
                home_wins => HomeW, draws => Draw, away_wins => AwayW,
                home_win_rate => pct(HomeW, N)}}.

%% =====================================================================
%% Dataset summary
%% =====================================================================

data_summary(_Args) ->
    S = bsoccer_data:stats(),
    Comps = maps:get(matches_by_competition, S),
    CompLines = [fmt("  - ~ts: ~p matches", [C, N])
                 || {C, N} <- lists:sort(maps:to_list(Comps))],
    Text = join_lines(
             [<<"Brazilian Soccer knowledge graph — dataset summary:"/utf8>>,
              fmt("- Total matches: ~p", [maps:get(matches, S)]),
              fmt("- Total players (FIFA): ~p", [maps:get(players, S)]),
              <<"- Matches by competition:">> | CompLines]),
    #{text => Text, data => S}.

%% =====================================================================
%% Predicate builders
%% =====================================================================

match_predicate(Args) ->
    TeamKey = case str_arg(Args, <<"team">>) of
                  undefined -> undefined;
                  T -> bsoccer_util:team_key(T)
              end,
    OppKey = case str_arg(Args, <<"opponent">>) of
                 undefined -> undefined;
                 O -> bsoccer_util:team_key(O)
             end,
    Venue = venue_arg(Args),
    fun(M) ->
            team_match_ok(M, TeamKey, Venue)
            andalso opp_ok(M, OppKey)
            andalso comp_ok(Args, M)
            andalso season_ok(Args, M)
            andalso date_ok(Args, M)
    end.

team_match_ok(_M, undefined, _Venue) -> true;
team_match_ok(M, Key, Venue) -> team_in(M, Key, Venue).

opp_ok(_M, undefined) -> true;
opp_ok(M, Key) ->
    key_contains(maps:get(home_key, M), Key)
        orelse key_contains(maps:get(away_key, M), Key).

team_in(M, Key, either) ->
    key_contains(maps:get(home_key, M), Key)
        orelse key_contains(maps:get(away_key, M), Key);
team_in(M, Key, home) -> key_contains(maps:get(home_key, M), Key);
team_in(M, Key, away) -> key_contains(maps:get(away_key, M), Key).

both_teams(M, K1, K2) ->
    H = maps:get(home_key, M), A = maps:get(away_key, M),
    (key_contains(H, K1) andalso key_contains(A, K2))
        orelse (key_contains(H, K2) andalso key_contains(A, K1)).

comp_ok(Args, M) ->
    case str_arg(Args, <<"competition">>) of
        undefined -> true;
        C ->
            key_contains(bsoccer_util:norm_key(maps:get(competition, M)),
                         bsoccer_util:norm_key(C))
    end.

season_ok(Args, M) ->
    S = maps:get(season, M),
    Exact = int_arg(Args, <<"season">>, undefined),
    From = int_arg(Args, <<"season_from">>, undefined),
    To = int_arg(Args, <<"season_to">>, undefined),
    (Exact =:= undefined orelse S =:= Exact)
        andalso (From =:= undefined orelse (is_integer(S) andalso S >= From))
        andalso (To =:= undefined orelse (is_integer(S) andalso S =< To)).

team_opt_ok(Args, M) ->
    case str_arg(Args, <<"team">>) of
        undefined -> true;
        T -> team_in(M, bsoccer_util:team_key(T), either)
    end.

date_ok(Args, M) ->
    DT = maps:get(date_tuple, M),
    From = date_bound(str_arg(Args, <<"date_from">>)),
    To = date_bound(str_arg(Args, <<"date_to">>)),
    (From =:= undefined orelse (DT =/= undefined andalso DT >= From))
        andalso (To =:= undefined orelse (DT =/= undefined andalso DT =< To)).

date_bound(undefined) -> undefined;
date_bound(Str) ->
    case bsoccer_util:parse_date(Str) of
        {DT, _} -> DT;
        undefined -> undefined
    end.

player_predicate(Args) ->
    NameKey = opt_key(str_arg(Args, <<"name">>)),
    NatKey = opt_key(str_arg(Args, <<"nationality">>)),
    ClubKey = case str_arg(Args, <<"club">>) of
                  undefined -> undefined;
                  C -> bsoccer_util:team_key(C)
              end,
    PosKey = opt_key(str_arg(Args, <<"position">>)),
    MinOverall = int_arg(Args, <<"min_overall">>, undefined),
    fun(P) ->
            opt_contains(maps:get(name_key, P), NameKey)
            andalso opt_eq_or_contains(maps:get(nationality_key, P), NatKey)
            andalso opt_contains(maps:get(club_key, P), ClubKey)
            andalso opt_pos(maps:get(position, P), PosKey)
            andalso (MinOverall =:= undefined
                     orelse (is_integer(maps:get(overall, P))
                             andalso maps:get(overall, P) >= MinOverall))
    end.

opt_key(undefined) -> undefined;
opt_key(S) -> bsoccer_util:norm_key(S).

opt_contains(_Val, undefined) -> true;
opt_contains(Val, Key) -> key_contains(Val, Key).

opt_eq_or_contains(_Val, undefined) -> true;
opt_eq_or_contains(Val, Key) -> key_contains(Val, Key).

opt_pos(_Pos, undefined) -> true;
opt_pos(Pos, Key) -> key_contains(bsoccer_util:norm_key(Pos), Key).

%% =====================================================================
%% Tallies / aggregations
%% =====================================================================

compute_record(Key, Matches) ->
    lists:foldl(
      fun(M, Acc) ->
              {For, Against, Res} = outcome(Key, M),
              #{played := P, wins := W, draws := D, losses := L,
                gf := GF, ga := GA} = Acc,
              {W1, D1, L1} = case Res of
                                 win -> {W + 1, D, L};
                                 draw -> {W, D + 1, L};
                                 loss -> {W, D, L + 1}
                             end,
              Acc#{played => P + 1, wins => W1, draws => D1, losses => L1,
                   gf => GF + For, ga => GA + Against}
      end,
      #{played => 0, wins => 0, draws => 0, losses => 0, gf => 0, ga => 0},
      Matches).

%% Determine goals for/against and result for `Key` in match M.
outcome(Key, M) ->
    HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
    case key_contains(maps:get(home_key, M), Key) of
        true  -> {HG, AG, cmp(HG, AG)};
        false -> {AG, HG, cmp(AG, HG)}
    end.

cmp(A, B) when A > B -> win;
cmp(A, B) when A < B -> loss;
cmp(_, _) -> draw.

h2h_tally(Key, Matches) ->
    lists:foldl(
      fun(M, {W, D, L, GF, GA}) ->
              {For, Against, Res} = outcome(Key, M),
              case Res of
                  win -> {W + 1, D, L, GF + For, GA + Against};
                  draw -> {W, D + 1, L, GF + For, GA + Against};
                  loss -> {W, D, L + 1, GF + For, GA + Against}
              end
      end, {0, 0, 0, 0, 0}, [M || M <- Matches, has_score(M)]).

h2h_pair_tally(K1, Matches) ->
    lists:foldl(
      fun(M, {W1, D, W2, G1, G2}) ->
              {For, Against, Res} = outcome(K1, M),
              case Res of
                  win -> {W1 + 1, D, W2, G1 + For, G2 + Against};
                  draw -> {W1, D + 1, W2, G1 + For, G2 + Against};
                  loss -> {W1, D, W2 + 1, G1 + For, G2 + Against}
              end
      end, {0, 0, 0, 0, 0}, Matches).

aggregate(Matches) ->
    lists:foldl(
      fun(M, {Goals, H, D, A}) ->
              HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
              G1 = Goals + HG + AG,
              case cmp(HG, AG) of
                  win -> {G1, H + 1, D, A};
                  draw -> {G1, H, D + 1, A};
                  loss -> {G1, H, D, A + 1}
              end
      end, {0, 0, 0, 0}, Matches).

build_table(Matches) ->
    %% Key teams by their precise identity (state suffix preserved) so clubs
    %% that differ only by state are not collapsed into one row; label each
    %% row with the full name carrying that suffix.
    lists:foldl(
      fun(M, Acc) ->
              HK = maps:get(home_ident, M), AK = maps:get(away_ident, M),
              HG = maps:get(home_goal, M), AG = maps:get(away_goal, M),
              Acc1 = add_result(Acc, HK, maps:get(home_full, M), HG, AG),
              add_result(Acc1, AK, maps:get(away_full, M), AG, HG)
      end, #{}, Matches).

add_result(Acc, Key, Name, For, Against) ->
    Cur = maps:get(Key, Acc, new_standing(Name)),
    {Dw, Dd, Dl, Dp} = points(For, Against),
    Upd = Cur#{name => maps:get(name, Cur),
               played => maps:get(played, Cur) + 1,
               wins => maps:get(wins, Cur) + Dw,
               draws => maps:get(draws, Cur) + Dd,
               losses => maps:get(losses, Cur) + Dl,
               gf => maps:get(gf, Cur) + For,
               ga => maps:get(ga, Cur) + Against,
               points => maps:get(points, Cur) + Dp},
    maps:put(Key, Upd, Acc).

new_standing(Name) ->
    #{name => Name, played => 0, wins => 0, draws => 0, losses => 0,
      gf => 0, ga => 0, points => 0}.

points(F, A) when F > A -> {1, 0, 0, 3};
points(F, A) when F < A -> {0, 0, 1, 0};
points(_, _) -> {0, 1, 0, 1}.

rank_table(Table) ->
    Rows = maps:values(Table),
    Sorted = lists:sort(fun standing_gt/2, Rows),
    lists:zipwith(fun(R, S) -> {R, maps:get(name, S), S} end,
                  lists:seq(1, length(Sorted)), Sorted).

standing_gt(A, B) ->
    KA = {maps:get(points, A), maps:get(gf, A) - maps:get(ga, A), maps:get(gf, A)},
    KB = {maps:get(points, B), maps:get(gf, B) - maps:get(ga, B), maps:get(gf, B)},
    KA >= KB.

%% =====================================================================
%% Collection / sorting helpers
%% =====================================================================

collect_matches(Pred) ->
    ets:foldl(fun({_, M}, Acc) ->
                      case Pred(M) of true -> [M | Acc]; false -> Acc end
              end, [], bsoccer_data:matches_table()).

collect_players(Pred) ->
    ets:foldl(fun({_, P}, Acc) ->
                      case Pred(P) of true -> [P | Acc]; false -> Acc end
              end, [], bsoccer_data:players_table()).

%% The five match files overlap heavily — e.g. the 2019 Brasileirão appears in
%% full in three of them, each spelling team names slightly differently, so a
%% naive value-based dedup leaves residual double counting. Instead we
%% canonicalise: bucket matches by {competition, season} and, within each
%% bucket, keep only the rows from the single highest-priority source that is
%% present. Every authoritative source carries a complete season, so this
%% yields exactly one copy of each match with consistent in-source naming.
canonical(Matches) ->
    Buckets = lists:foldl(
                fun(M, Acc) ->
                        K = {maps:get(competition, M), maps:get(season, M)},
                        maps:update_with(K, fun(L) -> [M | L] end, [M], Acc)
                end, #{}, Matches),
    lists:append([pick_source(B) || B <- maps:values(Buckets)]).

%% From one {competition, season} bucket, keep matches from the best source.
pick_source(Bucket) ->
    Best = lists:foldl(
             fun(M, Cur) ->
                     R = src_rank(maps:get(source, M)),
                     case Cur of undefined -> R; _ -> min(Cur, R) end
             end, undefined, Bucket),
    [M || M <- Bucket, src_rank(maps:get(source, M)) =:= Best].

%% Source priority: lower is more authoritative/complete for its competitions.
src_rank(<<"novo_campeonato_brasileiro.csv">>) -> 1;
src_rank(<<"Brasileirao_Matches.csv">>) -> 2;
src_rank(<<"Brazilian_Cup_Matches.csv">>) -> 3;
src_rank(<<"Libertadores_Matches.csv">>) -> 4;
src_rank(<<"BR-Football-Dataset.csv">>) -> 5;
src_rank(_) -> 99.

sort_recent(Matches) ->
    lists:sort(fun(A, B) ->
                       date_key(A) >= date_key(B)
               end, Matches).

date_key(M) ->
    case maps:get(date_tuple, M) of
        undefined -> {0, 0, 0};
        DT -> DT
    end.

sort_by_margin(Matches) ->
    lists:sort(fun(A, B) -> margin(A) >= margin(B) end, Matches).

margin(M) -> abs(maps:get(home_goal, M) - maps:get(away_goal, M)).

has_score(M) ->
    is_integer(maps:get(home_goal, M)) andalso is_integer(maps:get(away_goal, M)).

sort_players(Args, Players) ->
    case str_arg(Args, <<"sort">>) of
        <<"potential">> -> lists:sort(fun(A, B) -> ge(potential, A, B) end, Players);
        _ -> lists:sort(fun(A, B) -> ge(overall, A, B) end, Players)
    end.

ge(Field, A, B) ->
    nz(maps:get(Field, A)) >= nz(maps:get(Field, B)).

nz(undefined) -> -1;
nz(N) -> N.

%% =====================================================================
%% Formatting helpers
%% =====================================================================

format_match_line(M) ->
    Date = case maps:get(date, M) of undefined -> <<"????-??-??">>; D -> D end,
    Score = case has_score(M) of
                true -> fmt("~p-~p", [maps:get(home_goal, M), maps:get(away_goal, M)]);
                false -> <<"?-?">>
            end,
    Ctx = match_context(M),
    fmt("- ~ts: ~ts ~ts ~ts (~ts)",
        [Date, maps:get(home, M), Score, maps:get(away, M), Ctx]).

match_context(M) ->
    Comp = maps:get(competition, M),
    Extra = case {maps:get(round, M), maps:get(stage, M)} of
                {undefined, undefined} -> <<>>;
                {R, undefined} -> fmt(" Round ~ts", [R]);
                {undefined, S} -> fmt(" ~ts", [S]);
                {R, S} -> fmt(" ~ts/Round ~ts", [S, R])
            end,
    fmt("~ts~ts", [Comp, Extra]).

match_to_data(M) ->
    #{date => null_undef(maps:get(date, M)),
      competition => maps:get(competition, M),
      home => maps:get(home, M), away => maps:get(away, M),
      home_goal => null_undef(maps:get(home_goal, M)),
      away_goal => null_undef(maps:get(away_goal, M)),
      season => null_undef(maps:get(season, M)),
      round => null_undef(maps:get(round, M)),
      stage => null_undef(maps:get(stage, M)),
      source => maps:get(source, M)}.

standing_to_data({Rank, Name, S}) ->
    S#{rank => Rank, name => Name}.

player_to_data(P) ->
    #{name => maps:get(name, P), overall => null_undef(maps:get(overall, P)),
      potential => null_undef(maps:get(potential, P)),
      position => maps:get(position, P), club => maps:get(club, P),
      nationality => maps:get(nationality, P), age => null_undef(maps:get(age, P)),
      jersey => null_undef(maps:get(jersey, P)),
      height => maps:get(height, P), weight => maps:get(weight, P),
      foot => maps:get(foot, P), skills => maps:get(skills, P)}.

%% =====================================================================
%% Argument extraction (handles binary or atom keys, ints or strings)
%% =====================================================================

str_arg(Args, Key) ->
    case raw_arg(Args, Key) of
        undefined -> undefined;
        B when is_binary(B) ->
            case bsoccer_util:trim(B) of <<>> -> undefined; T -> T end;
        L when is_list(L) -> str_arg(#{Key => unicode:characters_to_binary(L)}, Key);
        I when is_integer(I) -> integer_to_binary(I);
        _ -> undefined
    end.

str_arg_default(Args, Key, Default) ->
    case str_arg(Args, Key) of undefined -> Default; V -> V end.

int_arg(Args, Key, Default) ->
    case raw_arg(Args, Key) of
        undefined -> Default;
        I when is_integer(I) -> I;
        B when is_binary(B) ->
            case bsoccer_util:parse_int(B) of undefined -> Default; V -> V end;
        _ -> Default
    end.

raw_arg(Args, Key) when is_binary(Key) ->
    case maps:find(Key, Args) of
        {ok, V} -> V;
        error ->
            try maps:find(binary_to_existing_atom(Key, utf8), Args) of
                {ok, V2} -> V2;
                error -> undefined
            catch _:_ -> undefined
            end
    end.

require_arg(Args, Key) ->
    case str_arg(Args, Key) of
        undefined -> throw({missing_argument, Key});
        V -> V
    end.

require_int(Args, Key) ->
    case int_arg(Args, Key, undefined) of
        undefined -> throw({missing_argument, Key});
        V -> V
    end.

venue_arg(Args) ->
    case str_arg(Args, <<"venue">>) of
        <<"home">> -> home;
        <<"away">> -> away;
        _ -> either
    end.

%% =====================================================================
%% Small utilities
%% =====================================================================

key_contains(_Hay, <<>>) -> false;
key_contains(<<>>, _Needle) -> false;
key_contains(Hay, Needle) when is_binary(Hay), is_binary(Needle) ->
    %% Both binaries are non-empty here, so binary:match/2 (which rejects an
    %% empty pattern) is always safe. Match in either direction so a short
    %% query key finds a longer stored key and vice versa.
    Hay =:= Needle
        orelse binary:match(Hay, Needle) =/= nomatch
        orelse binary:match(Needle, Hay) =/= nomatch;
key_contains(_, _) -> false.

take(N, L) when N >= 0 -> lists:sublist(L, N).

join_lines(Lines) ->
    Flat = [to_line(L) || L <- Lines],
    iolist_to_binary(lists:join(<<"\n">>, Flat)).

to_line(B) when is_binary(B) -> B;
to_line(L) -> unicode:characters_to_binary(L).

fmt(Format, Args) ->
    unicode:characters_to_binary(io_lib:format(Format, Args)).

pct(_, 0) -> <<"0.0%">>;
pct(X, N) -> fmt("~ts%", [f2(100.0 * X / N)]).

f2(F) -> fmt("~.1f", [F * 1.0]).

signed(N) when N >= 0 -> fmt("+~p", [N]);
signed(N) -> fmt("~p", [N]).

num(undefined) -> <<"n/a">>;
num(N) -> integer_to_binary(N).

blank(<<>>) -> <<"(unknown)">>;
blank(B) -> B.

gv(P, Key) -> maps:get(Key, P).

null_undef(undefined) -> null;
null_undef(V) -> V.

plural(1) -> <<>>;
plural(_) -> <<"es">>.
