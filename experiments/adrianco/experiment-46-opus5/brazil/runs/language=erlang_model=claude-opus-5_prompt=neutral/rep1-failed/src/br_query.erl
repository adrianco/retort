%%%-------------------------------------------------------------------
%%% @doc The query layer: everything the MCP tools expose.
%%%
%%% All functions take a map of options whose keys may be atoms (when
%%% called from Erlang) or binaries (when the arguments arrive as JSON
%%% from an MCP client), and return plain maps that can be rendered
%%% either as JSON (`structuredContent') or as text (see {@link
%%% br_format}).
%%%
%%% Errors are values, never exceptions: `{error, #{code := ..., message
%%% := ..., suggestions := [...]}}'.
%%% @end
%%%-------------------------------------------------------------------
-module(br_query).

-include("br_soccer.hrl").

-export([find_matches/1,
         head_to_head/1,
         team_stats/1,
         team_profile/1,
         standings/1,
         team_rankings/1,
         competition_stats/1,
         compare_seasons/1,
         biggest_wins/1,
         search_players/1,
         player_profile/1,
         club_squad/1,
         player_club_summary/1,
         derbies/1,
         list_teams/1,
         list_competitions/1,
         dataset_summary/1,
         graph_neighbors/1,
         graph_path/1,
         match_map/1,
         resolve_team/2,
         opt/3]).

-define(DEFAULT_LIMIT, 20).
-define(MAX_LIMIT, 500).

%%====================================================================
%% Matches
%%====================================================================

%% @doc Search matches by team, opponent, competition, season, date range.
-spec find_matches(map()) -> {ok, map()} | {error, map()}.
find_matches(Opts) ->
    with_teams([{team, team}, {opponent, opponent}, {home_team, home_team},
                {away_team, away_team}], Opts,
      fun(Teams) ->
          Comp = competition_opt(Opts),
          Candidates = candidate_matches(Teams),
          Filtered = [M || M <- Candidates, match_filter(M, Teams, Comp, Opts)],
          Sorted = sort_matches(Filtered, opt(sort, Opts, <<"date_desc">>)),
          Limit = limit(Opts),
          {ok, #{query => describe_query(Teams, Comp, Opts),
                 total => length(Sorted),
                 returned => min(Limit, length(Sorted)),
                 matches => [match_map(M) || M <- lists:sublist(Sorted, Limit)]}}
      end).

%% @doc Complete head-to-head record between two teams.
-spec head_to_head(map()) -> {ok, map()} | {error, map()}.
head_to_head(Opts) ->
    case {opt(team_a, Opts, opt(team, Opts, undefined)),
          opt(team_b, Opts, opt(opponent, Opts, undefined))} of
        {undefined, _} ->
            {error, error_map(missing_argument, <<"team_a is required">>, [])};
        {_, undefined} ->
            {error, error_map(missing_argument, <<"team_b is required">>, [])};
        {A0, B0} -> head_to_head(A0, B0, Opts)
    end.

head_to_head(A0, B0, Opts0) ->
    Opts = Opts0#{team_a => A0, team_b => B0},
    with_teams([{team_a, team}, {team_b, opponent}], Opts,
      fun(#{team := A, opponent := B} = Teams) ->
          Comp = competition_opt(Opts),
          Matches = [M || M <- br_store:team_matches(A),
                          involves(M, B),
                          match_filter(M, Teams, Comp, Opts)],
          Sorted = sort_matches(Matches, opt(sort, Opts, <<"date_desc">>)),
          Played = [M || M <- Sorted, has_score(M)],
          {AWins, BWins, Draws, AGoals, BGoals} = h2h_counts(A, Played),
          Limit = limit(Opts),
          {ok, #{team_a => team_ref(A), team_b => team_ref(B),
                 derby => null_if_undefined(br_names:rivalry_of(A, B)),
                 total => length(Sorted),
                 played => length(Played),
                 team_a_wins => AWins, team_b_wins => BWins, draws => Draws,
                 team_a_goals => AGoals, team_b_goals => BGoals,
                 competition => null_if_undefined(Comp),
                 season => null_if_undefined(season_opt(Opts)),
                 matches => [match_map(M) || M <- lists:sublist(Sorted, Limit)],
                 returned => min(Limit, length(Sorted))}}
      end).

h2h_counts(A, Matches) ->
    lists:foldl(
      fun(#match{home = H, home_goals = HG, away_goals = AG}, {W, L, D, GF, GA}) ->
              {Own, Opp} = case H =:= A of
                               true -> {HG, AG};
                               false -> {AG, HG}
                           end,
              case {Own > Opp, Own < Opp} of
                  {true, _} -> {W + 1, L, D, GF + Own, GA + Opp};
                  {_, true} -> {W, L + 1, D, GF + Own, GA + Opp};
                  _ -> {W, L, D + 1, GF + Own, GA + Opp}
              end
      end, {0, 0, 0, 0, 0}, Matches).

%% @doc Biggest winning margins, optionally per competition/season/team.
-spec biggest_wins(map()) -> {ok, map()} | {error, map()}.
biggest_wins(Opts) ->
    with_teams([{team, team}], Opts,
      fun(Teams) ->
          Comp = competition_opt(Opts),
          Candidates = candidate_matches(Teams),
          Scored = [M || M <- Candidates, has_score(M),
                         match_filter(M, Teams, Comp, Opts)],
          Sorted = lists:sort(fun(A, B) -> margin_key(A) >= margin_key(B) end, Scored),
          Limit = limit(Opts),
          {ok, #{total => length(Sorted),
                 returned => min(Limit, length(Sorted)),
                 matches => [begin
                                 Map = match_map(M),
                                 Map#{margin => abs(M#match.home_goals - M#match.away_goals)}
                             end || M <- lists:sublist(Sorted, Limit)]}}
      end).

