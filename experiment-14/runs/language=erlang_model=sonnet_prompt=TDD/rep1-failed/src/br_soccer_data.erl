-module(br_soccer_data).
-export([load_brasileirao/1, load_cup/1, load_libertadores/1,
         load_br_football/1, load_historico/1, load_players/1,
         load_all/1]).

%% Load all datasets and return a state map.
load_all(DataDir) ->
    #{
        brasileirao  => load_brasileirao(DataDir),
        cup          => load_cup(DataDir),
        libertadores => load_libertadores(DataDir),
        br_football  => load_br_football(DataDir),
        historico    => load_historico(DataDir),
        players      => load_players(DataDir)
    }.

%% Load Brasileirão Serie A matches from CSV.
%% Returns list of maps: #{home_team, away_team, home_goal, away_goal, season, date, round}
load_brasileirao(DataDir) ->
    File = filename:join(DataDir, "Brasileirao_Matches.csv"),
    Rows = br_soccer_csv:read_csv(File),
    [parse_brasileirao_row(R) || R <- Rows].

parse_brasileirao_row(R) ->
    #{
        home_team => br_soccer_csv:normalize_team(maps:get("home_team", R, "")),
        away_team => br_soccer_csv:normalize_team(maps:get("away_team", R, "")),
        home_goal => br_soccer_csv:parse_int(maps:get("home_goal", R, "0")),
        away_goal => br_soccer_csv:parse_int(maps:get("away_goal", R, "0")),
        season    => br_soccer_csv:parse_int(maps:get("season", R, "0")),
        round     => br_soccer_csv:parse_int(maps:get("round", R, "0")),
        date      => br_soccer_csv:parse_date(maps:get("datetime", R, "")),
        competition => "brasileirao"
    }.

%% Load Copa do Brasil matches.
load_cup(DataDir) ->
    File = filename:join(DataDir, "Brazilian_Cup_Matches.csv"),
    Rows = br_soccer_csv:read_csv(File),
    [parse_cup_row(R) || R <- Rows].

parse_cup_row(R) ->
    #{
        home_team   => br_soccer_csv:normalize_team(maps:get("home_team", R, "")),
        away_team   => br_soccer_csv:normalize_team(maps:get("away_team", R, "")),
        home_goal   => br_soccer_csv:parse_int(maps:get("home_goal", R, "0")),
        away_goal   => br_soccer_csv:parse_int(maps:get("away_goal", R, "0")),
        season      => br_soccer_csv:parse_int(maps:get("season", R, "0")),
        round       => maps:get("round", R, ""),
        date        => br_soccer_csv:parse_date(maps:get("datetime", R, "")),
        competition => "copa_do_brasil"
    }.

%% Load Copa Libertadores matches.
load_libertadores(DataDir) ->
    File = filename:join(DataDir, "Libertadores_Matches.csv"),
    Rows = br_soccer_csv:read_csv(File),
    [parse_libertadores_row(R) || R <- Rows].

parse_libertadores_row(R) ->
    #{
        home_team   => br_soccer_csv:normalize_team(maps:get("home_team", R, "")),
        away_team   => br_soccer_csv:normalize_team(maps:get("away_team", R, "")),
        home_goal   => br_soccer_csv:parse_int(maps:get("home_goal", R, "0")),
        away_goal   => br_soccer_csv:parse_int(maps:get("away_goal", R, "0")),
        season      => br_soccer_csv:parse_int(maps:get("season", R, "0")),
        stage       => maps:get("stage", R, ""),
        date        => br_soccer_csv:parse_date(maps:get("datetime", R, "")),
        competition => "libertadores"
    }.

%% Load extended BR football dataset.
load_br_football(DataDir) ->
    File = filename:join(DataDir, "BR-Football-Dataset.csv"),
    Rows = br_soccer_csv:read_csv(File),
    [parse_br_football_row(R) || R <- Rows].

parse_br_football_row(R) ->
    #{
        tournament   => maps:get("tournament", R, ""),
        home_team    => br_soccer_csv:normalize_team(maps:get("home", R, "")),
        away_team    => br_soccer_csv:normalize_team(maps:get("away", R, "")),
        home_goal    => round(br_soccer_csv:parse_float(maps:get("home_goal", R, "0"))),
        away_goal    => round(br_soccer_csv:parse_float(maps:get("away_goal", R, "0"))),
        home_corner  => br_soccer_csv:parse_float(maps:get("home_corner", R, "0")),
        away_corner  => br_soccer_csv:parse_float(maps:get("away_corner", R, "0")),
        home_shots   => br_soccer_csv:parse_float(maps:get("home_shots", R, "0")),
        away_shots   => br_soccer_csv:parse_float(maps:get("away_shots", R, "0")),
        date         => br_soccer_csv:parse_date(maps:get("date", R, "")),
        competition  => maps:get("tournament", R, "")
    }.

%% Load historical Brasileirão 2003-2019.
load_historico(DataDir) ->
    File = filename:join(DataDir, "novo_campeonato_brasileiro.csv"),
    Rows = br_soccer_csv:read_csv(File),
    [parse_historico_row(R) || R <- Rows].

parse_historico_row(R) ->
    #{
        home_team   => maps:get("Equipe_mandante", R, ""),
        away_team   => maps:get("Equipe_visitante", R, ""),
        home_goal   => br_soccer_csv:parse_int(maps:get("Gols_mandante", R, "0")),
        away_goal   => br_soccer_csv:parse_int(maps:get("Gols_visitante", R, "0")),
        season      => br_soccer_csv:parse_int(maps:get("Ano", R, "0")),
        round       => br_soccer_csv:parse_int(maps:get("Rodada", R, "0")),
        date        => br_soccer_csv:parse_date(maps:get("Data", R, "")),
        arena       => maps:get("Arena", R, ""),
        winner      => maps:get("Vencedor", R, ""),
        competition => "brasileirao"
    }.

%% Load FIFA player data.
load_players(DataDir) ->
    File = filename:join(DataDir, "fifa_data.csv"),
    Rows = br_soccer_csv:read_csv(File),
    [parse_player_row(R) || R <- Rows].

parse_player_row(R) ->
    #{
        id          => maps:get("ID", R, ""),
        name        => maps:get("Name", R, ""),
        age         => br_soccer_csv:parse_int(maps:get("Age", R, "0")),
        nationality => maps:get("Nationality", R, ""),
        overall     => br_soccer_csv:parse_int(maps:get("Overall", R, "0")),
        potential   => br_soccer_csv:parse_int(maps:get("Potential", R, "0")),
        club        => maps:get("Club", R, ""),
        position    => maps:get("Position", R, ""),
        value       => maps:get("Value", R, ""),
        wage        => maps:get("Wage", R, "")
    }.
