-module(bsm_query).
-export([
    search_matches/1,
    get_team_stats/1,
    head_to_head/1,
    search_players/1,
    get_standings/1,
    get_biggest_wins/1,
    get_season_summary/1,
    get_competition_matches/1
]).

%% ===================================================================
%% search_matches/1
%% Params: team, home_team, away_team, competition, season, date_from, date_to, limit
%% ===================================================================
search_matches(Params) ->
    Team = maps:get(<<"team">>, Params, <<>>),
    HomeTeam = maps:get(<<"home_team">>, Params, <<>>),
    AwayTeam = maps:get(<<"away_team">>, Params, <<>>),
    Competition = maps:get(<<"competition">>, Params, <<"all">>),
    Season = maps:get(<<"season">>, Params, 0),
    DateFrom = maps:get(<<"date_from">>, Params, <<>>),
    DateTo = maps:get(<<"date_to">>, Params, <<>>),
    Limit = maps:get(<<"limit">>, Params, 20),

    Matches = get_competition_data(Competition),

    TeamNorm = norm(Team),
    HomeNorm = norm(HomeTeam),
    AwayNorm = norm(AwayTeam),

    Filtered = lists:filter(fun(M) ->
        HT = norm(maps:get(home_team, M, <<>>)),
        AT = norm(maps:get(away_team, M, <<>>)),
        S = maps:get(season, M, 0),
        D = maps:get(date, M, <<>>),

        TeamOk = TeamNorm =:= <<>> orelse
                 contains(HT, TeamNorm) orelse
                 contains(AT, TeamNorm),
        HomeOk = HomeNorm =:= <<>> orelse contains(HT, HomeNorm),
        AwayOk = AwayNorm =:= <<>> orelse contains(AT, AwayNorm),
        SeasonOk = Season =:= 0 orelse S =:= Season,
        DateFromOk = DateFrom =:= <<>> orelse D >= DateFrom,
        DateToOk = DateTo =:= <<>> orelse D =< DateTo,

        TeamOk andalso HomeOk andalso AwayOk andalso SeasonOk
            andalso DateFromOk andalso DateToOk
    end, Matches),

    Sorted = lists:sort(fun(A, B) ->
        maps:get(date, A, <<>>) >= maps:get(date, B, <<>>)
    end, Filtered),

    Limited = lists:sublist(Sorted, Limit),
    TotalFound = length(Filtered),

    #{
        total => TotalFound,
        showing => length(Limited),
        matches => [format_match(M) || M <- Limited]
    }.

%% ===================================================================
%% get_team_stats/1
%% Params: team, competition, season
%% ===================================================================
get_team_stats(Params) ->
    Team = maps:get(<<"team">>, Params, <<>>),
    Competition = maps:get(<<"competition">>, Params, <<"all">>),
    Season = maps:get(<<"season">>, Params, 0),

    TeamNorm = norm(Team),
    Matches = get_competition_data(Competition),

    TeamMatches = [M || M <- Matches,
        begin
            HT = norm(maps:get(home_team, M, <<>>)),
            AT = norm(maps:get(away_team, M, <<>>)),
            S = maps:get(season, M, 0),
            SeasonOk = Season =:= 0 orelse S =:= Season,
            (contains(HT, TeamNorm) orelse contains(AT, TeamNorm)) andalso SeasonOk
        end],

    HomeMatches = [M || M <- TeamMatches,
        contains(norm(maps:get(home_team, M, <<>>)), TeamNorm)],
    AwayMatches = [M || M <- TeamMatches,
        contains(norm(maps:get(away_team, M, <<>>)), TeamNorm)],

    HomeStats = calc_stats(HomeMatches, home),
    AwayStats = calc_stats(AwayMatches, away),

    TotalW = maps:get(wins, HomeStats) + maps:get(wins, AwayStats),
    TotalD = maps:get(draws, HomeStats) + maps:get(draws, AwayStats),
    TotalL = maps:get(losses, HomeStats) + maps:get(losses, AwayStats),
    TotalGF = maps:get(goals_for, HomeStats) + maps:get(goals_for, AwayStats),
    TotalGA = maps:get(goals_against, HomeStats) + maps:get(goals_against, AwayStats),
    TotalP = length(TeamMatches),

    WinRate = case TotalP of
        0 -> 0.0;
        _ -> TotalW / TotalP * 100
    end,

    #{
        team => Team,
        competition => Competition,
        season => Season,
        total_matches => TotalP,
        wins => TotalW,
        draws => TotalD,
        losses => TotalL,
        goals_for => TotalGF,
        goals_against => TotalGA,
        goal_diff => TotalGF - TotalGA,
        win_rate => round(WinRate * 10) / 10,
        home => HomeStats,
        away => AwayStats
    }.

