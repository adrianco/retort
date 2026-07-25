%%%-------------------------------------------------------------------
%%% @doc Query and analytics layer over the knowledge graph.
%%%
%%% Context: every function here is pure with respect to ETS (read
%%% only), takes an options map with binary/atom keys already decoded by
%%% {@link bsmcp_tools} and returns plain maps that both the JSON
%%% encoder and the text formatter can consume.  Unresolvable team or
%%% competition names come back as `{error, Map}' with suggestions,
%%% which is what lets the LLM recover from "Fla" or "Atletico".
%%%
%%% Candidate sets are taken from the ETS indexes first (team ->
%%% matches, {competition, season} -> matches) and only then filtered,
%%% so even the heaviest aggregate touches a few thousand records.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_query).

-export([search_matches/1, head_to_head/1, team_stats/1, team_profile/1,
         standings/1, leaderboard/1, biggest_wins/1, competition_stats/1,
         search_players/1, player_profile/1, club_squad/1, club_ratings/1,
         list_teams/1, dataset_summary/0,
         competition_key/1, resolve_team_or_error/1, match_view/1,
         record_new/0, add_match_to_record/3, finalise_record/1]).

-define(DEFAULT_LIMIT, 20).
-define(MAX_LIMIT, 500).

%%====================================================================
%% Matches
%%====================================================================

%% @doc Filtered match list. See {@link bsmcp_tools} for the accepted keys.
search_matches(Opts) ->
    with_filters(Opts,
      fun(Filters) ->
              Matches = filtered_matches(Filters),
              Limit = limit(Opts),
              Sorted = sort_matches(Matches, maps:get(order, Opts, date_desc)),
              #{total => length(Sorted),
                returned => min(Limit, length(Sorted)),
                filters => describe_filters(Filters),
                matches => [match_view(M) || M <- lists:sublist(Sorted, Limit)]}
      end).

%% @doc Complete head-to-head record between two teams.
head_to_head(Opts) ->
    TeamA = maps:get(team_a, Opts, undefined),
    TeamB = maps:get(team_b, Opts, undefined),
    case {resolve_team_or_error(TeamA), resolve_team_or_error(TeamB)} of
        {{error, E}, _} -> {error, E};
        {_, {error, E}} -> {error, E};
        {{ok, A}, {ok, B}} ->
            with_filters(Opts#{team => undefined, opponent => undefined},
              fun(Filters0) ->
                      Filters = Filters0#{team_id => maps:get(id, A),
                                          opponent_id => maps:get(id, B)},
                      Matches = sort_matches(filtered_matches(Filters), date_desc),
                      Played = [M || M <- Matches, maps:get(played, M)],
                      {WinsA, WinsB, Draws} = tally(maps:get(id, A), Played),
                      {GoalsA, GoalsB} = goals(maps:get(id, A), Played),
                      Limit = limit(Opts),
                      #{team_a => team_view(A),
                        team_b => team_view(B),
                        filters => describe_filters(Filters),
                        summary => #{matches => length(Matches),
                                     played => length(Played),
                                     team_a_wins => WinsA,
                                     team_b_wins => WinsB,
                                     draws => Draws,
                                     team_a_goals => GoalsA,
                                     team_b_goals => GoalsB},
                        by_competition => h2h_by_competition(maps:get(id, A), Played),
                        matches => [match_view(M) || M <- lists:sublist(Matches, Limit)]}
              end)
    end.

h2h_by_competition(TeamId, Matches) ->
    Grouped = group_by(fun(#{competition := C}) -> C end, Matches),
    [begin
         {W, L, D} = tally(TeamId, Ms),
         #{competition => C,
           competition_name => bsmcp_data:competition_name(C),
           matches => length(Ms), wins => W, losses => L, draws => D}
     end || {C, Ms} <- lists:sort(maps:to_list(Grouped))].

tally(TeamId, Matches) ->
    lists:foldl(fun(#{home_team := H, result := R}, {W, L, D}) ->
                        case {R, H =:= TeamId} of
                            {draw, _} -> {W, L, D + 1};
                            {home, true} -> {W + 1, L, D};
                            {home, false} -> {W, L + 1, D};
                            {away, true} -> {W, L + 1, D};
                            {away, false} -> {W + 1, L, D};
                            _ -> {W, L, D}
                        end
                end, {0, 0, 0}, Matches).

goals(TeamId, Matches) ->
    lists:foldl(fun(#{home_team := H, home_goal := HG, away_goal := AG}, {F, A}) ->
                        case H =:= TeamId of
                            true -> {F + HG, A + AG};
                            false -> {F + AG, A + HG}
                        end
                end, {0, 0}, Matches).

%%====================================================================
%% Teams
%%====================================================================

%% @doc Win/draw/loss record with home & away splits.
team_stats(Opts) ->
    case resolve_team_or_error(maps:get(team, Opts, undefined)) of
        {error, E} ->
            {error, E};
        {ok, Team} ->
            TeamId = maps:get(id, Team),
            with_filters(Opts, fun(Filters0) ->
                Filters = Filters0#{team_id => TeamId},
                Matches = [M || M <- filtered_matches(Filters), maps:get(played, M)],
                Record = record_for(TeamId, Matches),
                ByComp = [begin
                              {C, record_for(TeamId, Ms)}
                          end || {C, Ms} <- lists:sort(maps:to_list(
                                              group_by(fun(#{competition := X}) -> X end,
                                                       Matches)))],
                #{team => team_view(Team),
                  filters => describe_filters(Filters),
                  record => Record,
                  by_competition => [#{competition => C,
                                       competition_name => bsmcp_data:competition_name(C),
                                       record => R} || {C, R} <- ByComp]}
            end)
    end.

%% @doc Everything the graph knows about one club.
team_profile(Opts) ->
    case resolve_team_or_error(maps:get(team, Opts, undefined)) of
        {error, E} ->
            {error, E};
        {ok, Team} ->
            TeamId = maps:get(id, Team),
            All = [bsmcp_data:match(Id) || Id <- bsmcp_data:team_match_ids(TeamId)],
            Played = [M || M <- All, maps:get(played, M)],
            Sorted = sort_matches(Played, date_asc),
            ByComp = group_by(fun(#{competition := C}) -> C end, Played),
            Competitions =
                [#{competition => C,
                   competition_name => bsmcp_data:competition_name(C),
                   matches => length(Ms),
                   seasons => lists:usort([S || #{season := S} <- Ms, S =/= undefined]),
                   record => record_for(TeamId, Ms)}
                 || {C, Ms} <- lists:sort(maps:to_list(ByComp))],
            Biggest = biggest_win_for(TeamId, Played),
            Squad = squad_for_team(Team),
            #{team => team_view(Team),
              record => record_for(TeamId, Played),
              competitions => Competitions,
              seasons => lists:usort([S || #{season := S} <- Played, S =/= undefined]),
              first_match => first_or_undefined(Sorted),
              last_match => first_or_undefined(lists:reverse(Sorted)),
              biggest_win => Biggest,
              squad_size => length(Squad),
              top_players => [player_view(P) || P <- lists:sublist(sort_players(Squad, overall), 5)]}
    end.

first_or_undefined([]) -> undefined;
first_or_undefined([M | _]) -> match_view(M).

biggest_win_for(TeamId, Matches) ->
    Wins = [M || M = #{result := R, home_team := H} <- Matches,
                 (R =:= home andalso H =:= TeamId) orelse
                 (R =:= away andalso H =/= TeamId)],
    case lists:sort(fun(A, B) -> margin(A) >= margin(B) end, Wins) of
        [] -> undefined;
        [M | _] -> match_view(M)
    end.

margin(#{home_goal := HG, away_goal := AG}) -> abs(HG - AG).

%% @doc Team lookup / name-variation explorer.
list_teams(Opts) ->
    Query = maps:get(query, Opts, undefined),
    Teams = case Query of
                undefined ->
                    bsmcp_data:teams();
                <<>> ->
                    bsmcp_data:teams();
                _ ->
                    %% best interpretation first, then every club whose name or
                    %% spellings contain the query ("Botafogo" -> RJ, SP, PB)
                    Best = bsmcp_data:resolve_team_all(Query),
                    Ids = [Id || #{id := Id} <- Best],
                    Best ++ [T || T = #{id := Id} <- bsmcp_data:search_teams(Query),
                                  not lists:member(Id, Ids)]
            end,
    Sorted = lists:sort(fun(#{match_count := A}, #{match_count := B}) -> A >= B end, Teams),
    Limit = limit(Opts),
    #{total => length(Sorted),
      teams => [team_view(T, full) || T <- lists:sublist(Sorted, Limit)]}.

%%====================================================================
%% Competitions
%%====================================================================

%% @doc League table computed from the merged match records.
standings(Opts) ->
    case competition_key_or_error(maps:get(competition, Opts, <<"serie a">>)) of
        {error, E} ->
            {error, E};
        {ok, Comp} ->
            case maps:get(season, Opts, undefined) of
                undefined ->
                    {error, #{error => missing_season,
                              message => <<"A season is required, e.g. 2019">>,
                              available_seasons => bsmcp_data:seasons(Comp)}};
                Season ->
                    Ids = bsmcp_data:competition_match_ids(Comp, Season),
                    Matches = [M || Id <- Ids, M <- [bsmcp_data:match(Id)],
                                    maps:get(played, M)],
                    build_table(Comp, Season, Matches)
            end
    end.

build_table(Comp, Season, []) ->
    #{competition => Comp,
      competition_name => bsmcp_data:competition_name(Comp),
      season => Season,
      matches => 0,
      table => [],
      note => <<"No played matches for that competition and season">>,
      available_seasons => bsmcp_data:seasons(Comp)};
build_table(Comp, Season, Matches) ->
    Records = lists:foldl(fun(M, Acc) ->
                                  #{home_team := H, away_team := A} = M,
                                  Acc1 = maps:update_with(H,
                                            fun(R) -> add_match_to_record(R, M, H) end,
                                            add_match_to_record(record_new(), M, H), Acc),
                                  maps:update_with(A,
                                            fun(R) -> add_match_to_record(R, M, A) end,
                                            add_match_to_record(record_new(), M, A), Acc1)
                          end, #{}, Matches),
    Rows = [(finalise_record(Rec))#{team => TeamId, team_name => team_name(TeamId)}
            || {TeamId, Rec} <- maps:to_list(Records)],
    %% A handful of rows in the extended-stats file carry the wrong
    %% tournament label (a state championship tagged "Serie A").  They
    %% show up as clubs with one or two matches in a 38 round league, so
    %% they are reported separately instead of polluting the table.
    MaxPlayed = lists:max([maps:get(played, R) || R <- Rows]),
    {Core, Outliers} = lists:partition(fun(#{played := P}) -> P * 2 >= MaxPlayed end, Rows),
    Sorted = lists:sort(fun table_order/2, Core),
    {Ranked, _} = lists:mapfoldl(fun(R, Pos) -> {R#{position => Pos}, Pos + 1} end, 1, Sorted),
    N = length(Ranked),
    Complete = is_complete_league(Comp, Ranked),
    #{competition => Comp,
      competition_name => bsmcp_data:competition_name(Comp),
      season => Season,
      matches => length(Matches),
      teams => N,
      complete => Complete,
      champion => case {Comp, Ranked, Complete} of
                      {libertadores, _, _} -> undefined;
                      {copa_do_brasil, _, _} -> undefined;
                      {_, [First | _], true} -> maps:get(team_name, First);
                      _ -> undefined
                  end,
      relegated => relegation_zone(Comp, Ranked, Complete),
      excluded_teams => [#{team => maps:get(team_name, R), played => maps:get(played, R)}
                         || R <- Outliers],
      table => Ranked}.

table_order(A, B) ->
    key_of(A) >= key_of(B).

key_of(#{points := P, wins := W, goal_difference := GD, goals_for := GF}) ->
    {P, W, GD, GF}.

%% Only call a table "complete" when every side played a full double
%% round robin; partial imports must not crown a champion.
is_complete_league(Comp, Rows) when Comp =:= serie_a; Comp =:= serie_b; Comp =:= serie_c ->
    N = length(Rows),
    N >= 8 andalso lists:all(fun(#{played := P}) -> P >= 2 * (N - 1) end, Rows);
is_complete_league(_, _) ->
    false.

relegation_zone(Comp, Rows, true) when Comp =:= serie_a; Comp =:= serie_b ->
    N = length(Rows),
    case N >= 16 of
        true -> [maps:get(team_name, R) || R <- lists:nthtail(N - 4, Rows)];
        false -> undefined
    end;
relegation_zone(_, _, _) ->
    undefined.

%% @doc Aggregate competition statistics, optionally split by season.
competition_stats(Opts) ->
    with_filters(Opts, fun(Filters) ->
        Matches = [M || M <- filtered_matches(Filters), maps:get(played, M)],
        BySeason = group_by(fun(#{season := S}) -> S end, Matches),
        #{filters => describe_filters(Filters),
          overall => aggregate_stats(Matches),
          by_season => [#{season => S, stats => aggregate_stats(Ms)}
                        || {S, Ms} <- lists:sort(maps:to_list(BySeason))]}
    end).

aggregate_stats([]) ->
    #{matches => 0};
aggregate_stats(Matches) ->
    N = length(Matches),
    {Home, Away, Draw, Goals, HomeGoals, AwayGoals, Over25, Nil} =
        lists:foldl(fun(#{result := R, home_goal := HG, away_goal := AG},
                        {H, A, D, G, HGs, AGs, O, Z}) ->
                            Total = HG + AG,
                            {case R of home -> H + 1; _ -> H end,
                             case R of away -> A + 1; _ -> A end,
                             case R of draw -> D + 1; _ -> D end,
                             G + Total, HGs + HG, AGs + AG,
                             case Total > 2 of true -> O + 1; false -> O end,
                             case Total =:= 0 of true -> Z + 1; false -> Z end}
                    end, {0, 0, 0, 0, 0, 0, 0, 0}, Matches),
    #{matches => N,
      goals => Goals,
      goals_per_match => bsmcp_text:round2(Goals / N),
      home_goals => HomeGoals,
      away_goals => AwayGoals,
      home_wins => Home,
      away_wins => Away,
      draws => Draw,
      home_win_pct => bsmcp_text:pct(Home, N),
      away_win_pct => bsmcp_text:pct(Away, N),
      draw_pct => bsmcp_text:pct(Draw, N),
      over_2_5_goals_pct => bsmcp_text:pct(Over25, N),
      goalless_pct => bsmcp_text:pct(Nil, N)}.

%% @doc Rank teams by an aggregate metric over any match filter.
leaderboard(Opts) ->
    Metric = maps:get(metric, Opts, points),
    with_filters(Opts, fun(Filters) ->
        Matches = [M || M <- filtered_matches(Filters), maps:get(played, M)],
        Records = lists:foldl(fun(M, Acc) ->
                                      #{home_team := H, away_team := A} = M,
                                      Acc1 = bump(Acc, H, M),
                                      bump(Acc1, A, M)
                              end, #{}, Matches),
        MinPlayed = maps:get(min_played, Opts, 1),
        Rows = [begin
                    R = finalise_record(Rec),
                    R#{team => TeamId, team_name => team_name(TeamId)}
                end || {TeamId, Rec} <- maps:to_list(Records)],
        Eligible = [R || R <- Rows, maps:get(played, R) >= MinPlayed],
        Sorted = lists:sort(fun(A, B) ->
                                    {metric_value(Metric, A), maps:get(goal_difference, A)} >=
                                        {metric_value(Metric, B), maps:get(goal_difference, B)}
                            end, Eligible),
        Limit = limit(Opts),
        #{metric => Metric,
          filters => describe_filters(Filters),
          total_teams => length(Eligible),
          leaderboard => [R#{value => metric_value(Metric, R)}
                          || R <- lists:sublist(Sorted, Limit)]}
    end).

bump(Acc, TeamId, M) ->
    maps:update_with(TeamId, fun(R) -> add_match_to_record(R, M, TeamId) end,
                     add_match_to_record(record_new(), M, TeamId), Acc).

metric_value(points, R) -> maps:get(points, R);
metric_value(wins, R) -> maps:get(wins, R);
metric_value(draws, R) -> maps:get(draws, R);
metric_value(losses, R) -> maps:get(losses, R);
metric_value(goals_for, R) -> maps:get(goals_for, R);
metric_value(goals_against, R) -> -maps:get(goals_against, R);
metric_value(goal_difference, R) -> maps:get(goal_difference, R);
metric_value(win_rate, R) -> maps:get(win_rate, R);
metric_value(points_per_match, R) -> maps:get(points_per_match, R);
metric_value(home_win_rate, R) -> maps:get(win_rate, maps:get(home, R));
metric_value(away_win_rate, R) -> maps:get(win_rate, maps:get(away, R));
metric_value(home_points, R) -> maps:get(points, maps:get(home, R));
metric_value(away_points, R) -> maps:get(points, maps:get(away, R));
metric_value(_, R) -> maps:get(points, R).

%% @doc Matches ordered by winning margin.  With a team filter these are
%% that club's biggest *wins*, not the biggest scorelines it took part in.
biggest_wins(Opts) ->
    with_filters(Opts, fun(Filters) ->
        TeamId = maps:get(team_id, Filters, undefined),
        Matches = [M || M <- filtered_matches(Filters), maps:get(played, M),
                        margin(M) > 0, won_by(M, TeamId)],
        Sorted = lists:sort(fun(A, B) ->
                                    {margin(A), total_goals(A)} >= {margin(B), total_goals(B)}
                            end, Matches),
        Limit = limit(Opts),
        #{filters => describe_filters(Filters),
          total => length(Sorted),
          matches => [(match_view(M))#{margin => margin(M)}
                      || M <- lists:sublist(Sorted, Limit)]}
    end).

total_goals(#{home_goal := HG, away_goal := AG}) -> HG + AG.

won_by(_M, undefined) -> true;
won_by(#{result := home, home_team := H}, TeamId) -> H =:= TeamId;
won_by(#{result := away, away_team := A}, TeamId) -> A =:= TeamId;
won_by(_M, _TeamId) -> false.

%%====================================================================
%% Players
%%====================================================================

search_players(Opts) ->
    Candidates = player_candidates(Opts),
    Filtered = [P || P <- Candidates, player_matches(P, Opts)],
    Sort = maps:get(sort, Opts, overall),
    Sorted = sort_players(Filtered, Sort),
    Limit = limit(Opts),
    #{total => length(Sorted),
      sort => Sort,
      players => [player_view(P) || P <- lists:sublist(Sorted, Limit)]}.

player_profile(Opts) ->
    Name = maps:get(name, Opts, <<>>),
    case sort_players([P || P <- player_candidates(#{name => Name}),
                            player_matches(P, #{name => Name})], overall) of
        [] ->
            {error, #{error => unknown_player,
                      message => <<"No player matches that name. Note that the "
                                   "FIFA dataset renames players at unlicensed "
                                   "clubs, so many Brazilian league players are "
                                   "missing or appear under an invented name.">>,
                      query => Name}};
        [Best | Rest] ->
            #{player => player_view(Best, full),
              also_matching => [player_view(P) || P <- lists:sublist(Rest, 5)]}
    end.

club_squad(Opts) ->
    Club = maps:get(club, Opts, <<>>),
    Team = case bsmcp_data:resolve_team(Club) of
               undefined -> undefined;
               T -> T
           end,
    Players = case Team of
                  undefined -> bsmcp_data:players_by_club(club_key(Club));
                  _ -> squad_for_team(Team)
              end,
    case Players of
        [] ->
            {error, #{error => no_squad_data,
                      message => <<"That club has no players in the FIFA dataset. "
                                   "The FIFA data only carries squads for the "
                                   "Brazilian clubs it was licensed for; the "
                                   "others are absent even though their matches "
                                   "are in the graph.">>,
                      query => Club,
                      team => case Team of undefined -> undefined; _ -> team_view(Team) end,
                      clubs_with_squads => brazilian_clubs_with_squads()}};
        _ ->
            Sorted = sort_players(Players, maps:get(sort, Opts, overall)),
            Limit = limit(Opts),
            #{club => case Team of
                          undefined -> Club;
                          #{name := N} -> N
                      end,
              team => case Team of undefined -> undefined; _ -> team_view(Team) end,
              squad_size => length(Sorted),
              summary => squad_summary(Sorted),
              players => [player_view(P) || P <- lists:sublist(Sorted, Limit)]}
    end.

%% Clubs that appear both in the match data and in the FIFA file.
brazilian_clubs_with_squads() ->
    Counts = bsmcp_data:fold_players(
               fun(#{team_id := T, club := C}, Acc) when T =/= undefined, C =/= undefined ->
                       case bsmcp_data:team(T) of
                           #{state := S} when S =/= undefined ->
                               case bsmcp_names:is_state(S) of
                                   true -> maps:update_with(C, fun(N) -> N + 1 end, 1, Acc);
                                   false -> Acc   % Libertadores side from abroad
                               end;
                           _ ->
                               Acc
                       end;
                  (_, Acc) ->
                       Acc
               end, #{}),
    [#{club => C, players => N}
     || {C, N} <- lists:sort(fun({_, A}, {_, B}) -> A >= B end, maps:to_list(Counts))].

squad_for_team(#{id := Id, key := Key}) ->
    lists:usort(bsmcp_data:players_by_club(Id) ++ bsmcp_data:players_by_club(Key)).

club_key(Club) ->
    {Key, _State, _} = bsmcp_names:resolve(Club),
    Key.

squad_summary([]) -> #{players => 0};
squad_summary(Players) ->
    Overalls = [O || #{overall := O} <- Players, O =/= undefined],
    Ages = [A || #{age := A} <- Players, A =/= undefined],
    #{players => length(Players),
      avg_overall => avg(Overalls),
      max_overall => lists:max([0 | Overalls]),
      avg_age => avg(Ages)}.

%% @doc Group players by club (used for "Brazilian players at Brazilian clubs").
club_ratings(Opts) ->
    Players0 = case maps:get(nationality, Opts, undefined) of
                   undefined -> bsmcp_data:players();
                   Nat -> bsmcp_data:players_by_nationality(Nat)
               end,
    Players = [P || P <- Players0, maps:get(club, P, undefined) =/= undefined,
                    not maps:get(brazilian_clubs_only, Opts, false)
                        orelse maps:get(team_id, P, undefined) =/= undefined],
    Grouped = group_by(fun(#{club := C}) -> C end, Players),
    MinPlayers = maps:get(min_players, Opts, 1),
    Rows = [begin
                Summary = squad_summary(Ps),
                Summary#{club => C,
                         team => case Ps of
                                     [#{team_id := T} | _] when T =/= undefined ->
                                         team_name(T);
                                     _ -> undefined
                                 end,
                         top_player => case sort_players(Ps, overall) of
                                           [#{name := N} | _] -> N;
                                           [] -> undefined
                                       end}
            end || {C, Ps} <- maps:to_list(Grouped), length(Ps) >= MinPlayers],
    Sorted = lists:sort(fun(A, B) ->
                                {maps:get(avg_overall, A), maps:get(players, A)} >=
                                    {maps:get(avg_overall, B), maps:get(players, B)}
                        end, Rows),
    Limit = limit(Opts),
    #{total_clubs => length(Sorted),
      clubs => lists:sublist(Sorted, Limit)}.

player_candidates(Opts) ->
    case {maps:get(name, Opts, undefined), maps:get(club, Opts, undefined),
          maps:get(nationality, Opts, undefined)} of
        {Name, _, _} when Name =/= undefined, Name =/= <<>> ->
            case bsmcp_text:tokens(Name) of
                [] -> [];
                Tokens ->
                    %% intersect the token index for multi word queries
                    Sets = [sets:from_list([maps:get(id, P)
                                            || P <- bsmcp_data:players_by_token(T)])
                            || T <- Tokens],
                    Ids = sets:to_list(lists:foldl(fun sets:intersection/2, hd(Sets), tl(Sets))),
                    case Ids of
                        [] -> prefix_candidates(Tokens);
                        _ -> [bsmcp_data:player(Id) || Id <- Ids]
                    end
            end;
        {_, Club, _} when Club =/= undefined, Club =/= <<>> ->
            case bsmcp_data:resolve_team(Club) of
                undefined -> bsmcp_data:players_by_club(club_key(Club));
                Team -> squad_for_team(Team)
            end;
        {_, _, Nat} when Nat =/= undefined, Nat =/= <<>> ->
            bsmcp_data:players_by_nationality(Nat);
        _ ->
            bsmcp_data:players()
    end.

%% "gabriel bar" should still find "Gabriel Barbosa"
prefix_candidates(Tokens) ->
    Last = lists:last(Tokens),
    bsmcp_data:fold_players(
      fun(P = #{name_key := K}, Acc) ->
              case binary:match(K, Last) of
                  nomatch -> Acc;
                  _ -> [P | Acc]
              end
      end, []).

player_matches(P, Opts) ->
    matches_name(P, maps:get(name, Opts, undefined))
        andalso matches_field(maps:get(nationality_key, P), maps:get(nationality, Opts, undefined))
        andalso matches_club(P, maps:get(club, Opts, undefined))
        andalso matches_position(P, maps:get(position, Opts, undefined))
        andalso at_least(maps:get(overall, P), maps:get(min_overall, Opts, undefined))
        andalso at_most(maps:get(overall, P), maps:get(max_overall, Opts, undefined))
        andalso at_least(maps:get(potential, P), maps:get(min_potential, Opts, undefined))
        andalso at_most(maps:get(age, P), maps:get(max_age, Opts, undefined))
        andalso at_least(maps:get(age, P), maps:get(min_age, Opts, undefined)).

matches_name(_, undefined) -> true;
matches_name(_, <<>>) -> true;
matches_name(#{name_key := K}, Query) ->
    Q = bsmcp_text:normalize(Query),
    binary:match(K, Q) =/= nomatch
        orelse lists:all(fun(T) -> binary:match(K, T) =/= nomatch end,
                         binary:split(Q, <<" ">>, [global, trim_all])).

matches_field(_, undefined) -> true;
matches_field(_, <<>>) -> true;
matches_field(undefined, _) -> false;
matches_field(Value, Query) ->
    binary:match(Value, bsmcp_text:normalize(Query)) =/= nomatch.

matches_club(_, undefined) -> true;
matches_club(_, <<>>) -> true;
matches_club(#{club := undefined}, _) -> false;
matches_club(#{club := Club, club_key := CK, team_id := TeamId}, Query) ->
    QKey = club_key(Query),
    CK =:= QKey orelse TeamId =:= QKey
        orelse bsmcp_text:contains(Club, Query)
        orelse case bsmcp_data:resolve_team(Query) of
                   #{id := Id} -> TeamId =:= Id;
                   undefined -> false
               end.

matches_position(_, undefined) -> true;
matches_position(_, <<>>) -> true;
matches_position(#{position := undefined}, _) -> false;
matches_position(#{position := Pos}, Query) ->
    Q = bsmcp_text:normalize(Query),
    P = bsmcp_text:normalize(Pos),
    P =:= Q orelse binary:match(P, Q) =/= nomatch orelse position_group(P, Q).

%% forward/midfielder/defender/goalkeeper style queries
position_group(Pos, <<"forward">>) -> lists:member(Pos, [<<"st">>, <<"cf">>, <<"lf">>, <<"rf">>, <<"lw">>, <<"rw">>, <<"ls">>, <<"rs">>]);
position_group(Pos, <<"striker">>) -> lists:member(Pos, [<<"st">>, <<"cf">>, <<"ls">>, <<"rs">>]);
position_group(Pos, <<"winger">>) -> lists:member(Pos, [<<"lw">>, <<"rw">>, <<"lm">>, <<"rm">>]);
position_group(Pos, <<"midfielder">>) -> lists:member(Pos, [<<"cm">>, <<"cdm">>, <<"cam">>, <<"lm">>, <<"rm">>, <<"lcm">>, <<"rcm">>, <<"ldm">>, <<"rdm">>, <<"lam">>, <<"ram">>]);
position_group(Pos, <<"defender">>) -> lists:member(Pos, [<<"cb">>, <<"lb">>, <<"rb">>, <<"lwb">>, <<"rwb">>, <<"lcb">>, <<"rcb">>]);
position_group(Pos, <<"goalkeeper">>) -> Pos =:= <<"gk">>;
position_group(_, _) -> false.

at_least(_, undefined) -> true;
at_least(undefined, _) -> false;
at_least(Value, Min) -> Value >= Min.

at_most(_, undefined) -> true;
at_most(undefined, _) -> false;
at_most(Value, Max) -> Value =< Max.

sort_players(Players, Sort) ->
    KeyFun = fun(P) -> player_sort_key(Sort, P) end,
    lists:sort(fun(A, B) -> KeyFun(A) >= KeyFun(B) end, Players).

player_sort_key(overall, #{overall := O, potential := P}) -> {num(O), num(P)};
player_sort_key(potential, #{potential := P, overall := O}) -> {num(P), num(O)};
player_sort_key(age, #{age := A}) -> {-num(A), 0};
player_sort_key(oldest, #{age := A}) -> {num(A), 0};
player_sort_key(name, #{name_key := K}) -> {invert_name(K), 0};
player_sort_key(_, P) -> player_sort_key(overall, P).

invert_name(K) -> [255 - C || <<C>> <= K].

num(undefined) -> 0;
num(N) -> N.

avg([]) -> undefined;
avg(L) -> bsmcp_text:round2(lists:sum(L) / length(L)).

%%====================================================================
%% Dataset summary
%%====================================================================

dataset_summary() ->
    Status = bsmcp_data:status(),
    Status#{note => <<"Match records are de-duplicated and merged across the "
                      "source files; goal scorer data is not present in any of "
                      "the provided datasets."/utf8>>}.

%%====================================================================
%% Filters
%%====================================================================

with_filters(Opts, Fun) ->
    case build_filters(Opts) of
        {error, E} -> {error, E};
        {ok, Filters} -> Fun(Filters)
    end.

build_filters(Opts) ->
    case competition_filter(Opts) of
        {error, E} ->
            {error, E};
        {ok, Comp} ->
            case team_filters(Opts) of
                {error, E} ->
                    {error, E};
                {ok, TeamId, OpponentId, HomeId, AwayId} ->
                    {ok, #{competition => Comp,
                           season => maps:get(season, Opts, undefined),
                           seasons => maps:get(seasons, Opts, undefined),
                           season_from => maps:get(season_from, Opts, undefined),
                           season_to => maps:get(season_to, Opts, undefined),
                           date_from => date_opt(maps:get(date_from, Opts, undefined)),
                           date_to => date_opt(maps:get(date_to, Opts, undefined)),
                           team_id => TeamId,
                           opponent_id => OpponentId,
                           home_id => HomeId,
                           away_id => AwayId,
                           venue => maps:get(venue, Opts, undefined),
                           stage => maps:get(stage, Opts, undefined),
                           round => maps:get(round, Opts, undefined),
                           played_only => maps:get(played_only, Opts, false)}}
            end
    end.

date_opt(undefined) -> undefined;
date_opt(Bin) -> bsmcp_text:parse_date(Bin).

competition_filter(Opts) ->
    case maps:get(competition, Opts, undefined) of
        undefined -> {ok, undefined};
        <<>> -> {ok, undefined};
        Comp -> competition_key_or_error(Comp)
    end.

team_filters(Opts) ->
    Names = [{team, maps:get(team, Opts, undefined)},
             {opponent, maps:get(opponent, Opts, undefined)},
             {home, maps:get(home_team, Opts, undefined)},
             {away, maps:get(away_team, Opts, undefined)}],
    Resolved = [{K, case V of
                        undefined -> {ok, undefined};
                        <<>> -> {ok, undefined};
                        _ -> resolve_team_or_error(V)
                    end} || {K, V} <- Names],
    case [E || {_, {error, E}} <- Resolved] of
        [E | _] ->
            {error, E};
        [] ->
            Get = fun(K) ->
                          case proplists:get_value(K, Resolved) of
                              {ok, undefined} -> undefined;
                              {ok, Team} -> maps:get(id, Team)
                          end
                  end,
            {ok, Get(team), Get(opponent), Get(home), Get(away)}
    end.

%% Candidate set from the narrowest available index, then filter.
filtered_matches(Filters) ->
    Ids = candidate_ids(Filters),
    Matches = case Ids of
                  all -> bsmcp_data:matches();
                  _ -> [bsmcp_data:match(Id) || Id <- Ids]
              end,
    [M || M <- Matches, M =/= undefined, match_passes(M, Filters)].

candidate_ids(Filters) ->
    case first_defined([maps:get(team_id, Filters, undefined),
                        maps:get(home_id, Filters, undefined),
                        maps:get(away_id, Filters, undefined),
                        maps:get(opponent_id, Filters, undefined)]) of
        undefined ->
            case {maps:get(competition, Filters, undefined), seasons_of(Filters)} of
                {undefined, _} -> all;
                {_, undefined} -> all;
                {Comp, Seasons} ->
                    lists:append([bsmcp_data:competition_match_ids(Comp, S) || S <- Seasons])
            end;
        TeamId ->
            bsmcp_data:team_match_ids(TeamId)
    end.

seasons_of(Filters) ->
    case {maps:get(season, Filters, undefined), maps:get(seasons, Filters, undefined)} of
        {undefined, undefined} -> undefined;
        {S, undefined} -> [S];
        {undefined, L} when is_list(L) -> L;
        {S, L} when is_list(L) -> lists:usort([S | L])
    end.

first_defined([]) -> undefined;
first_defined([undefined | T]) -> first_defined(T);
first_defined([V | _]) -> V.

match_passes(M, F) ->
    check_competition(M, F) andalso check_season(M, F) andalso check_date(M, F)
        andalso check_teams(M, F) andalso check_stage(M, F) andalso check_played(M, F).

check_competition(#{competition := C}, #{competition := Want}) ->
    Want =:= undefined orelse C =:= Want.

check_season(#{season := S}, F) ->
    InList = case seasons_of(F) of
                 undefined -> true;
                 Seasons -> lists:member(S, Seasons)
             end,
    InList
        andalso in_range(S, maps:get(season_from, F, undefined),
                         maps:get(season_to, F, undefined)).

check_date(#{date := D}, F) ->
    in_range(D, maps:get(date_from, F, undefined), maps:get(date_to, F, undefined)).

in_range(_, undefined, undefined) -> true;
in_range(undefined, _, _) -> false;
in_range(V, From, undefined) -> V >= From;
in_range(V, undefined, To) -> V =< To;
in_range(V, From, To) -> V >= From andalso V =< To.

check_teams(M = #{home_team := H, away_team := A}, F) ->
    Team = maps:get(team_id, F, undefined),
    Opp = maps:get(opponent_id, F, undefined),
    HomeId = maps:get(home_id, F, undefined),
    AwayId = maps:get(away_id, F, undefined),
    Venue = maps:get(venue, F, undefined),
    (Team =:= undefined orelse H =:= Team orelse A =:= Team)
        andalso (Opp =:= undefined orelse H =:= Opp orelse A =:= Opp)
        andalso (HomeId =:= undefined orelse H =:= HomeId)
        andalso (AwayId =:= undefined orelse A =:= AwayId)
        andalso check_venue(M, Team, Venue).

check_venue(_, _, undefined) -> true;
check_venue(_, undefined, _) -> true;
check_venue(#{home_team := H}, Team, home) -> H =:= Team;
check_venue(#{away_team := A}, Team, away) -> A =:= Team;
check_venue(_, _, _) -> true.

check_stage(#{stage := S, round := R}, F) ->
    stage_ok(S, maps:get(stage, F, undefined)) andalso round_ok(R, maps:get(round, F, undefined)).

stage_ok(_, undefined) -> true;
stage_ok(undefined, _) -> false;
stage_ok(Stage, Want) -> bsmcp_text:contains(Stage, Want).

round_ok(_, undefined) -> true;
round_ok(undefined, _) -> false;
round_ok(Round, Want) -> bsmcp_text:normalize(Round) =:= bsmcp_text:normalize(Want).

check_played(#{played := P}, F) ->
    not maps:get(played_only, F, false) orelse P.

describe_filters(F) ->
    Pairs = [{competition, maps:get(competition, F, undefined)},
             {season, maps:get(season, F, undefined)},
             {seasons, maps:get(seasons, F, undefined)},
             {season_from, maps:get(season_from, F, undefined)},
             {season_to, maps:get(season_to, F, undefined)},
             {date_from, bsmcp_text:format_date(maps:get(date_from, F, undefined))},
             {date_to, bsmcp_text:format_date(maps:get(date_to, F, undefined))},
             {team, team_name_opt(maps:get(team_id, F, undefined))},
             {opponent, team_name_opt(maps:get(opponent_id, F, undefined))},
             {home_team, team_name_opt(maps:get(home_id, F, undefined))},
             {away_team, team_name_opt(maps:get(away_id, F, undefined))},
             {venue, maps:get(venue, F, undefined)},
             {stage, maps:get(stage, F, undefined)},
             {round, maps:get(round, F, undefined)}],
    maps:from_list([{K, V} || {K, V} <- Pairs, V =/= undefined]).

team_name_opt(undefined) -> undefined;
team_name_opt(TeamId) -> team_name(TeamId).

team_name(TeamId) ->
    case bsmcp_data:team(TeamId) of
        #{name := Name} -> Name;
        undefined -> TeamId
    end.

%%====================================================================
%% Records
%%====================================================================

record_new() ->
    #{played => 0, wins => 0, draws => 0, losses => 0,
      goals_for => 0, goals_against => 0,
      home => #{played => 0, wins => 0, draws => 0, losses => 0,
                goals_for => 0, goals_against => 0},
      away => #{played => 0, wins => 0, draws => 0, losses => 0,
                goals_for => 0, goals_against => 0}}.

record_for(TeamId, Matches) ->
    finalise_record(lists:foldl(fun(M, R) -> add_match_to_record(R, M, TeamId) end,
                                record_new(), Matches)).

add_match_to_record(R, M = #{home_team := H}, TeamId) ->
    case maps:get(played, M, true) of
        false ->
            R;
        true ->
            Side = case H =:= TeamId of true -> home; false -> away end,
            Outcome = outcome(M, Side),
            {GF, GA} = case Side of
                           home -> {maps:get(home_goal, M), maps:get(away_goal, M)};
                           away -> {maps:get(away_goal, M), maps:get(home_goal, M)}
                       end,
            Updated = bump_record(R, Outcome, GF, GA),
            Sub = bump_record(maps:get(Side, R), Outcome, GF, GA),
            Updated#{Side => Sub}
    end.

outcome(#{result := draw}, _) -> draw;
outcome(#{result := home}, home) -> win;
outcome(#{result := home}, away) -> loss;
outcome(#{result := away}, away) -> win;
outcome(#{result := away}, home) -> loss.

bump_record(R, Outcome, GF, GA) ->
    R1 = R#{played => maps:get(played, R) + 1,
            goals_for => maps:get(goals_for, R) + GF,
            goals_against => maps:get(goals_against, R) + GA},
    case Outcome of
        win -> R1#{wins => maps:get(wins, R1) + 1};
        draw -> R1#{draws => maps:get(draws, R1) + 1};
        loss -> R1#{losses => maps:get(losses, R1) + 1}
    end.

finalise_record(R) ->
    Base = derive(R),
    Base#{home => derive(maps:get(home, R, record_new())),
          away => derive(maps:get(away, R, record_new()))}.

derive(R) ->
    P = maps:get(played, R),
    W = maps:get(wins, R),
    D = maps:get(draws, R),
    GF = maps:get(goals_for, R),
    GA = maps:get(goals_against, R),
    Points = W * 3 + D,
    R1 = maps:without([home, away], R),
    R1#{points => Points,
        goal_difference => GF - GA,
        win_rate => bsmcp_text:pct(W, P),
        points_per_match => case P of 0 -> 0.0; _ -> bsmcp_text:round2(Points / P) end,
        goals_for_per_match => case P of 0 -> 0.0; _ -> bsmcp_text:round2(GF / P) end,
        goals_against_per_match => case P of 0 -> 0.0; _ -> bsmcp_text:round2(GA / P) end}.

%%====================================================================
%% Views
%%====================================================================

match_view(M) ->
    #{id := Id, competition := C, season := S, date := D, home_name := HN,
      away_name := AN, home_goal := HG, away_goal := AG, result := R,
      home_team := HT, away_team := AT} = M,
    Base = #{id => Id,
             competition => C,
             competition_name => bsmcp_data:competition_name(C),
             season => S,
             date => bsmcp_text:format_date(D),
             time => maps:get(time, M, undefined),
             round => maps:get(round, M, undefined),
             stage => maps:get(stage, M, undefined),
             venue => maps:get(venue, M, undefined),
             home_team => HN,
             away_team => AN,
             home_team_id => HT,
             away_team_id => AT,
             home_goal => HG,
             away_goal => AG,
             result => R,
             score => score_text(HG, AG),
             played => maps:get(played, M),
             sources => maps:get(sources, M, [])},
    case maps:get(stats, M, #{}) of
        Empty when map_size(Empty) =:= 0 -> Base;
        Stats -> Base#{stats => Stats}
    end.

score_text(undefined, _) -> undefined;
score_text(_, undefined) -> undefined;
score_text(HG, AG) ->
    <<(integer_to_binary(HG))/binary, "-", (integer_to_binary(AG))/binary>>.

team_view(Team) -> team_view(Team, short).

team_view(#{id := Id, name := Name, state := State, key := Key,
            match_count := Count, variants := Variants}, full) ->
    #{id => Id, name => Name, state => State, key => Key,
      matches => Count, name_variants => Variants};
team_view(#{id := Id, name := Name, state := State, match_count := Count}, short) ->
    #{id => Id, name => Name, state => State, matches => Count}.

player_view(P) -> player_view(P, short).

player_view(P, short) ->
    maps:with([id, name, age, nationality, overall, potential, club, position,
               jersey_number, team_id], P);
player_view(P, full) ->
    maps:without([name_key, nationality_key, club_key], P).

%%====================================================================
%% Helpers
%%====================================================================

sort_matches(Matches, date_asc) ->
    lists:sort(fun(A, B) -> sort_key(A) =< sort_key(B) end, Matches);
sort_matches(Matches, _) ->
    lists:sort(fun(A, B) -> sort_key(A) >= sort_key(B) end, Matches).

sort_key(#{date := undefined, season := S, id := Id}) -> {{0, 0, 0}, S, Id};
sort_key(#{date := D, season := S, id := Id}) -> {D, S, Id}.

group_by(Fun, List) ->
    lists:foldl(fun(X, Acc) ->
                        maps:update_with(Fun(X), fun(L) -> [X | L] end, [X], Acc)
                end, #{}, List).

limit(Opts) ->
    case maps:get(limit, Opts, ?DEFAULT_LIMIT) of
        N when is_integer(N), N > 0 -> min(N, ?MAX_LIMIT);
        _ -> ?DEFAULT_LIMIT
    end.

%% @doc Team name -> team map, with suggestions when it cannot be resolved.
resolve_team_or_error(undefined) ->
    {error, #{error => missing_team, message => <<"A team name is required">>}};
resolve_team_or_error(<<>>) ->
    {error, #{error => missing_team, message => <<"A team name is required">>}};
resolve_team_or_error(Name) ->
    case bsmcp_data:resolve_team(Name) of
        undefined ->
            Suggestions = [N || #{name := N} <- lists:sublist(
                                                  bsmcp_data:search_teams(first_token(Name)), 8)],
            {error, #{error => unknown_team,
                      message => <<"No team matches that name">>,
                      query => Name,
                      suggestions => Suggestions}};
        Team ->
            {ok, Team}
    end.

first_token(Name) ->
    case bsmcp_text:tokens(Name) of
        [] -> Name;
        [T | _] -> T
    end.

%% @doc Competition alias -> internal key.
-spec competition_key(binary() | atom()) -> atom() | undefined.
competition_key(Key) when is_atom(Key) ->
    case lists:member(Key, [serie_a, serie_b, serie_c, copa_do_brasil, libertadores]) of
        true -> Key;
        false -> undefined
    end;
competition_key(Bin) when is_binary(Bin) ->
    case bsmcp_text:normalize(Bin) of
        <<"serie a">> -> serie_a;
        <<"seriea">> -> serie_a;
        <<"brasileirao">> -> serie_a;
        <<"brasileirao serie a">> -> serie_a;
        <<"campeonato brasileiro">> -> serie_a;
        <<"brasileiro">> -> serie_a;
        <<"serie b">> -> serie_b;
        <<"brasileirao serie b">> -> serie_b;
        <<"serie c">> -> serie_c;
        <<"brasileirao serie c">> -> serie_c;
        <<"copa brasil">> -> copa_do_brasil;
        <<"copa">> -> copa_do_brasil;
        <<"cup">> -> copa_do_brasil;
        <<"libertadores">> -> libertadores;
        <<"copa libertadores">> -> libertadores;
        <<"conmebol libertadores">> -> libertadores;
        _ -> undefined
    end.

competition_key_or_error(Comp) ->
    case competition_key(Comp) of
        undefined ->
            {error, #{error => unknown_competition,
                      query => bsmcp_text:bin(Comp),
                      message => <<"Unknown competition">>,
                      available => [#{key => K, name => bsmcp_data:competition_name(K)}
                                    || K <- bsmcp_data:competitions()]}};
        Key ->
            {ok, Key}
    end.
