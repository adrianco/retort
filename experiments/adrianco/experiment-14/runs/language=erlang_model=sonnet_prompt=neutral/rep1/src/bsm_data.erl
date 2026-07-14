-module(bsm_data).
-export([load_all/0, get_matches/0, get_players/0, get_stats_matches/0, get_historical_matches/0,
         normalize_team_name/1]).

-define(MATCHES_TAB, bsm_matches).
-define(PLAYERS_TAB, bsm_players).
-define(STATS_TAB, bsm_stats_matches).

load_all() ->
    case is_loaded() of
        true -> ok;
        false ->
            ensure_table(?MATCHES_TAB),
            ensure_table(?PLAYERS_TAB),
            ensure_table(?STATS_TAB),
            DataDir = data_dir(),
            load_brasileirao(DataDir),
            load_copa_brasil(DataDir),
            load_libertadores(DataDir),
            load_historical(DataDir),
            load_br_football(DataDir),
            load_players(DataDir),
            ets:insert(?MATCHES_TAB, {loaded, true}),
            ok
    end.

is_loaded() ->
    case ets:info(?MATCHES_TAB) of
        undefined -> false;
        _ -> ets:member(?MATCHES_TAB, loaded)
    end.

data_dir() ->
    %% Try relative to escript location, then cwd
    ScriptDir = filename:dirname(escript:script_name()),
    Candidates = [
        filename:join([ScriptDir, "data", "kaggle"]),
        filename:join([code:priv_dir(brazilian_soccer_mcp), "..", "..", "data", "kaggle"]),
        "data/kaggle"
    ],
    case lists:dropwhile(fun(D) -> not filelib:is_dir(D) end, Candidates) of
        [Dir | _] -> Dir;
        [] -> "data/kaggle"
    end.

ensure_table(Name) ->
    case ets:info(Name) of
        undefined -> ets:new(Name, [named_table, public, bag]);
        _ -> ok
    end.

load_brasileirao(Dir) ->
    File = filename:join(Dir, "Brasileirao_Matches.csv"),
    Rows = bsm_csv:parse_file(File),
    [ets:insert(?MATCHES_TAB, {brasileirao, normalize_match(R, brasileirao)}) || R <- Rows],
    ok.

load_copa_brasil(Dir) ->
    File = filename:join(Dir, "Brazilian_Cup_Matches.csv"),
    Rows = bsm_csv:parse_file(File),
    [ets:insert(?MATCHES_TAB, {copa_brasil, normalize_match(R, copa_brasil)}) || R <- Rows],
    ok.

load_libertadores(Dir) ->
    File = filename:join(Dir, "Libertadores_Matches.csv"),
    Rows = bsm_csv:parse_file(File),
    [ets:insert(?MATCHES_TAB, {libertadores, normalize_match(R, libertadores)}) || R <- Rows],
    ok.

load_historical(Dir) ->
    File = filename:join(Dir, "novo_campeonato_brasileiro.csv"),
    Rows = bsm_csv:parse_file(File),
    [ets:insert(?MATCHES_TAB, {brasileirao_hist, normalize_historical(R)}) || R <- Rows],
    ok.

load_br_football(Dir) ->
    File = filename:join(Dir, "BR-Football-Dataset.csv"),
    Rows = bsm_csv:parse_file(File),
    [ets:insert(?STATS_TAB, {stats, normalize_stats_match(R)}) || R <- Rows],
    ok.

load_players(Dir) ->
    File = filename:join(Dir, "fifa_data.csv"),
    Rows = bsm_csv:parse_file(File),
    [ets:insert(?PLAYERS_TAB, {player, normalize_player(R)}) || R <- Rows],
    ok.

%% Normalize a standard match row (Brasileirao, Copa Brasil, Libertadores)
normalize_match(Row, Competition) ->
    HomeRaw = maps:get(<<"home_team">>, Row, <<>>),
    AwayRaw = maps:get(<<"away_team">>, Row, <<>>),
    DatetimeRaw = maps:get(<<"datetime">>, Row, <<>>),
    HomeGoalRaw = maps:get(<<"home_goal">>, Row, <<>>),
    AwayGoalRaw = maps:get(<<"away_goal">>, Row, <<>>),
    SeasonRaw = maps:get(<<"season">>, Row, <<>>),
    RoundRaw = maps:get(<<"round">>, Row, <<>>),
    StageRaw = maps:get(<<"stage">>, Row, <<>>),
    #{
        competition => Competition,
        home_team => normalize_team_name(HomeRaw),
        away_team => normalize_team_name(AwayRaw),
        home_team_raw => HomeRaw,
        away_team_raw => AwayRaw,
        home_goal => parse_int(HomeGoalRaw),
        away_goal => parse_int(AwayGoalRaw),
        season => parse_int(SeasonRaw),
        round => RoundRaw,
        stage => StageRaw,
        date => parse_date(DatetimeRaw),
        datetime_raw => DatetimeRaw
    }.

normalize_historical(Row) ->
    HomeRaw = maps:get(<<"Equipe_mandante">>, Row, <<>>),
    AwayRaw = maps:get(<<"Equipe_visitante">>, Row, <<>>),
    DateRaw = maps:get(<<"Data">>, Row, <<>>),
    HomeGoal = parse_int(maps:get(<<"Gols_mandante">>, Row, <<>>)),
    AwayGoal = parse_int(maps:get(<<"Gols_visitante">>, Row, <<>>)),
    Season = parse_int(maps:get(<<"Ano">>, Row, <<>>)),
    Round = maps:get(<<"Rodada">>, Row, <<>>),
    Arena = maps:get(<<"Arena">>, Row, <<>>),
    Winner = maps:get(<<"Vencedor">>, Row, <<>>),
    #{
        competition => brasileirao_hist,
        home_team => normalize_team_name(HomeRaw),
        away_team => normalize_team_name(AwayRaw),
        home_team_raw => HomeRaw,
        away_team_raw => AwayRaw,
        home_goal => HomeGoal,
        away_goal => AwayGoal,
        season => Season,
        round => Round,
        stage => <<>>,
        date => parse_date_br(DateRaw),
        datetime_raw => DateRaw,
        arena => Arena,
        winner => Winner
    }.