%% ===================================================================
%% head_to_head/1
%% Params: team1, team2, competition, season, limit
%% ===================================================================
head_to_head(Params) ->
    Team1 = maps:get(<<"team1">>, Params, <<>>),
    Team2 = maps:get(<<"team2">>, Params, <<>>),
    Competition = maps:get(<<"competition">>, Params, <<"all">>),
    Season = maps:get(<<"season">>, Params, 0),
    Limit = maps:get(<<"limit">>, Params, 20),

    T1 = norm(Team1),
    T2 = norm(Team2),

    Matches = get_competition_data(Competition),

    H2H = [M || M <- Matches,
        begin
            HT = norm(maps:get(home_team, M, <<>>)),
            AT = norm(maps:get(away_team, M, <<>>)),
            S = maps:get(season, M, 0),
            SeasonOk = Season =:= 0 orelse S =:= Season,
            IsH2H = (contains(HT, T1) andalso contains(AT, T2)) orelse
                    (contains(HT, T2) andalso contains(AT, T1)),
            IsH2H andalso SeasonOk
        end],

    Sorted = lists:sort(fun(A, B) ->
        maps:get(date, A, <<>>) >= maps:get(date, B, <<>>)
    end, H2H),

    T1Wins = length([M || M <- H2H, team_won(M, T1)]),
    T2Wins = length([M || M <- H2H, team_won(M, T2)]),
    Draws = length([M || M <- H2H,
        maps:get(home_goal, M, 0) =:= maps:get(away_goal, M, 0)]),

    #{
        team1 => Team1,
        team2 => Team2,
        total_matches => length(H2H),
        team1_wins => T1Wins,
        team2_wins => T2Wins,
        draws => Draws,
        matches => [format_match(M) || M <- lists:sublist(Sorted, Limit)]
    }.

%% ===================================================================
%% search_players/1
%% Params: name, nationality, club, position, min_rating, max_results
%% ===================================================================
search_players(Params) ->
    NameQ = norm(maps:get(<<"name">>, Params, <<>>)),
    NatQ = norm(maps:get(<<"nationality">>, Params, <<>>)),
    ClubQ = norm(maps:get(<<"club">>, Params, <<>>)),
    PosQ = norm(maps:get(<<"position">>, Params, <<>>)),
    MinRating = maps:get(<<"min_rating">>, Params, 0),
    MaxResults = maps:get(<<"max_results">>, Params, 20),

    Players = bsm_data:get_players(),

    Filtered = lists:filter(fun(P) ->
        Name = norm(maps:get(name, P, <<>>)),
        Nat = norm(maps:get(nationality, P, <<>>)),
        Club = norm(maps:get(club, P, <<>>)),
        Pos = norm(maps:get(position, P, <<>>)),
        Rating = maps:get(overall, P, 0),

        (NameQ =:= <<>> orelse contains(Name, NameQ)) andalso
        (NatQ =:= <<>> orelse contains(Nat, NatQ)) andalso
        (ClubQ =:= <<>> orelse contains(Club, ClubQ)) andalso
        (PosQ =:= <<>> orelse contains(Pos, PosQ)) andalso
        Rating >= MinRating
    end, Players),

    Sorted = lists:sort(fun(A, B) ->
        maps:get(overall, A, 0) >= maps:get(overall, B, 0)
    end, Filtered),

    Limited = lists:sublist(Sorted, MaxResults),

    #{
        total => length(Filtered),
        showing => length(Limited),
        players => [format_player(P) || P <- Limited]
    }.

