-module(br_soccer_query).
-export([find_matches_by_team/3, find_matches_by_season/2,
         find_matches_by_competition/2, head_to_head/3,
         team_stats/4, season_standings/3, find_players_by_name/2,
         find_players_by_nationality/2, find_players_by_club/2,
         top_players/2, biggest_wins/2, avg_goals_per_match/2,
         best_home_records/3]).

%% Collect all matches across all datasets, deduplicated by key fields.
%% historico (2003-2011 only) and brasileirao (2012-2023) together cover all years.
all_matches(State) ->
    Brasileirao = maps:get(brasileirao, State, []),
    Cup         = maps:get(cup, State, []),
    Libertadores= maps:get(libertadores, State, []),
    Historico   = maps:get(historico, State, []),
    %% Use historico only for seasons not covered by brasileirao (pre-2012)
    BrSeasons = lists:usort([maps:get(season, M, 0) || M <- Brasileirao]),
    HistFiltered = [M || M <- Historico, not lists:member(maps:get(season, M, 0), BrSeasons)],
    lists:flatten([Brasileirao, Cup, Libertadores, HistFiltered]).

%% Case-insensitive substring match for team names.
team_matches(TeamName, MatchTeam) ->
    string:find(string:lowercase(MatchTeam), string:lowercase(TeamName)) =/= nomatch.

%% Find matches involving a team (home, away, or all).
find_matches_by_team(State, Team, home) ->
    [M || M <- all_matches(State), team_matches(Team, maps:get(home_team, M, ""))];
find_matches_by_team(State, Team, away) ->
    [M || M <- all_matches(State), team_matches(Team, maps:get(away_team, M, ""))];
find_matches_by_team(State, Team, all) ->
    [M || M <- all_matches(State),
          team_matches(Team, maps:get(home_team, M, "")) orelse
          team_matches(Team, maps:get(away_team, M, ""))].

%% Find matches by season (integer).
find_matches_by_season(State, Season) ->
    [M || M <- all_matches(State), maps:get(season, M, 0) =:= Season].

%% Find matches by competition string (uses deduplicated all_matches as base).
%% br_football is excluded to avoid double-counting with the primary datasets.
find_matches_by_competition(State, Comp) ->
    CompLow = string:lowercase(Comp),
    [M || M <- all_matches(State),
          string:find(string:lowercase(maps:get(competition, M, "")), CompLow) =/= nomatch].

%% Head-to-head statistics between two teams.
head_to_head(State, Team1, Team2) ->
    Matches = [M || M <- all_matches(State),
                    (team_matches(Team1, maps:get(home_team, M, "")) andalso
                     team_matches(Team2, maps:get(away_team, M, ""))) orelse
                    (team_matches(Team2, maps:get(home_team, M, "")) andalso
                     team_matches(Team1, maps:get(away_team, M, "")))],
    {W1, W2, D} = lists:foldl(fun(M, {A1, A2, AD}) ->
        HG = maps:get(home_goal, M, 0),
        AG = maps:get(away_goal, M, 0),
        HomeIsT1 = team_matches(Team1, maps:get(home_team, M, "")),
        if
            HG > AG, HomeIsT1 -> {A1 + 1, A2, AD};
            HG > AG            -> {A1, A2 + 1, AD};
            HG < AG, HomeIsT1 -> {A1, A2 + 1, AD};
            HG < AG            -> {A1 + 1, A2, AD};
            true               -> {A1, A2, AD + 1}
        end
    end, {0, 0, 0}, Matches),
    #{total => length(Matches), team1_wins => W1, team2_wins => W2, draws => D}.

%% Calculate team statistics for a given competition and season.
%% Use season=0 for all seasons, competition="" for all.
team_stats(State, Team, Comp, Season) ->
    Matches = find_matches_by_competition(State, Comp),
    Filtered = [M || M <- Matches,
                     (Season =:= 0 orelse maps:get(season, M, 0) =:= Season),
                     (team_matches(Team, maps:get(home_team, M, "")) orelse
                      team_matches(Team, maps:get(away_team, M, "")))],
    lists:foldl(fun(M, Acc) ->
        HG = maps:get(home_goal, M, 0),
        AG = maps:get(away_goal, M, 0),
        IsHome = team_matches(Team, maps:get(home_team, M, "")),
        {GF, GA} = if IsHome -> {HG, AG}; true -> {AG, HG} end,
        Result = if
            IsHome, HG > AG -> win;
            IsHome, HG < AG -> loss;
            IsHome -> draw;
            AG > HG -> win;
            AG < HG -> loss;
            true -> draw
        end,
        #{matches := Matches2, wins := W, draws := D, losses := L,
          goals_for := GoalsF, goals_against := GoalsA} = Acc,
        Acc#{
            matches := Matches2 + 1,
            wins    := W + (if Result =:= win -> 1; true -> 0 end),
            draws   := D + (if Result =:= draw -> 1; true -> 0 end),
            losses  := L + (if Result =:= loss -> 1; true -> 0 end),
            goals_for     := GoalsF + GF,
            goals_against := GoalsA + GA
        }
    end, #{matches => 0, wins => 0, draws => 0, losses => 0, goals_for => 0, goals_against => 0},
    Filtered).