normalize_stats_match(Row) ->
    Tournament = maps:get(<<"tournament">>, Row, <<>>),
    HomeRaw = maps:get(<<"home">>, Row, <<>>),
    AwayRaw = maps:get(<<"away">>, Row, <<>>),
    #{
        competition => stats,
        tournament => Tournament,
        home_team => normalize_team_name(HomeRaw),
        away_team => normalize_team_name(AwayRaw),
        home_team_raw => HomeRaw,
        away_team_raw => AwayRaw,
        home_goal => parse_float_int(maps:get(<<"home_goal">>, Row, <<>>)),
        away_goal => parse_float_int(maps:get(<<"away_goal">>, Row, <<>>)),
        home_corner => parse_float_int(maps:get(<<"home_corner">>, Row, <<>>)),
        away_corner => parse_float_int(maps:get(<<"away_corner">>, Row, <<>>)),
        home_shots => parse_float_int(maps:get(<<"home_shots">>, Row, <<>>)),
        away_shots => parse_float_int(maps:get(<<"away_shots">>, Row, <<>>)),
        home_attack => parse_float_int(maps:get(<<"home_attack">>, Row, <<>>)),
        away_attack => parse_float_int(maps:get(<<"away_attack">>, Row, <<>>)),
        total_corners => parse_float_int(maps:get(<<"total_corners">>, Row, <<>>)),
        date => parse_date(maps:get(<<"date">>, Row, <<>>)),
        datetime_raw => maps:get(<<"date">>, Row, <<>>),
        season => 0,
        round => <<>>
    }.

normalize_player(Row) ->
    #{
        id => maps:get(<<"ID">>, Row, <<>>),
        name => maps:get(<<"Name">>, Row, <<>>),
        age => parse_int(maps:get(<<"Age">>, Row, <<>>)),
        nationality => maps:get(<<"Nationality">>, Row, <<>>),
        overall => parse_int(maps:get(<<"Overall">>, Row, <<>>)),
        potential => parse_int(maps:get(<<"Potential">>, Row, <<>>)),
        club => maps:get(<<"Club">>, Row, <<>>),
        position => maps:get(<<"Position">>, Row, <<>>),
        jersey_number => maps:get(<<"Jersey Number">>, Row, <<>>),
        height => maps:get(<<"Height">>, Row, <<>>),
        weight => maps:get(<<"Weight">>, Row, <<>>),
        value => maps:get(<<"Value">>, Row, <<>>),
        wage => maps:get(<<"Wage">>, Row, <<>>)
    }.

%% Return all match records as a flat list of match maps
get_matches() ->
    All = ets:tab2list(?MATCHES_TAB),
    [M || {K, M} <- All, is_map(M), K =/= loaded].

get_historical_matches() ->
    All = ets:match(?MATCHES_TAB, {brasileirao_hist, '$1'}),
    [M || [M] <- All].

get_stats_matches() ->
    All = ets:tab2list(?STATS_TAB),
    [M || {_, M} <- All].

get_players() ->
    All = ets:tab2list(?PLAYERS_TAB),
    [P || {_, P} <- All].

%% Normalize team name: strip state suffix, lowercase for comparison key
normalize_team_name(<<>>) -> <<>>;
normalize_team_name(Name) ->
    %% Remove state suffix like "-SP", "-RJ", etc.
    Stripped = case re:run(Name, <<"^(.*?)\\s*-[A-Z]{2}$">>, [{capture, [1], binary}]) of
        {match, [Base]} -> Base;
        _ -> Name
    end,
    %% Trim whitespace
    re:replace(Stripped, <<"^\\s+|\\s+$">>, <<>>, [global, {return, binary}]).

parse_int(<<>>) -> 0;
parse_int(B) when is_binary(B) ->
    S = binary_to_list(B),
    case string:to_integer(S) of
        {Int, _} when is_integer(Int) -> Int;
        _ -> 0
    end.

parse_float_int(<<>>) -> 0;
parse_float_int(B) when is_binary(B) ->
    S = binary_to_list(B),
    case string:to_float(S) of
        {F, _} when is_float(F) -> round(F);
        _ ->
            case string:to_integer(S) of
                {I, _} when is_integer(I) -> I;
                _ -> 0
            end
    end.

%% Parse ISO date "2023-09-24" or "2023-09-24 18:30:00"
parse_date(<<>>) -> <<>>;
parse_date(B) ->
    case re:run(B, <<"^(\\d{4}-\\d{2}-\\d{2})">>, [{capture, [1], binary}]) of
        {match, [D]} -> D;
        _ -> B
    end.

%% Parse Brazilian date "29/03/2003"
parse_date_br(<<>>) -> <<>>;
parse_date_br(B) ->
    case re:run(B, <<"^(\\d{2})/(\\d{2})/(\\d{4})">>, [{capture, [1,2,3], binary}]) of
        {match, [D, M, Y]} -> <<Y/binary, "-", M/binary, "-", D/binary>>;
        _ -> parse_date(B)
    end.