%% ===================================================================
%% get_standings/1
%% Params: season, competition
%% ===================================================================
get_standings(Params) ->
    Season = maps:get(<<"season">>, Params, 0),
    Competition = maps:get(<<"competition">>, Params, <<"brasileirao">>),

    Matches = get_competition_data(Competition),
    SeasonMatches = [M || M <- Matches,
        Season =:= 0 orelse maps:get(season, M, 0) =:= Season],

    Teams = collect_teams(SeasonMatches),

    Standings = lists:map(fun(Team) ->
        TeamMatches = [M || M <- SeasonMatches,
            maps:get(home_team_raw, M, maps:get(home_team, M)) =:= Team orelse
            maps:get(away_team_raw, M, maps:get(away_team, M)) =:= Team],
        HomeM = [M || M <- TeamMatches,
            maps:get(home_team_raw, M, maps:get(home_team, M)) =:= Team],
        AwayM = [M || M <- TeamMatches,
            maps:get(away_team_raw, M, maps:get(away_team, M)) =:= Team],
        HS = calc_stats(HomeM, home),
        AS = calc_stats(AwayM, away),
        W = maps:get(wins, HS) + maps:get(wins, AS),
        D = maps:get(draws, HS) + maps:get(draws, AS),
        L = maps:get(losses, HS) + maps:get(losses, AS),
        GF = maps:get(goals_for, HS) + maps:get(goals_for, AS),
        GA = maps:get(goals_against, HS) + maps:get(goals_against, AS),
        Pts = W * 3 + D,
        #{
            team => bsm_data:normalize_team_name(Team),
            played => length(TeamMatches),
            wins => W,
            draws => D,
            losses => L,
            goals_for => GF,
            goals_against => GA,
            goal_diff => GF - GA,
            points => Pts
        }
    end, Teams),

    Sorted = lists:sort(fun(A, B) ->
        PA = maps:get(points, A),
        PB = maps:get(points, B),
        if PA =/= PB -> PA > PB;
           true ->
               GDA = maps:get(goal_diff, A),
               GDB = maps:get(goal_diff, B),
               GDA >= GDB
        end
    end, Standings),

    Ranked = lists:zipwith(fun(Pos, Entry) ->
        maps:put(position, Pos, Entry)
    end, lists:seq(1, length(Sorted)), Sorted),

    #{
        season => Season,
        competition => Competition,
        total_matches => length(SeasonMatches),
        standings => Ranked
    }.

%% ===================================================================
%% get_biggest_wins/1
%% Params: competition, season, limit
%% ===================================================================
get_biggest_wins(Params) ->
    Competition = maps:get(<<"competition">>, Params, <<"all">>),
    Season = maps:get(<<"season">>, Params, 0),
    Limit = maps:get(<<"limit">>, Params, 10),

    Matches = get_competition_data(Competition),
    Filtered = [M || M <- Matches,
        Season =:= 0 orelse maps:get(season, M, 0) =:= Season],

    WithMargin = lists:map(fun(M) ->
        HG = maps:get(home_goal, M, 0),
        AG = maps:get(away_goal, M, 0),
        Margin = abs(HG - AG),
        maps:put(margin, Margin, M)
    end, Filtered),

    Sorted = lists:sort(fun(A, B) ->
        MA = maps:get(margin, A),
        MB = maps:get(margin, B),
        if MA =/= MB -> MA > MB;
           true ->
               TGA = maps:get(home_goal, A, 0) + maps:get(away_goal, A, 0),
               TGB = maps:get(home_goal, B, 0) + maps:get(away_goal, B, 0),
               TGA >= TGB
        end
    end, WithMargin),

    Limited = lists:sublist(Sorted, Limit),

    #{
        competition => Competition,
        season => Season,
        biggest_wins => [format_match(M) || M <- Limited]
    }.