margin_key(#match{home_goals = H, away_goals = A, date = D}) ->
    {abs(H - A), H + A, br_date:to_days(D)}.

%%====================================================================
%% Teams
%%====================================================================

%% @doc Wins/draws/losses/goals for a team, with home and away splits.
-spec team_stats(map()) -> {ok, map()} | {error, map()}.
team_stats(Opts) ->
    with_teams([{team, team}], Opts,
      fun(#{team := Id} = Teams) ->
          Comp = competition_opt(Opts),
          All = [M || M <- br_store:team_matches(Id),
                      match_filter(M, Teams, Comp, Opts), has_score(M)],
          Venue = venue_opt(Opts),
          Selected = [M || M <- All, venue_match(M, Id, Venue)],
          Base = record_of(Id, Selected),
          Home = record_of(Id, [M || M <- All, M#match.home =:= Id]),
          Away = record_of(Id, [M || M <- All, M#match.away =:= Id]),
          Biggest = case lists:sort(fun(A, B) -> team_margin(Id, A) >= team_margin(Id, B) end,
                                    [M || M <- Selected, won(Id, M)]) of
                        [Best | _] -> match_map(Best);
                        [] -> null
                    end,
          {ok, maps:merge(
                 Base,
                 #{team => Id, team_name => team_name(Id),
                   competition => null_if_undefined(Comp),
                   competition_name => comp_name_or_null(Comp),
                   season => null_if_undefined(season_opt(Opts)),
                   venue => Venue,
                   home => Home, away => Away,
                   biggest_win => Biggest,
                   first_match => date_or_null(first_date(Selected)),
                   last_match => date_or_null(last_date(Selected))})}
      end).

%% @doc Everything the graph knows about one club, across all files.
-spec team_profile(map()) -> {ok, map()} | {error, map()}.
team_profile(Opts) ->
    with_teams([{team, team}], Opts,
      fun(#{team := Id}) ->
          Matches = [M || M <- br_store:team_matches(Id), has_score(M)],
          {ok, Team} = team_or_default(Id),
          ByComp = group_by(fun(#match{competition = C}) -> C end, Matches),
          BySeason = group_by(fun(#match{season = S}) -> S end, Matches),
          Squad = br_store:players_of_club(Id),
          {ok, #{team => Id,
                 team_name => Team#team.name,
                 state => null_if_undefined(Team#team.state),
                 country => null_if_undefined(Team#team.country),
                 aliases => Team#team.aliases,
                 seasons => Team#team.seasons,
                 overall => record_of(Id, Matches),
                 by_competition =>
                     [maps:merge(#{competition => C,
                                   competition_name => br_names:competition_display(C)},
                                 record_of(Id, Ms))
                      || {C, Ms} <- lists:sort(ByComp)],
                 by_season =>
                     [maps:merge(#{season => S}, record_of(Id, Ms))
                      || {S, Ms} <- lists:reverse(lists:sort(BySeason)), S =/= undefined],
                 squad_size => length(Squad),
                 squad_note => squad_note(Squad),
                 squad => [player_summary(P) || P <- top_players(Squad, 10)],
                 rivals => [#{derby => Name, team => Other, team_name => team_name(Other)}
                            || {Name, X, Y} <- br_names:rivalries(),
                               {Match, Other} <- [{X =:= Id, Y}, {Y =:= Id, X}], Match]}}
      end).

squad_note([]) ->
    <<"No squad in fifa_data.csv - FIFA 19 did not license every Brazilian club.">>;
squad_note(_) ->
    <<"Squad from fifa_data.csv (FIFA 19 ratings).">>.

%% @doc List the teams in the graph, optionally filtered.
-spec list_teams(map()) -> {ok, map()}.
list_teams(Opts) ->
    Comp = competition_opt(Opts),
    Season = season_opt(Opts),
    State = case opt(state, Opts, undefined) of
                undefined -> undefined;
                S -> string:uppercase(to_bin(S))
            end,
    Query = opt(query, Opts, undefined),
    Teams0 = case Query of
                 undefined -> br_store:all_teams();
                 Q -> br_store:search_teams(Q)
             end,
    Teams = [T || T <- Teams0,
                  (Comp =:= undefined orelse lists:member(Comp, T#team.competitions)),
                  (Season =:= undefined orelse lists:member(Season, T#team.seasons)),
                  (State =:= undefined orelse T#team.state =:= State)],
    Sorted = lists:sort(fun(#team{match_count = A}, #team{match_count = B}) -> A >= B end,
                        Teams),
    Limit = limit(Opts, 50),
    {ok, #{total => length(Sorted),
           returned => min(Limit, length(Sorted)),
           teams => [team_map(T) || T <- lists:sublist(Sorted, Limit)]}}.

team_map(#team{} = T) ->
    #{team => T#team.id,
      name => T#team.name,
      state => null_if_undefined(T#team.state),
      country => null_if_undefined(T#team.country),
      matches => T#team.match_count,
      competitions => T#team.competitions,
      seasons => T#team.seasons,
      aliases => T#team.aliases}.

%%====================================================================
%% Competitions
%%====================================================================

%% @doc League table computed from the match results themselves.
-spec standings(map()) -> {ok, map()} | {error, map()}.
standings(Opts) ->
    case competition_opt(Opts, <<"brasileirao_serie_a">>) of
        undefined ->
            {error, error_map(unknown_competition, <<"unknown competition">>, [])};
        Comp ->
            case season_opt(Opts) of
                undefined ->
                    {error, error_map(missing_season,
                                      <<"a season is required, e.g. 2019">>,
                                      [integer_to_binary(S)
                                       || S <- lists:reverse(br_store:seasons_of(Comp))])};
                Season -> standings(Comp, Season, Opts)
            end
    end.

standings(Comp, Season, Opts) ->
    Matches = [M || M <- br_store:fold_matches(fun(M, A) -> [M | A] end, []),
                    M#match.competition =:= Comp,
                    M#match.season =:= Season,
                    has_score(M)],
    case Matches of
        [] ->
            {error, error_map(no_data,
                              iolist_to_binary(
                                io_lib:format("no ~s matches for season ~p",
                                              [br_names:competition_display(Comp), Season])),
                              [integer_to_binary(S) || S <- br_store:seasons_of(Comp)])};
        _ ->
            Table = build_table(Matches),
            Complete = is_complete_league(Comp, Table, length(Matches)),
            Limit = limit(Opts, ?MAX_LIMIT),
            {ok, #{competition => Comp,
                   competition_name => br_names:competition_display(Comp),
                   competition_type => case is_league(Comp) of
                                           true -> <<"league">>;
                                           false -> <<"knockout">>
                                       end,
                   season => Season,
                   matches => length(Matches),
                   teams => length(Table),
                   complete => Complete,
                   champion => case {Complete, Table} of
                                   {true, [#{team_name := N} | _]} -> N;
                                   _ -> null
                               end,
                   relegated => relegated(Comp, Complete, Table),
                   table => lists:sublist(Table, Limit)}}
    end.

build_table(Matches) ->
    Records = lists:foldl(
                fun(#match{home = H, away = A, home_goals = HG, away_goals = AG}, Acc) ->
                        Acc1 = tally(H, HG, AG, Acc),
                        tally(A, AG, HG, Acc1)
                end, #{}, Matches),
    Rows = [row(Id, R) || {Id, R} <- maps:to_list(Records)],
    Ranked = lists:sort(fun(A, B) -> table_key(A) >= table_key(B) end, Rows),
    lists:zipwith(fun(Pos, Row) -> Row#{position => Pos} end,
                  lists:seq(1, length(Ranked)), Ranked).

tally(Team, GF, GA, Acc) ->
    #{played := P, wins := W, draws := D, losses := L, gf := F, ga := Ag} =
        maps:get(Team, Acc, #{played => 0, wins => 0, draws => 0, losses => 0,
                              gf => 0, ga => 0}),
    New = case {GF > GA, GF < GA} of
              {true, _} -> #{played => P + 1, wins => W + 1, draws => D, losses => L,
                             gf => F + GF, ga => Ag + GA};
              {_, true} -> #{played => P + 1, wins => W, draws => D, losses => L + 1,
                             gf => F + GF, ga => Ag + GA};
              _ -> #{played => P + 1, wins => W, draws => D + 1, losses => L,
                     gf => F + GF, ga => Ag + GA}
          end,
    Acc#{Team => New}.

row(Id, #{played := P, wins := W, draws := D, losses := L, gf := GF, ga := GA}) ->
    #{team => Id, team_name => team_name(Id), played => P, wins => W, draws => D,
      losses => L, goals_for => GF, goals_against => GA, goal_difference => GF - GA,
      points => W * 3 + D}.

table_key(#{points := Pts, wins := W, goal_difference := GD, goals_for := GF}) ->
    {Pts, W, GD, GF}.

is_league(Comp) ->
    lists:member(Comp, [<<"brasileirao_serie_a">>, <<"brasileirao_serie_b">>,
                        <<"brasileirao_serie_c">>]).

%% A league season is "complete" when every team played the same,
%% plausible number of games - the guard for partial data sets.
is_complete_league(Comp, Table, MatchCount) ->
    IsLeague = is_league(Comp),
    N = length(Table),
    Played = lists:usort([P || #{played := P} <- Table]),
    IsLeague andalso N >= 8 andalso Played =:= [2 * (N - 1)]
        andalso MatchCount =:= N * (N - 1).

relegated(Comp, true, Table) when Comp =:= <<"brasileirao_serie_a">>;
                                  Comp =:= <<"brasileirao_serie_b">> ->
    N = length(Table),
    case N >= 16 of
        true -> [maps:get(team_name, R) || R <- lists:nthtail(N - 4, Table)];
        false -> []
    end;
relegated(_, _, _) -> [].

%% @doc Rank teams by a metric, optionally home-only or away-only.
%%
%% Answers "which team has the best home record", "which team scored the
%% most goals in Serie A 2023" and "who has the meanest defence".
-spec team_rankings(map()) -> {ok, map()} | {error, map()}.
team_rankings(Opts) ->
    Comp = competition_opt(Opts),
    Season = season_opt(Opts),
    Venue = venue_opt(Opts),
    Metric = metric_opt(Opts),
    Matches = [M || M <- br_store:fold_matches(fun(M, A) -> [M | A] end, []),
                    (Comp =:= undefined orelse M#match.competition =:= Comp),
                    (Season =:= undefined orelse M#match.season =:= Season),
                    has_score(M)],
    case Matches of
        [] -> {error, error_map(no_data, <<"no matches for that filter">>, [])};
        _ ->
            Records = lists:foldl(
                        fun(#match{home = H, away = A, home_goals = HG, away_goals = AG},
                            Acc) ->
                                case Venue of
                                    <<"home">> -> tally(H, HG, AG, Acc);
                                    <<"away">> -> tally(A, AG, HG, Acc);
                                    _ -> tally(A, AG, HG, tally(H, HG, AG, Acc))
                                end
                        end, #{}, Matches),
            MinMatches = case to_int(opt(min_matches, Opts, undefined)) of
                             undefined -> default_min_matches(Metric);
                             N -> N
                         end,
            Rows0 = [enrich(row(Id, R)) || {Id, R} <- maps:to_list(Records)],
            Rows = [R || R <- Rows0, maps:get(played, R) >= MinMatches],
            Ascending = ascending_metric(Metric),
            Sorted = lists:sort(fun(A, B) ->
                                        KA = {maps:get(Metric, A), maps:get(points, A)},
                                        KB = {maps:get(Metric, B), maps:get(points, B)},
                                        case Ascending of
                                            true -> KA =< KB;
                                            false -> KA >= KB
                                        end
                                end, Rows),
            Limit = limit(Opts, 10),
            Ranked = lists:zipwith(fun(Pos, Row) -> Row#{position => Pos} end,
                                   lists:seq(1, length(Sorted)), Sorted),
            {ok, #{competition => null_if_undefined(Comp),
                   competition_name => comp_name_or_null(Comp),
                   season => null_if_undefined(Season),
                   venue => Venue,
                   metric => atom_to_binary(Metric, utf8),
                   min_matches => MinMatches,
                   teams => length(Ranked),
                   returned => min(Limit, length(Ranked)),
                   rankings => lists:sublist(Ranked, Limit)}}
    end.

enrich(#{played := P, wins := W, points := Pts} = Row) ->
    Row#{win_rate => pct(W, P),
         points_per_game => case P of
                                0 -> 0.0;
                                _ -> round2(Pts / P)
                            end}.

metric_opt(Opts) ->
    case br_text:normalize(opt(metric, Opts, <<"points">>)) of
        <<"wins">> -> wins;
        <<"win rate">> -> win_rate;
        <<"win_rate">> -> win_rate;
        <<"goals">> -> goals_for;
        <<"goals for">> -> goals_for;
        <<"goals against">> -> goals_against;
        <<"defence">> -> goals_against;
        <<"goal difference">> -> goal_difference;
        <<"points per game">> -> points_per_game;
        _ -> points
    end.

ascending_metric(goals_against) -> true;
ascending_metric(_) -> false.

default_min_matches(win_rate) -> 10;
default_min_matches(points_per_game) -> 10;
default_min_matches(goals_against) -> 10;
default_min_matches(_) -> 1.

%% @doc Aggregate statistics for a competition (optionally one season).
-spec competition_stats(map()) -> {ok, map()} | {error, map()}.
competition_stats(Opts) ->
    Comp = competition_opt(Opts),
    Season = season_opt(Opts),
    Matches = [M || M <- br_store:fold_matches(fun(M, A) -> [M | A] end, []),
                    (Comp =:= undefined orelse M#match.competition =:= Comp),
                    (Season =:= undefined orelse M#match.season =:= Season),
                    has_score(M)],
    case Matches of
        [] -> {error, error_map(no_data, <<"no matches for that filter">>, [])};
        _ ->
            Total = length(Matches),
            Goals = lists:sum([HG + AG || #match{home_goals = HG, away_goals = AG} <- Matches]),
            HomeGoals = lists:sum([HG || #match{home_goals = HG} <- Matches]),
            AwayGoals = lists:sum([AG || #match{away_goals = AG} <- Matches]),
            HomeWins = length([1 || #match{home_goals = H, away_goals = A} <- Matches, H > A]),
            AwayWins = length([1 || #match{home_goals = H, away_goals = A} <- Matches, H < A]),
            Draws = Total - HomeWins - AwayWins,
            Table = build_table(Matches),
            Biggest = hd(lists:sort(fun(A, B) -> margin_key(A) >= margin_key(B) end, Matches)),
            {ok, #{competition => null_if_undefined(Comp),
                   competition_name => comp_name_or_null(Comp),
                   season => null_if_undefined(Season),
                   seasons_covered => lists:usort([S || #match{season = S} <- Matches,
                                                        S =/= undefined]),
                   matches => Total,
                   goals => Goals,
                   goals_per_match => round2(Goals / Total),
                   home_goals => HomeGoals,
                   away_goals => AwayGoals,
                   home_wins => HomeWins,
                   away_wins => AwayWins,
                   draws => Draws,
                   home_win_rate => pct(HomeWins, Total),
                   away_win_rate => pct(AwayWins, Total),
                   draw_rate => pct(Draws, Total),
                   biggest_win => match_map(Biggest),
                   top_scoring_teams =>
                       lists:sublist(lists:sort(fun(#{goals_for := A}, #{goals_for := B}) ->
                                                        A >= B
                                                end, Table), 5),
                   best_attack => best_by(goals_for, Table, fun erlang:'>='/2),
                   best_defence => best_by(goals_against, Table, fun erlang:'=<'/2)}}
    end.

best_by(Key, Table, Cmp) ->
    case lists:sort(fun(A, B) -> Cmp(maps:get(Key, A), maps:get(Key, B)) end, Table) of
        [Best | _] -> Best;
        [] -> null
    end.

%% @doc Side-by-side comparison of two seasons of one competition.
-spec compare_seasons(map()) -> {ok, map()} | {error, map()}.
compare_seasons(Opts) ->
    Comp = competition_opt(Opts, <<"brasileirao_serie_a">>),
    A = to_int(opt(season_a, Opts, undefined)),
    B = to_int(opt(season_b, Opts, undefined)),
    case {A, B} of
        {undefined, _} -> {error, error_map(missing_season, <<"season_a is required">>, [])};
        {_, undefined} -> {error, error_map(missing_season, <<"season_b is required">>, [])};
        _ ->
            case {competition_stats(#{competition => Comp, season => A}),
                  competition_stats(#{competition => Comp, season => B})} of
                {{ok, SA}, {ok, SB}} ->
                    Keys = [matches, goals, goals_per_match, home_win_rate, draw_rate,
                            away_win_rate],
                    {ok, #{competition => Comp,
                           competition_name => br_names:competition_display(Comp),
                           season_a => SA, season_b => SB,
                           deltas => maps:from_list(
                                       [{K, round2(maps:get(K, SB) - maps:get(K, SA))}
                                        || K <- Keys])}};
                {{error, E}, _} -> {error, E};
                {_, {error, E}} -> {error, E}
            end
    end.

%% @doc The traditional derbies, optionally for one season.
-spec derbies(map()) -> {ok, map()} | {error, map()}.
derbies(Opts) ->
    Season = season_opt(Opts),
    Comp = competition_opt(Opts),
    Results =
        lists:filtermap(
          fun({Name, A, B}) ->
                  Matches = [M || M <- br_store:team_matches(A), involves(M, B),
                                  (Season =:= undefined orelse M#match.season =:= Season),
                                  (Comp =:= undefined orelse M#match.competition =:= Comp)],
                  case Matches of
                      [] -> false;
                      _ ->
                          Sorted = sort_matches(Matches, <<"date_desc">>),
                          {true, #{derby => Name,
                                   team_a => team_ref(A), team_b => team_ref(B),
                                   matches => length(Sorted),
                                   fixtures => [match_map(M) || M <- lists:sublist(Sorted, 10)]}}
                  end
          end, br_names:rivalries()),
    {ok, #{season => null_if_undefined(Season),
           competition => null_if_undefined(Comp),
           derbies => Results,
           total => lists:sum([N || #{matches := N} <- Results])}}.

-spec list_competitions(map()) -> {ok, map()}.
list_competitions(_Opts) ->
    {ok, #{competitions =>
               [#{competition => C,
                  name => br_names:competition_display(C),
                  seasons => br_store:seasons_of(C),
                  matches => length([1 || M <- br_store:all_matches(),
                                          M#match.competition =:= C])}
                || C <- br_store:competitions()]}}.

%% @doc What is loaded: files, counts, coverage.
-spec dataset_summary(map()) -> {ok, map()}.
dataset_summary(_Opts) ->
    Stats = br_store:stats(),
    {ok, Comps} = list_competitions(#{}),
    {ok, maps:merge(Stats, #{competitions => maps:get(competitions, Comps),
                             files => [list_to_binary(F)
                                       || {_, F} <- br_loader:data_files()],
                             seasons => br_store:seasons()})}.

%%====================================================================
%% Players
%%====================================================================

%% @doc Search the FIFA player data.
-spec search_players(map()) -> {ok, map()} | {error, map()}.
search_players(Opts) ->
    Name = norm_opt(name, Opts),
    Nationality = norm_opt(nationality, Opts),
    Club = norm_opt(club, Opts),
    Position = case opt(position, Opts, undefined) of
                   undefined -> undefined;
                   P -> br_text:normalize(P)
               end,
    MinOverall = to_int(opt(min_overall, Opts, undefined)),
    MaxAge = to_int(opt(max_age, Opts, undefined)),
    MinAge = to_int(opt(min_age, Opts, undefined)),
    Players = br_store:fold_players(
                fun(P, Acc) ->
                        case player_filter(P, Name, Nationality, Club, Position,
                                           MinOverall, MinAge, MaxAge) of
                            true -> [P | Acc];
                            false -> Acc
                        end
                end, []),
    Sorted = sort_players(Players, opt(sort, Opts, <<"overall_desc">>)),
    Limit = limit(Opts),
    {ok, #{total => length(Sorted),
           returned => min(Limit, length(Sorted)),
           note => empty_player_note(Sorted, opt(club, Opts, undefined)),
           filters => #{name => null_if_undefined(opt(name, Opts, undefined)),
                        nationality => null_if_undefined(opt(nationality, Opts, undefined)),
                        club => null_if_undefined(opt(club, Opts, undefined)),
                        position => null_if_undefined(opt(position, Opts, undefined)),
                        min_overall => null_if_undefined(MinOverall)},
           players => [player_summary(P) || P <- lists:sublist(Sorted, Limit)]}}.

%% A club that has matches but no players is the normal case for the
%% Brazilian clubs FIFA 19 did not license; say so rather than returning
%% an unexplained empty list.
empty_player_note([], undefined) -> null;
empty_player_note([], Club) ->
    case br_store:resolve_team(Club) of
        {ok, Id} ->
            case br_store:team(Id) of
                {ok, #team{name = Name, match_count = N}} when N > 0 ->
                    <<Name/binary, " has ", (integer_to_binary(N))/binary,
                      " matches in the match data but no squad in fifa_data.csv "
                      "(FIFA 19 did not license every Brazilian club).">>;
                _ -> null
            end;
        {error, _} -> null
    end;
empty_player_note(_, _) -> null.

player_filter(#player{} = P, Name, Nat, Club, Pos, MinOverall, MinAge, MaxAge) ->
    matches_norm(P#player.norm_name, Name)
        andalso matches_norm(P#player.nationality, Nat)
        andalso matches_norm(P#player.club, Club)
        andalso position_filter(P#player.position, Pos)
        andalso (MinOverall =:= undefined orelse
                 (is_integer(P#player.overall) andalso P#player.overall >= MinOverall))
        andalso (MinAge =:= undefined orelse
                 (is_integer(P#player.age) andalso P#player.age >= MinAge))
        andalso (MaxAge =:= undefined orelse
                 (is_integer(P#player.age) andalso P#player.age =< MaxAge)).

matches_norm(_Value, undefined) -> true;
matches_norm(undefined, _Query) -> false;
matches_norm(Value, Query) ->
    binary:match(br_text:normalize(Value), Query) =/= nomatch.

%% "forward"/"defender"/"midfielder"/"goalkeeper" expand to FIFA codes.
position_filter(_Value, undefined) -> true;
position_filter(undefined, _Query) -> false;
position_filter(Value, Query) ->
    V = br_text:normalize(Value),
    case position_group(Query) of
        undefined -> V =:= Query orelse binary:match(V, Query) =/= nomatch;
        Codes -> lists:member(V, Codes)
    end.

position_group(<<"forward">>) -> [<<"st">>, <<"cf">>, <<"lw">>, <<"rw">>, <<"ls">>,
                                  <<"rs">>, <<"lf">>, <<"rf">>];
position_group(<<"forwards">>) -> position_group(<<"forward">>);
position_group(<<"striker">>) -> [<<"st">>, <<"ls">>, <<"rs">>, <<"cf">>];
position_group(<<"winger">>) -> [<<"lw">>, <<"rw">>, <<"lm">>, <<"rm">>];
position_group(<<"midfielder">>) -> [<<"cm">>, <<"cdm">>, <<"cam">>, <<"lm">>, <<"rm">>,
                                     <<"lcm">>, <<"rcm">>, <<"ldm">>, <<"rdm">>,
                                     <<"lam">>, <<"ram">>];
position_group(<<"midfield">>) -> position_group(<<"midfielder">>);
position_group(<<"defender">>) -> [<<"cb">>, <<"lb">>, <<"rb">>, <<"lcb">>, <<"rcb">>,
                                   <<"lwb">>, <<"rwb">>];
position_group(<<"defence">>) -> position_group(<<"defender">>);
position_group(<<"goalkeeper">>) -> [<<"gk">>];
position_group(<<"keeper">>) -> [<<"gk">>];
position_group(_) -> undefined.

sort_players(Players, Sort) ->
    Key = fun(#player{overall = O, potential = Pot, age = A, name = N}) ->
                  case to_bin(Sort) of
                      <<"overall_desc">> -> {nz(O), nz(Pot)};
                      <<"potential_desc">> -> {nz(Pot), nz(O)};
                      <<"age_asc">> -> {-nz(A), nz(O)};
                      <<"age_desc">> -> {nz(A), nz(O)};
                      <<"name">> -> {neg_name(N)};
                      _ -> {nz(O), nz(Pot)}
                  end
          end,
    lists:sort(fun(A, B) -> Key(A) >= Key(B) end, Players).

neg_name(N) -> [-C || C <- binary_to_list(br_text:normalize(N))].

nz(undefined) -> 0;
nz(N) -> N.

%% @doc Full profile of one player (by name or FIFA id).
-spec player_profile(map()) -> {ok, map()} | {error, map()}.
player_profile(Opts) ->
    case to_int(opt(player_id, Opts, undefined)) of
        undefined ->
            case opt(name, Opts, undefined) of
                undefined ->
                    {error, error_map(missing_argument, <<"name or player_id required">>, [])};
                Name -> profile_by_name(Name)
            end;
        Id ->
            case br_store:player(Id) of
                {ok, P} -> {ok, player_detail(P)};
                error -> {error, error_map(unknown_player,
                                           <<"no player with that id">>, [])}
            end
    end.

profile_by_name(Name) ->
    Norm = br_text:normalize(Name),
    Candidates = br_store:fold_players(
                   fun(P, Acc) ->
                           case binary:match(P#player.norm_name, Norm) of
                               nomatch -> Acc;
                               _ -> [P | Acc]
                           end
                   end, []),
    case sort_players(Candidates, <<"overall_desc">>) of
        [] ->
            %% Suggest players who share a name part rather than
            %% silently answering about someone else.
            Similar = [N || #player{name = N} <- lists:sublist(similar_players(Norm), 5)],
            {error, error_map(unknown_player,
                              <<"no player matching \"", (to_bin(Name))/binary,
                                "\" in fifa_data.csv">>, Similar)};
        [Best | Rest] ->
            Detail = player_detail(Best),
            {ok, Detail#{other_matches => [player_summary(P) || P <- lists:sublist(Rest, 5)]}}
    end.

%% Players matching any single word of the query, best rated first.
similar_players(Norm) ->
    Tokens = [T || T <- binary:split(Norm, <<" ">>, [global]), byte_size(T) > 2],
    case Tokens of
        [] -> [];
        _ ->
            Found = br_store:fold_players(
                      fun(P, Acc) ->
                              case lists:any(fun(T) ->
                                                     binary:match(P#player.norm_name, T)
                                                         =/= nomatch
                                             end, Tokens) of
                                  true -> [P | Acc];
                                  false -> Acc
                              end
                      end, []),
            sort_players(Found, <<"overall_desc">>)
    end.

player_detail(#player{} = P) ->
    Club = P#player.club_id,
    ClubInfo = case Club of
                   undefined -> null;
                   _ ->
                       case br_store:team(Club) of
                           {ok, T} -> #{team => T#team.id, team_name => T#team.name,
                                        matches_in_dataset => T#team.match_count,
                                        competitions => T#team.competitions};
                           error -> null
                       end
               end,
    maps:merge(player_summary(P),
               #{potential => null_if_undefined(P#player.potential),
                 height => null_if_undefined(P#player.height),
                 weight => null_if_undefined(P#player.weight),
                 value => null_if_undefined(P#player.value),
                 wage => null_if_undefined(P#player.wage),
                 preferred_foot => null_if_undefined(P#player.foot),
                 jersey_number => null_if_undefined(P#player.jersey),
                 club_in_match_data => ClubInfo,
                 skills => P#player.skills,
                 top_skills => top_skills(P#player.skills)}).

top_skills(Skills) ->
    Sorted = lists:sort(fun({_, A}, {_, B}) -> A >= B end, maps:to_list(Skills)),
    [#{skill => K, value => V} || {K, V} <- lists:sublist(Sorted, 6)].

player_summary(#player{} = P) ->
    #{player_id => P#player.id,
      name => P#player.name,
      age => null_if_undefined(P#player.age),
      nationality => null_if_undefined(P#player.nationality),
      overall => null_if_undefined(P#player.overall),
      potential => null_if_undefined(P#player.potential),
      club => null_if_undefined(P#player.club),
      club_id => null_if_undefined(P#player.club_id),
      position => null_if_undefined(P#player.position)}.

%% @doc Squad of a club from the FIFA data, joined to its match record.
-spec club_squad(map()) -> {ok, map()} | {error, map()}.
club_squad(Opts) ->
    case opt(club, Opts, opt(team, Opts, undefined)) of
        undefined -> {error, error_map(missing_argument, <<"club is required">>, [])};
        Club ->
            ClubId = case br_store:resolve_team(Club) of
                         {ok, Id} -> Id;
                         {error, _} -> br_names:canonical_id(Club)
                     end,
            Squad0 = br_store:players_of_club(ClubId),
            Squad = case Squad0 of
                        [] -> players_by_club_name(Club);
                        _ -> Squad0
                    end,
            Sorted = sort_players(Squad, <<"overall_desc">>),
            Ratings = [O || #player{overall = O} <- Sorted, is_integer(O)],
            Limit = limit(Opts, 40),
            {ok, #{club => ClubId,
                   club_name => team_name(ClubId),
                   squad_size => length(Sorted),
                   average_overall => case Ratings of
                                          [] -> null;
                                          _ -> round2(lists:sum(Ratings) / length(Ratings))
                                      end,
                   note => squad_note(Sorted),
                   players => [player_summary(P) || P <- lists:sublist(Sorted, Limit)]}}
    end.

players_by_club_name(Club) ->
    Norm = br_text:normalize(Club),
    br_store:fold_players(
      fun(P, Acc) ->
              case matches_norm(P#player.club, Norm) of
                  true -> [P | Acc];
                  false -> Acc
              end
      end, []).

%% @doc Group players by club: how many, how good - e.g. "Brazilian
%% players at Brazilian clubs".
-spec player_club_summary(map()) -> {ok, map()}.
player_club_summary(Opts) ->
    Nationality = norm_opt(nationality, Opts),
    OnlyDataset = boolean_opt(only_clubs_in_match_data, Opts, false),
    Players = br_store:fold_players(
                fun(P, Acc) ->
                        case matches_norm(P#player.nationality, Nationality)
                            andalso P#player.club_id =/= undefined
                            andalso (not OnlyDataset
                                     orelse br_store:team(P#player.club_id) =/= error) of
                            true -> [P | Acc];
                            false -> Acc
                        end
                end, []),
    Groups = group_by(fun(#player{club_id = C}) -> C end, Players),
    Rows = [begin
                Ratings = [O || #player{overall = O} <- Ps, is_integer(O)],
                #{club => C,
                  club_name => team_name(C),
                  players => length(Ps),
                  average_overall => case Ratings of
                                         [] -> null;
                                         _ -> round2(lists:sum(Ratings) / length(Ratings))
                                     end,
                  best => player_summary(hd(sort_players(Ps, <<"overall_desc">>)))}
            end || {C, Ps} <- Groups],
    Sorted = lists:sort(fun(#{players := A}, #{players := B}) -> A >= B end, Rows),
    Limit = limit(Opts, 25),
    {ok, #{total_players => length(Players),
           clubs => length(Rows),
           nationality => null_if_undefined(opt(nationality, Opts, undefined)),
           returned => min(Limit, length(Sorted)),
           by_club => lists:sublist(Sorted, Limit)}}.

top_players(Players, N) ->
    lists:sublist(sort_players(Players, <<"overall_desc">>), N).

%%====================================================================
%% Graph
%%====================================================================

%% @doc Neighbours of a node in the knowledge graph.
-spec graph_neighbors(map()) -> {ok, map()} | {error, map()}.
graph_neighbors(Opts) ->
    case node_opt(Opts) of
        {error, E} -> {error, E};
        {ok, NodeId} ->
            {ok, Node} = br_graph:get_node(NodeId),
            Rel = case opt(relation, Opts, undefined) of
                      undefined -> undefined;
                      R -> binary_to_atom(to_bin(R), utf8)
                  end,
            Neighbours0 = br_graph:neighbours(NodeId),
            Neighbours = [N || {R, _, _} = N <- Neighbours0,
                               Rel =:= undefined orelse R =:= Rel],
            Limit = limit(Opts, 50),
            {ok, #{node => node_map(Node),
                   degree => br_graph:degree(NodeId),
                   total => length(Neighbours),
                   returned => min(Limit, length(Neighbours)),
                   neighbours =>
                       [begin
                            {ok, N} = br_graph:get_node(Id),
                            #{relation => R, direction => Dir, node => node_map(N)}
                        end || {R, Id, Dir} <- lists:sublist(Neighbours, Limit)]}}
    end.

%% @doc Shortest path between two nodes, e.g. player -> club -> match -> club.
-spec graph_path(map()) -> {ok, map()} | {error, map()}.
graph_path(Opts) ->
    case {node_opt(from, Opts), node_opt(to, Opts)} of
        {{error, E}, _} -> {error, E};
        {_, {error, E}} -> {error, E};
        {{ok, From}, {ok, To}} ->
            MaxDepth = case to_int(opt(max_depth, Opts, 6)) of
                           undefined -> 6;
                           D -> min(D, 8)
                       end,
            case br_graph:path(From, To, MaxDepth) of
                not_found ->
                    {ok, #{from => From, to => To, found => false, path => []}};
                {ok, Steps} ->
                    {ok, #{from => From, to => To, found => true,
                           length => length(Steps) - 1,
                           path => [begin
                                        {ok, N} = br_graph:get_node(Id),
                                        #{relation => Rel, node => node_map(N)}
                                    end || {Rel, Id} <- Steps]}}
            end
    end.

node_map(#{id := Id, type := Type, label := Label, props := Props}) ->
    #{id => Id, type => Type, label => Label, properties => nullify(Props)}.

nullify(Map) ->
    maps:map(fun(_, undefined) -> null; (_, V) -> V end, Map).

node_opt(Opts) -> node_opt(node, Opts).

node_opt(Key, Opts) ->
    case opt(Key, Opts, undefined) of
        undefined ->
            %% Allow node references by kind + name, e.g. type=team, name=Santos.
            case {opt(type, Opts, undefined), opt(name, Opts, undefined)} of
                {undefined, _} ->
                    {error, error_map(missing_argument,
                                      <<"a node id such as \"team:santos\" is required">>, [])};
                {Type, Name} -> resolve_node(to_bin(Type), Name)
            end;
        Raw ->
            Id = to_bin(Raw),
            case br_graph:has_node(Id) of
                true -> {ok, Id};
                false ->
                    case binary:split(Id, <<":">>) of
                        [Type, Name] -> resolve_node(Type, Name);
                        _ -> {error, error_map(unknown_node,
                                               <<"no node ", Id/binary>>, [])}
                    end
            end
    end.

resolve_node(<<"team">>, Name) ->
    case br_store:resolve_team(Name) of
        {ok, Id} -> {ok, br_graph:id(team, Id)};
        {error, _} -> {error, error_map(unknown_node, <<"unknown team">>, [])}
    end;
resolve_node(<<"competition">>, Name) ->
    case br_names:competition(Name) of
        undefined -> {error, error_map(unknown_node, <<"unknown competition">>, [])};
        C -> {ok, br_graph:id(competition, C)}
    end;
resolve_node(Type, Name) ->
    Id = br_graph:id(binary_to_atom(Type, utf8), br_text:to_binary(Name)),
    case br_graph:has_node(Id) of
        true -> {ok, Id};
        false -> {error, error_map(unknown_node, <<"no node ", Id/binary>>, [])}
    end.

%%====================================================================
%% Shared helpers
%%====================================================================

%% @doc Resolve a team option, reporting suggestions when it is unknown.
-spec resolve_team(term(), map()) -> {ok, binary()} | {error, map()}.
resolve_team(Value, _Opts) ->
    case br_store:resolve_team(Value) of
        {ok, Id} -> {ok, Id};
        {error, {unknown_team, Query, _}} ->
            Suggestions = [N || #team{name = N} <- lists:sublist(suggest(Query), 5)],
            {error, error_map(unknown_team,
                              <<"unknown team \"", Query/binary, "\"">>, Suggestions)}
    end.

suggest(Query) ->
    case br_text:tokens(Query) of
        [] -> [];
        [First | _] -> br_store:search_teams(First)
    end.

%% Resolve every team option present in Opts, then run Fun.
with_teams(Specs, Opts, Fun) ->
    Result = lists:foldl(
               fun(_, {error, _} = E) -> E;
                  ({OptKey, MapKey}, Acc) ->
                       case opt(OptKey, Opts, undefined) of
                           undefined -> Acc;
                           Value ->
                               case resolve_team(Value, Opts) of
                                   {ok, Id} -> Acc#{MapKey => Id};
                                   {error, E} -> {error, E}
                               end
                       end
               end, #{}, Specs),
    case Result of
        {error, E} -> {error, E};
        Teams -> Fun(Teams)
    end.

candidate_matches(Teams) ->
    case first_team(Teams) of
        undefined -> br_store:fold_matches(fun(M, A) -> [M | A] end, []);
        Id -> br_store:team_matches(Id)
    end.

first_team(Teams) ->
    case [Id || Key <- [team, home_team, away_team, opponent],
                Id <- [maps:get(Key, Teams, undefined)], Id =/= undefined] of
        [Id | _] -> Id;
        [] -> undefined
    end.

match_filter(#match{} = M, Teams, Comp, Opts) ->
    team_ok(M, Teams)
        andalso (Comp =:= undefined orelse M#match.competition =:= Comp)
        andalso season_ok(M, Opts)
        andalso date_ok(M, Opts).

team_ok(M, Teams) ->
    lists:all(fun({Key, Check}) ->
                      case maps:get(Key, Teams, undefined) of
                          undefined -> true;
                          Id -> Check(M, Id)
                      end
              end,
              [{team, fun(Match, Id) -> involves(Match, Id) end},
               {opponent, fun(Match, Id) -> involves(Match, Id) end},
               {home_team, fun(#match{home = H}, Id) -> H =:= Id end},
               {away_team, fun(#match{away = A}, Id) -> A =:= Id end}]).

season_ok(#match{season = S}, Opts) ->
    case season_opt(Opts) of
        undefined ->
            From = to_int(opt(season_from, Opts, undefined)),
            To = to_int(opt(season_to, Opts, undefined)),
            (From =:= undefined orelse (is_integer(S) andalso S >= From))
                andalso (To =:= undefined orelse (is_integer(S) andalso S =< To));
        Season -> S =:= Season
    end.

date_ok(#match{date = D}, Opts) ->
    From = date_opt(date_from, Opts),
    To = date_opt(date_to, Opts),
    case {From, To} of
        {undefined, undefined} -> true;
        _ -> br_date:in_range(D, From, To)
    end.

date_opt(Key, Opts) ->
    case opt(Key, Opts, undefined) of
        undefined -> undefined;
        V ->
            case br_date:parse_date(V) of
                {ok, D} -> D;
                error -> undefined
            end
    end.

involves(#match{home = H, away = A}, Id) -> H =:= Id orelse A =:= Id.

has_score(#match{home_goals = H, away_goals = A}) ->
    is_integer(H) andalso is_integer(A).

won(Id, #match{home = H, home_goals = HG, away_goals = AG}) ->
    case H =:= Id of
        true -> HG > AG;
        false -> AG > HG
    end.

team_margin(Id, #match{home = H, home_goals = HG, away_goals = AG} = M) ->
    Margin = case H =:= Id of
                 true -> HG - AG;
                 false -> AG - HG
             end,
    {Margin, HG + AG, br_date:to_days(M#match.date)}.

venue_match(_M, _Id, <<"any">>) -> true;
venue_match(#match{home = H}, Id, <<"home">>) -> H =:= Id;
venue_match(#match{away = A}, Id, <<"away">>) -> A =:= Id;
venue_match(_, _, _) -> true.

venue_opt(Opts) ->
    case br_text:normalize(opt(venue, Opts, <<"any">>)) of
        <<"home">> -> <<"home">>;
        <<"away">> -> <<"away">>;
        _ -> <<"any">>
    end.

record_of(Id, Matches) ->
    {W, D, L, GF, GA} =
        lists:foldl(
          fun(#match{home = H, home_goals = HG, away_goals = AG}, {Wa, Da, La, F, A}) ->
                  {Own, Opp} = case H =:= Id of
                                   true -> {HG, AG};
                                   false -> {AG, HG}
                               end,
                  case {Own > Opp, Own < Opp} of
                      {true, _} -> {Wa + 1, Da, La, F + Own, A + Opp};
                      {_, true} -> {Wa, Da, La + 1, F + Own, A + Opp};
                      _ -> {Wa, Da + 1, La, F + Own, A + Opp}
                  end
          end, {0, 0, 0, 0, 0}, Matches),
    Played = W + D + L,
    #{played => Played, wins => W, draws => D, losses => L,
      goals_for => GF, goals_against => GA, goal_difference => GF - GA,
      points => W * 3 + D,
      win_rate => pct(W, Played),
      points_per_game => case Played of
                             0 -> 0.0;
                             _ -> round2((W * 3 + D) / Played)
                         end}.

sort_matches(Matches, Sort) ->
    case to_bin(Sort) of
        <<"date_asc">> ->
            lists:sort(fun(A, B) -> sort_key(A) =< sort_key(B) end, Matches);
        <<"goals_desc">> ->
            lists:sort(fun(A, B) -> goals_of(A) >= goals_of(B) end, Matches);
        _ ->
            lists:sort(fun(A, B) -> sort_key(A) >= sort_key(B) end, Matches)
    end.

sort_key(#match{date = D, season = S, round = R}) ->
    {br_date:to_days(D), nz(S), R}.

goals_of(#match{home_goals = H, away_goals = A}) when is_integer(H), is_integer(A) -> H + A;
goals_of(_) -> 0.

first_date(Matches) -> extreme(fun lists:min/1, Matches).

last_date(Matches) -> extreme(fun lists:max/1, Matches).

extreme(Fun, Matches) ->
    case [br_date:to_days(D) || #match{date = D} <- Matches, D =/= undefined] of
        [] -> undefined;
        Days -> Fun(Days)
    end.

date_or_null(undefined) -> null;
date_or_null(Days) when is_integer(Days) ->
    br_date:format(calendar:gregorian_days_to_date(Days));
date_or_null(_) -> null.

group_by(KeyFun, List) ->
    maps:to_list(lists:foldl(fun(X, Acc) ->
                                     K = KeyFun(X),
                                     Acc#{K => [X | maps:get(K, Acc, [])]}
                             end, #{}, List)).

team_name(Id) ->
    case br_store:team(Id) of
        {ok, #team{name = N}} -> N;
        error -> br_names:display(Id)
    end.

team_ref(Id) -> #{team => Id, team_name => team_name(Id)}.

team_or_default(Id) ->
    case br_store:team(Id) of
        {ok, T} -> {ok, T};
        error -> {ok, #team{id = Id, name = br_names:display(Id)}}
    end.

describe_query(Teams, Comp, Opts) ->
    #{team => null_if_undefined(maps:get(team, Teams, undefined)),
      opponent => null_if_undefined(maps:get(opponent, Teams, undefined)),
      home_team => null_if_undefined(maps:get(home_team, Teams, undefined)),
      away_team => null_if_undefined(maps:get(away_team, Teams, undefined)),
      competition => null_if_undefined(Comp),
      season => null_if_undefined(season_opt(Opts))}.

%% @doc Render a match as a plain map (used for JSON and by br_format).
-spec match_map(#match{}) -> map().
match_map(#match{} = M) ->
    #{id => M#match.id,
      competition => M#match.competition,
      competition_name => br_names:competition_display(M#match.competition),
      season => null_if_undefined(M#match.season),
      date => date_bin(M#match.date),
      time => time_bin(M#match.time),
      round => null_if_undefined(M#match.round),
      stage => null_if_undefined(M#match.stage),
      home => M#match.home,
      home_name => team_name(M#match.home),
      away => M#match.away,
      away_name => team_name(M#match.away),
      home_goals => null_if_undefined(M#match.home_goals),
      away_goals => null_if_undefined(M#match.away_goals),
      score => score_bin(M),
      result => result_of(M),
      venue => null_if_undefined(M#match.venue),
      sources => [atom_to_binary(S, utf8) || S <- M#match.sources],
      statistics => M#match.stats}.

score_bin(#match{home_goals = H, away_goals = A}) when is_integer(H), is_integer(A) ->
    <<(integer_to_binary(H))/binary, "-", (integer_to_binary(A))/binary>>;
score_bin(_) -> null.

result_of(#match{home_goals = H, away_goals = A}) when is_integer(H), is_integer(A) ->
    if H > A -> <<"home_win">>;
       H < A -> <<"away_win">>;
       true -> <<"draw">>
    end;
result_of(_) -> null.

date_bin(undefined) -> null;
date_bin(D) -> br_date:format(D).

time_bin(undefined) -> null;
time_bin({H, M, S}) ->
    iolist_to_binary(io_lib:format("~2..0b:~2..0b:~2..0b", [H, M, S])).

%%--------------------------------------------------------------------
%% Option access: accepts atom or binary keys.
%%--------------------------------------------------------------------

-spec opt(atom(), map(), term()) -> term().
opt(Key, Opts, Default) when is_map(Opts) ->
    case maps:find(Key, Opts) of
        {ok, V} -> nonempty(V, Default);
        error ->
            case maps:find(atom_to_binary(Key, utf8), Opts) of
                {ok, V} -> nonempty(V, Default);
                error -> Default
            end
    end;
opt(_Key, _Opts, Default) -> Default.

nonempty(null, Default) -> Default;
nonempty(undefined, Default) -> Default;
nonempty(<<>>, Default) -> Default;
nonempty("", Default) -> Default;
nonempty(V, _Default) -> V.

norm_opt(Key, Opts) ->
    case opt(Key, Opts, undefined) of
        undefined -> undefined;
        V -> br_text:normalize(V)
    end.

boolean_opt(Key, Opts, Default) ->
    case opt(Key, Opts, Default) of
        true -> true;
        false -> false;
        <<"true">> -> true;
        <<"false">> -> false;
        _ -> Default
    end.

season_opt(Opts) -> to_int(opt(season, Opts, undefined)).

competition_opt(Opts) -> competition_opt(Opts, undefined).

competition_opt(Opts, Default) ->
    case opt(competition, Opts, undefined) of
        undefined -> Default;
        V ->
            case br_names:competition(V) of
                undefined -> Default;
                C -> C
            end
    end.

limit(Opts) -> limit(Opts, ?DEFAULT_LIMIT).

limit(Opts, Default) ->
    case to_int(opt(limit, Opts, Default)) of
        undefined -> Default;
        N when N < 1 -> Default;
        N -> min(N, ?MAX_LIMIT)
    end.

to_int(undefined) -> undefined;
to_int(null) -> undefined;
to_int(N) when is_integer(N) -> N;
to_int(F) when is_float(F) -> round(F);
to_int(B) when is_binary(B) ->
    try binary_to_integer(string:trim(B))
    catch error:badarg -> undefined
    end;
to_int(L) when is_list(L) -> to_int(list_to_binary(L));
to_int(_) -> undefined.

to_bin(V) -> br_text:to_binary(V).

pct(_, 0) -> 0.0;
pct(N, Total) -> round2(N * 100 / Total).

round2(F) when is_float(F) -> round(F * 100) / 100;
round2(N) -> N.

null_if_undefined(undefined) -> null;
null_if_undefined(V) -> V.

comp_name_or_null(undefined) -> null;
comp_name_or_null(C) -> br_names:competition_display(C).

error_map(Code, Message, Suggestions) ->
    #{code => Code, message => Message, suggestions => Suggestions}.
