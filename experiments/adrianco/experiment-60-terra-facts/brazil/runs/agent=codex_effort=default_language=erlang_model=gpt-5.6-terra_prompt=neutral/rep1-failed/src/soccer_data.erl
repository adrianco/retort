-module(soccer_data).
-export([load/1, normalize_team/1, normalize_text/1, to_int/1]).

load(DataDir) ->
    MatchFiles = [
      {"Brasileirao_Matches.csv", brasileirao},
      {"Brazilian_Cup_Matches.csv", copa_do_brasil},
      {"Libertadores_Matches.csv", libertadores},
      {"BR-Football-Dataset.csv", extended},
      {"novo_campeonato_brasileiro.csv", historical}],
    Matches = lists:flatten([load_matches(filename:join(DataDir, File), Competition) || {File, Competition} <- MatchFiles]),
    #{matches => Matches, players => load_players(filename:join(DataDir, "fifa_data.csv"))}.

load_matches(Path, Competition) ->
    [Header | Rows] = soccer_csv:read(Path),
    Keys = [normalize_key(K) || K <- Header],
    [match(row(Keys, R), Competition) || R <- Rows, length(R) =:= length(Keys)].

load_players(Path) ->
    [Header | Rows] = soccer_csv:read(Path),
    Keys = [normalize_key(K) || K <- Header],
    [player(row(Keys, R)) || R <- Rows, length(R) =:= length(Keys)].

row(Keys, Values) -> maps:from_list(lists:zip(Keys, Values)).
field(Map, Keys) ->
    case lists:dropwhile(fun(K) -> not maps:is_key(K, Map) end, Keys) of
        [K | _] -> maps:get(K, Map); [] -> ""
    end.
match(Row, Competition) ->
    {Home, Away, HG, AG, Date, Season, Round} = case Competition of
        extended -> {field(Row,[home]), field(Row,[away]), field(Row,[home_goal]), field(Row,[away_goal]), field(Row,[date]), season_from_date(field(Row,[date])), ""};
        historical -> {field(Row,[equipe_mandante]), field(Row,[equipe_visitante]), field(Row,[gols_mandante]), field(Row,[gols_visitante]), field(Row,[data]), field(Row,[ano]), field(Row,[rodada])};
        _ -> {field(Row,[home_team]), field(Row,[away_team]), field(Row,[home_goal]), field(Row,[away_goal]), field(Row,[datetime]), field(Row,[season]), field(Row,[round, stage])}
    end,
    #{competition => Competition, home => Home, away => Away, home_key => normalize_team(Home), away_key => normalize_team(Away),
      home_goals => to_int(HG), away_goals => to_int(AG), date => Date, season => to_int(Season), round => Round}.
player(Row) ->
    #{id => field(Row,[id]), name => field(Row,[name]), name_key => normalize_text(field(Row,[name])), nationality => field(Row,[nationality]),
      club => field(Row,[club]), club_key => normalize_text(field(Row,[club])), position => field(Row,[position]), overall => to_int(field(Row,[overall])), potential => to_int(field(Row,[potential]))}.

normalize_key(Key) -> list_to_atom(lists:flatten(string:replace(normalize_text(Key), " ", "_", all))).
normalize_team(S) ->
    N = normalize_text(S),
    case re:run(N, "^(.*)-[a-z]{2}$", [{capture,[1],list}]) of {match,[Base]} -> Base; nomatch -> N end.
normalize_text(S) ->
    Lower = string:lowercase(string:trim(S)),
    lists:flatten([fold(C) || C <- Lower, C =/= 16#FEFF]).
fold($á)->"a"; fold($à)->"a"; fold($â)->"a"; fold($ã)->"a"; fold($ä)->"a";
fold($é)->"e"; fold($ê)->"e"; fold($ë)->"e"; fold($í)->"i"; fold($ï)->"i";
fold($ó)->"o"; fold($ô)->"o"; fold($õ)->"o"; fold($ö)->"o"; fold($ú)->"u"; fold($ü)->"u"; fold($ç)->"c"; fold(C)->[C].
to_int(S) when is_integer(S) -> S;
to_int("") -> 0;
to_int(S) ->
    case string:to_float(S) of {F, _} when is_float(F) -> trunc(F); {error, _} -> case string:to_integer(S) of {I,_}->I; _->0 end end.
season_from_date(Date) ->
    case re:run(Date, "([0-9]{4})", [{capture,[1],list}]) of {match,[Year]} -> to_int(Year); _ -> 0 end.