%% ===================================================================
%% get_season_summary/1
%% Params: season, competition
%% ===================================================================
get_season_summary(Params) ->
    Season = maps:get(<<"season">>, Params, 0),
    Competition = maps:get(<<"competition">>, Params, <<"all">>),

    Matches = get_competition_data(Competition),
    SeasonMatches = [M || M <- Matches,
        Season =:= 0 orelse maps:get(season, M, 0) =:= Season],

    TotalMatches = length(SeasonMatches),
    TotalGoals = lists:sum([maps:get(home_goal, M, 0) + maps:get(away_goal, M, 0) || M <- SeasonMatches]),
    HomeWins = length([M || M <- SeasonMatches, maps:get(home_goal, M, 0) > maps:get(away_goal, M, 0)]),
    AwayWins = length([M || M <- SeasonMatches, maps:get(home_goal, M, 0) < maps:get(away_goal, M, 0)]),
    Draws = TotalMatches - HomeWins - AwayWins,

    AvgGoals = case TotalMatches of
        0 -> 0.0;
        _ -> TotalGoals / TotalMatches
    end,
    HomeWinRate = case TotalMatches of
        0 -> 0.0;
        _ -> HomeWins / TotalMatches * 100
    end,

    #{
        season => Season,
        competition => Competition,
        total_matches => TotalMatches,
        total_goals => TotalGoals,
        avg_goals_per_match => round(AvgGoals * 100) / 100,
        home_wins => HomeWins,
        away_wins => AwayWins,
        draws => Draws,
        home_win_rate => round(HomeWinRate * 10) / 10
    }.

%% ===================================================================
%% get_competition_matches/1
%% Params: competition, season, stage, limit
%% ===================================================================
get_competition_matches(Params) ->
    Competition = maps:get(<<"competition">>, Params, <<"all">>),
    Season = maps:get(<<"season">>, Params, 0),
    Stage = norm(maps:get(<<"stage">>, Params, <<>>)),
    Limit = maps:get(<<"limit">>, Params, 50),

    Matches = get_competition_data(Competition),
    Filtered = [M || M <- Matches,
        begin
            S = maps:get(season, M, 0),
            Stg = norm(maps:get(stage, M, <<>>)),
            SeasonOk = Season =:= 0 orelse S =:= Season,
            StageOk = Stage =:= <<>> orelse contains(Stg, Stage),
            SeasonOk andalso StageOk
        end],

    Sorted = lists:sort(fun(A, B) ->
        maps:get(date, A, <<>>) >= maps:get(date, B, <<>>)
    end, Filtered),

    Limited = lists:sublist(Sorted, Limit),

    #{
        competition => Competition,
        season => Season,
        total => length(Filtered),
        showing => length(Limited),
        matches => [format_match(M) || M <- Limited]
    }.

%% ===================================================================
%% Internal helpers
%% ===================================================================

get_competition_data(<<"all">>) ->
    bsm_data:get_matches();
get_competition_data(<<"brasileirao">>) ->
    %% Prefer the main Brasileirao dataset; use hist only for years not covered (pre-2012)
    All = bsm_data:get_matches(),
    Main = [M || M <- All, maps:get(competition, M) =:= brasileirao],
    MainSeasons = lists:usort([maps:get(season, M, 0) || M <- Main]),
    Hist = [M || M <- All, maps:get(competition, M) =:= brasileirao_hist,
                 not lists:member(maps:get(season, M, 0), MainSeasons)],
    Main ++ Hist;