%% Calculate season standings as [{Team, Points, Wins, Draws, Losses}] sorted by points.
season_standings(State, Season, Comp) ->
    Matches = [M || M <- find_matches_by_competition(State, Comp),
                    maps:get(season, M, 0) =:= Season],
    Teams = lists:usort(
        [maps:get(home_team, M, "") || M <- Matches] ++
        [maps:get(away_team, M, "") || M <- Matches]
    ),
    TeamPoints = lists:map(fun(Team) ->
        {W, D, L} = lists:foldl(fun(M, {Wins, Draws, Losses}) ->
            HG = maps:get(home_goal, M, 0),
            AG = maps:get(away_goal, M, 0),
            IsHome = team_matches(Team, maps:get(home_team, M, "")),
            IsAway = team_matches(Team, maps:get(away_team, M, "")),
            if
                IsHome, HG > AG -> {Wins + 1, Draws, Losses};
                IsHome, HG =:= AG -> {Wins, Draws + 1, Losses};
                IsHome -> {Wins, Draws, Losses + 1};
                IsAway, AG > HG -> {Wins + 1, Draws, Losses};
                IsAway, AG =:= HG -> {Wins, Draws + 1, Losses};
                IsAway -> {Wins, Draws, Losses + 1};
                true -> {Wins, Draws, Losses}
            end
        end, {0, 0, 0}, Matches),
        Points = W * 3 + D,
        {Team, Points, W, D, L}
    end, Teams),
    lists:sort(fun({_, P1, W1, _, _}, {_, P2, W2, _, _}) ->
        P1 > P2 orelse (P1 =:= P2 andalso W1 > W2)
    end, TeamPoints).

%% Find players by name (case-insensitive partial match).
find_players_by_name(State, Name) ->
    NameLow = string:lowercase(Name),
    [P || P <- maps:get(players, State, []),
          string:find(string:lowercase(maps:get(name, P, "")), NameLow) =/= nomatch].

%% Find players by nationality (exact match).
find_players_by_nationality(State, Nationality) ->
    [P || P <- maps:get(players, State, []),
          maps:get(nationality, P, "") =:= Nationality].

%% Find players by club (case-insensitive partial match).
find_players_by_club(State, Club) ->
    ClubLow = string:lowercase(Club),
    [P || P <- maps:get(players, State, []),
          string:find(string:lowercase(maps:get(club, P, "")), ClubLow) =/= nomatch].

%% Top players with optional filters: nationality, club, position, limit.
top_players(State, Opts) ->
    Nationality = maps:get(nationality, Opts, ""),
    Club = maps:get(club, Opts, ""),
    Position = maps:get(position, Opts, ""),
    Limit = maps:get(limit, Opts, 10),
    Players = maps:get(players, State, []),
    Filtered = [P || P <- Players,
                     (Nationality =:= "" orelse maps:get(nationality, P, "") =:= Nationality),
                     (Club =:= "" orelse team_matches(Club, maps:get(club, P, ""))),
                     (Position =:= "" orelse maps:get(position, P, "") =:= Position)],
    Sorted = lists:sort(fun(A, B) ->
        maps:get(overall, A, 0) >= maps:get(overall, B, 0)
    end, Filtered),
    lists:sublist(Sorted, Limit).

%% Find the N biggest wins (largest goal difference) across all matches.
biggest_wins(State, N) ->
    Matches = all_matches(State),
    WithDiff = [{M, abs(maps:get(home_goal, M, 0) - maps:get(away_goal, M, 0))} || M <- Matches],
    Sorted = lists:sort(fun({_, D1}, {_, D2}) -> D1 >= D2 end, WithDiff),
    lists:sublist(Sorted, N).

%% Average goals per match for a competition.
avg_goals_per_match(State, Comp) ->
    Matches = find_matches_by_competition(State, Comp),
    case length(Matches) of
        0 -> 0.0;
        N ->
            Total = lists:sum([maps:get(home_goal, M, 0) + maps:get(away_goal, M, 0) || M <- Matches]),
            Total / N
    end.

%% Best home records (win rate) for a competition, returning top N teams.
best_home_records(State, Comp, N) ->
    Matches = find_matches_by_competition(State, Comp),
    Teams = lists:usort([maps:get(home_team, M, "") || M <- Matches]),
    Records = lists:filtermap(fun(Team) ->
        HomeMatches = [M || M <- Matches, team_matches(Team, maps:get(home_team, M, ""))],
        case length(HomeMatches) of
            0 -> false;
            Total ->
                Wins = length([M || M <- HomeMatches,
                                    maps:get(home_goal, M, 0) > maps:get(away_goal, M, 0)]),
                {true, {Team, Wins / Total}}
        end
    end, Teams),
    Sorted = lists:sort(fun({_, R1}, {_, R2}) -> R1 >= R2 end, Records),
    lists:sublist(Sorted, N).
