%%% Query functions over the dataset produced by bs_data:load/1.
%%%
%%% All functions are pure: they take the loaded data and a filter map and
%%% return plain Erlang terms that bs_tools formats for the MCP client.
%%% Team arguments are normalised keys (see bs_text:normalize_team/1); use
%%% resolve_team/2 to turn free text such as "Flamengo-RJ" into a key.
-module(bs_query).

-export([resolve_team/2, search_matches/2, team_stats/3, head_to_head/3,
         standings/2, aggregate/2, search_players/2, brazilian_club_summary/1]).

-type filters() :: #{season => integer(), competition => binary(),
                     from => binary(), to => binary(),
                     team => binary(), opponent => binary()}.

%% --- teams -----------------------------------------------------------------

%% Turns free text ("Flamengo", "Atletico-MG", "Flu") into a team key.
%% A base name shared by several states needs its state to pick one club.
-spec resolve_team(binary(), map()) ->
          {ok, binary()} | {error, not_found | {ambiguous, [binary()]}}.
resolve_team(Query, #{teams := Teams, bases := Bases} = Data) ->
    {Base, State} = bs_text:split_team(Query),
    case maps:get(Base, Bases, undefined) of
        undefined when Base =:= <<>> ->
            {error, not_found};
        undefined ->
            %% No exact base: fall back to a unique substring match ("flu").
            case [B || B <- maps:keys(Bases), string:find(B, Base) =/= nomatch] of
                [] -> {error, not_found};
                [B] -> choose(B, maps:get(B, Bases), State, Data);
                Many ->
                    {error, {ambiguous, names([K || B <- Many, K <- maps:get(B, Bases)], Teams)}}
            end;
        Keys ->
            choose(Base, Keys, State, Data)
    end.

%% A bare name shared by several clubs resolves to the one with most matches.
choose(_Base, [Key], _State, _Data) ->
    {ok, Key};
choose(_Base, Keys, none, #{appearances := Counts}) ->
    {ok, hd([K || K <- lists:sort(fun(A, B) -> maps:get(A, Counts, 0) >= maps:get(B, Counts, 0) end,
                                  Keys)])};
choose(Base, Keys, State, _Data) ->
    Key = <<Base/binary, "-", State/binary>>,
    case lists:member(Key, Keys) of
        true -> {ok, Key};
        false -> {error, not_found}
    end.

names(Keys, Teams) -> lists:sort([maps:get(K, Teams) || K <- Keys]).

%% --- matches ---------------------------------------------------------------

%% Newest first. Filters are ANDed; `team` and `opponent` together select
%% the fixtures between the two teams.
-spec search_matches(map(), filters()) -> [bs_data:match()].
search_matches(#{matches := Matches}, Filters) ->
    Keep = [M || M <- Matches, matches_all(M, Filters)],
    lists:reverse(Keep).

matches_all(M, Filters) ->
    maps:fold(fun(K, V, Ok) -> Ok andalso filter_ok(K, V, M) end, true, Filters).

filter_ok(season, S, M) -> maps:get(season, M) =:= S;
filter_ok(competition, C, M) ->
    string:find(bs_text:fold(maps:get(competition, M)), bs_text:fold(C)) =/= nomatch;
filter_ok(from, D, M) -> maps:get(date, M) >= D;
filter_ok(to, D, M) -> maps:get(date, M) =< D;
filter_ok(team, K, M) -> involves(K, M);
filter_ok(opponent, K, M) -> involves(K, M).

involves(K, M) -> maps:get(home, M) =:= K orelse maps:get(away, M) =:= K.

%% --- team statistics -------------------------------------------------------

%% Record for team K across the filtered matches, from its own perspective.
-spec team_stats(map(), binary(), filters()) -> map().
team_stats(Data, K, Filters) ->
    Matches = search_matches(Data, Filters#{team => K}),
    Results = [perspective(K, M) || M <- Matches],
    (summarise(Results))#{team => K,
                          home => summarise([R || {home, _, _, _} = R <- Results]),
                          away => summarise([R || {away, _, _, _} = R <- Results])}.

%% {Venue, GoalsFor, GoalsAgainst, Outcome} from K's point of view.
perspective(K, #{home := K, home_goals := GF, away_goals := GA}) ->
    {home, GF, GA, outcome(GF, GA)};
perspective(_K, #{away_goals := GF, home_goals := GA}) ->
    {away, GF, GA, outcome(GF, GA)}.

outcome(GF, GA) when GF > GA -> win;
outcome(GF, GA) when GF < GA -> loss;
outcome(_, _) -> draw.

summarise(Results) ->
    Played = length(Results),
    Wins = length([x || {_, _, _, win} <- Results]),
    Draws = length([x || {_, _, _, draw} <- Results]),
    #{matches => Played, wins => Wins, draws => Draws,
      losses => Played - Wins - Draws,
      goals_for => lists:sum([GF || {_, GF, _, _} <- Results]),
      goals_against => lists:sum([GA || {_, _, GA, _} <- Results]),
      win_rate => percent(Wins, Played)}.

%% --- head to head ----------------------------------------------------------

-spec head_to_head(map(), binary(), binary()) -> map().
head_to_head(Data, K1, K2) ->
    Matches = search_matches(Data, #{team => K1, opponent => K2}),
    Results = [perspective(K1, M) || M <- Matches],
    Summary = summarise(Results),
    #{team1 => K1, team2 => K2,
      matches => Matches,
      team1_wins => maps:get(wins, Summary),
      team2_wins => maps:get(losses, Summary),
      draws => maps:get(draws, Summary),
      team1_goals => maps:get(goals_for, Summary),
      team2_goals => maps:get(goals_against, Summary)}.

%% --- standings and aggregates ----------------------------------------------

%% League table for the filtered matches. Points: 3 win, 1 draw, 0 loss.
%% Sorted by points, wins, goal difference, goals scored, then name.
-spec standings(map(), filters()) -> [map()].
standings(Data, Filters) ->
    Matches = search_matches(Data, Filters),
    Names = maps:get(teams, Data),
    Rows = [table_row(K, Results, Names) || {K, Results} <- per_team(Matches)],
    lists:sort(fun(A, B) -> table_key(A) =< table_key(B) end, Rows).

table_row(K, Results, Names) ->
    S = summarise(Results),
    Wins = maps:get(wins, S),
    Draws = maps:get(draws, S),
    GF = maps:get(goals_for, S),
    GA = maps:get(goals_against, S),
    #{team => maps:get(K, Names), key => K,
      played => maps:get(matches, S), won => Wins, drawn => Draws,
      lost => maps:get(losses, S), goals_for => GF, goals_against => GA,
      goal_difference => GF - GA, points => 3 * Wins + Draws}.

table_key(Row) ->
    {-maps:get(points, Row), -maps:get(won, Row), -maps:get(goal_difference, Row),
     -maps:get(goals_for, Row), maps:get(team, Row)}.

%% Aggregate statistics over the filtered matches.
-spec aggregate(map(), {atom(), filters()}) -> map() | [map()].
aggregate(Data, {Metric, Filters}) ->
    Matches = search_matches(Data, Filters),
    N = length(Matches),
    case Metric of
        average_goals ->
            Goals = lists:sum([H + A || #{home_goals := H, away_goals := A} <- Matches]),
            #{matches => N, average_goals => ratio(Goals, N)};
        home_win_rate ->
            HomeWins = length([x || #{home_goals := H, away_goals := A} <- Matches, H > A]),
            #{matches => N, home_wins => HomeWins, home_win_rate => percent(HomeWins, N)};
        biggest_wins ->
            Sorted = lists:sort(fun(X, Y) -> margin(X) >= margin(Y) end, Matches),
            lists:sublist(Sorted, 10);
        best_away_record ->
            away_records(Data, Matches);
        top_scorers ->
            Names = maps:get(teams, Data),
            Rows = [#{team => maps:get(K, Names), goals_for => GF, matches => length(R)}
                    || {K, R} <- per_team(Matches),
                       GF <- [lists:sum([F || {_, F, _, _} <- R])]],
            lists:sublist(lists:sort(fun(X, Y) ->
                                         maps:get(goals_for, X) >= maps:get(goals_for, Y)
                                     end, Rows), 10)
    end.

margin(#{home_goals := H, away_goals := A}) -> abs(H - A).

%% Groups perspective results by team key in one pass over the matches.
per_team(Matches) ->
    Grouped = lists:foldl(fun(M, Acc) ->
                              H = maps:get(home, M),
                              A = maps:get(away, M),
                              Acc#{H => [perspective(H, M) | maps:get(H, Acc, [])],
                                   A => [perspective(A, M) | maps:get(A, Acc, [])]}
                          end, #{}, Matches),
    maps:to_list(Grouped).

%% Away win rate per team; teams need at least 10 away matches to qualify.
away_records(Data, Matches) ->
    Names = maps:get(teams, Data),
    Rows = [#{team => maps:get(K, Names), away_matches => maps:get(matches, Away),
              away_wins => maps:get(wins, Away), away_win_rate => maps:get(win_rate, Away)}
            || {K, Results} <- per_team(Matches),
               Away <- [summarise([R || {away, _, _, _} = R <- Results])],
               maps:get(matches, Away) >= 10],
    lists:sublist(lists:sort(fun(X, Y) ->
                                 maps:get(away_win_rate, X) >= maps:get(away_win_rate, Y)
                             end, Rows), 10).

%% --- players ---------------------------------------------------------------

%% Filters: name (accent/case-insensitive substring), nationality, club,
%% position (exact, upper case), min_overall. Sorted by overall rating.
-spec search_players(map(), map()) -> [map()].
search_players(#{players := Players}, Filters) ->
    Matched = [P || P <- Players, player_ok(P, Filters)],
    lists:sort(fun(A, B) ->
                   {-maps:get(overall, A), maps:get(name, A)} =<
                       {-maps:get(overall, B), maps:get(name, B)}
               end, Matched).

player_ok(P, Filters) ->
    maps:fold(fun(K, V, Ok) -> Ok andalso player_filter(K, V, P) end, true, Filters).

player_filter(name, Q, P) -> string:find(maps:get(name_key, P), bs_text:fold(Q)) =/= nomatch;
player_filter(nationality, Q, P) ->
    string:find(bs_text:fold(maps:get(nationality, P)), bs_text:fold(Q)) =/= nomatch;
player_filter(club, K, P) -> string:find(maps:get(club_key, P), K) =/= nomatch;
player_filter(position, Pos, P) -> maps:get(position, P) =:= Pos;
player_filter(min_overall, N, P) -> maps:get(overall, P) >= N.

%% Brazilian players grouped by their FIFA club name, for clubs whose base
%% name also appears in the match data. Joins player and match files.
-spec brazilian_club_summary(map()) -> [map()].
brazilian_club_summary(#{players := Players, bases := Bases}) ->
    Brazilian = [P || P <- Players,
                      bs_text:fold(maps:get(nationality, P)) =:= "brazil",
                      maps:is_key(maps:get(club_key, P), Bases)],
    Groups = lists:foldl(fun(P, Acc) ->
                             C = maps:get(club, P),
                             Acc#{C => [maps:get(overall, P) | maps:get(C, Acc, [])]}
                         end, #{}, Brazilian),
    Rows = [#{club => C, players => length(Ratings),
              average_overall => ratio(lists:sum(Ratings), length(Ratings))}
            || {C, Ratings} <- maps:to_list(Groups)],
    lists:sort(fun(A, B) -> maps:get(players, A) >= maps:get(players, B) end, Rows).

%% --- numbers ---------------------------------------------------------------

percent(_, 0) -> 0.0;
percent(Part, Whole) -> round(Part * 1000 / Whole) / 10.

ratio(_, 0) -> 0.0;
ratio(Part, Whole) -> round(Part * 100 / Whole) / 100.