get_competition_data(<<"copa_brasil">>) ->
    All = bsm_data:get_matches(),
    [M || M <- All, maps:get(competition, M) =:= copa_brasil];
get_competition_data(<<"libertadores">>) ->
    All = bsm_data:get_matches(),
    [M || M <- All, maps:get(competition, M) =:= libertadores];
get_competition_data(_) ->
    bsm_data:get_matches().

calc_stats(Matches, Side) ->
    lists:foldl(fun(M, Acc) ->
        HG = maps:get(home_goal, M, 0),
        AG = maps:get(away_goal, M, 0),
        {GF, GA} = case Side of
            home -> {HG, AG};
            away -> {AG, HG}
        end,
        {W, D, L} = if
            GF > GA -> {1, 0, 0};
            GF =:= GA -> {0, 1, 0};
            true -> {0, 0, 1}
        end,
        #{
            wins => maps:get(wins, Acc) + W,
            draws => maps:get(draws, Acc) + D,
            losses => maps:get(losses, Acc) + L,
            goals_for => maps:get(goals_for, Acc) + GF,
            goals_against => maps:get(goals_against, Acc) + GA,
            played => maps:get(played, Acc) + 1
        }
    end, #{wins => 0, draws => 0, losses => 0, goals_for => 0, goals_against => 0, played => 0}, Matches).

team_won(M, TeamNorm) ->
    HT = norm(maps:get(home_team, M, <<>>)),
    AT = norm(maps:get(away_team, M, <<>>)),
    HG = maps:get(home_goal, M, 0),
    AG = maps:get(away_goal, M, 0),
    (contains(HT, TeamNorm) andalso HG > AG) orelse
    (contains(AT, TeamNorm) andalso AG > HG).

collect_teams(Matches) ->
    %% Use raw names (with state suffix) as identity keys, deduplicate
    All = [maps:get(home_team_raw, M, maps:get(home_team, M)) || M <- Matches] ++
          [maps:get(away_team_raw, M, maps:get(away_team, M)) || M <- Matches],
    Unique = lists:usort([T || T <- All, T =/= <<>>]),
    Unique.

format_match(M) ->
    #{
        competition => atom_to_binary(maps:get(competition, M, unknown)),
        date => maps:get(date, M, <<>>),
        home_team => maps:get(home_team_raw, M, maps:get(home_team, M, <<>>)),
        away_team => maps:get(away_team_raw, M, maps:get(away_team, M, <<>>)),
        home_goal => maps:get(home_goal, M, 0),
        away_goal => maps:get(away_goal, M, 0),
        season => maps:get(season, M, 0),
        round => maps:get(round, M, <<>>),
        stage => maps:get(stage, M, <<>>)
    }.

format_player(P) ->
    #{
        name => maps:get(name, P, <<>>),
        nationality => maps:get(nationality, P, <<>>),
        overall => maps:get(overall, P, 0),
        potential => maps:get(potential, P, 0),
        club => maps:get(club, P, <<>>),
        position => maps:get(position, P, <<>>),
        age => maps:get(age, P, 0),
        height => maps:get(height, P, <<>>),
        weight => maps:get(weight, P, <<>>),
        value => maps:get(value, P, <<>>)
    }.

norm(<<>>) -> <<>>;
norm(B) when is_binary(B) ->
    Str = unicode:characters_to_list(B, utf8),
    Lower = string:casefold(Str),
    Bin = unicode:characters_to_binary(Lower),
    %% Trim whitespace
    Trimmed = string:trim(Bin),
    case is_binary(Trimmed) of
        true -> Trimmed;
        false -> unicode:characters_to_binary(Trimmed)
    end;
norm(A) when is_atom(A) ->
    norm(atom_to_binary(A));
norm(I) when is_integer(I) ->
    integer_to_binary(I).

contains(_, <<>>) -> true;
contains(Haystack, Needle) ->
    binary:match(Haystack, Needle) =/= nomatch.
