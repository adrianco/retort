%% @doc Dataset loading and normalization.
%%
%% Each provided CSV uses a different column layout; the `*_row/1'
%% functions convert one header-keyed row map into a single canonical
%% match map shape:
%%
%%   #{competition, home, away, home_norm, away_norm,
%%     home_goal, away_goal, season, round, date, stage}
%%
%% Player rows from the FIFA dataset are converted by `player_row/1'.
-module(bsmcp_data).

-export([parse_date/1, parse_int/1]).
-export([brasileirao_row/1, cup_row/1, libertadores_row/1,
         br_football_row/1, novo_row/1, player_row/1]).
-export([load_matches/1, load_players/1, default_dir/0, dedup/1]).

-define(MATCH_FILES,
        [{"Brasileirao_Matches.csv", brasileirao_row},
         {"Brazilian_Cup_Matches.csv", cup_row},
         {"Libertadores_Matches.csv", libertadores_row},
         {"BR-Football-Dataset.csv", br_football_row},
         {"novo_campeonato_brasileiro.csv", novo_row}]).

%% --- value parsing ----------------------------------------------------

%% @doc Normalize any supported date spelling to ISO `YYYY-MM-DD'.
-spec parse_date(binary() | undefined) -> binary() | undefined.
parse_date(undefined) -> undefined;
parse_date(<<>>) -> undefined;
parse_date(Bin) ->
    %% Drop any trailing " HH:MM:SS" time component first.
    [DatePart | _] = binary:split(Bin, <<" ">>),
    case binary:split(DatePart, <<"/">>, [global]) of
        [D, M, Y] when byte_size(Y) =:= 4 ->
            <<Y/binary, "-", (pad2(M))/binary, "-", (pad2(D))/binary>>;
        _ ->
            case binary:split(DatePart, <<"-">>, [global]) of
                [Y, M, D] when byte_size(Y) =:= 4 ->
                    <<Y/binary, "-", (pad2(M))/binary, "-", (pad2(D))/binary>>;
                _ -> DatePart
            end
    end.

pad2(<<C>>) -> <<$0, C>>;
pad2(B) -> B.

%% @doc Parse an integer, tolerating "1.0"-style floats and blanks.
-spec parse_int(binary() | undefined) -> integer() | undefined.
parse_int(undefined) -> undefined;
parse_int(<<>>) -> undefined;
parse_int(Bin) ->
    S = string:trim(binary_to_list(Bin)),
    case S of
        "" -> undefined;
        _ ->
            try list_to_integer(S)
            catch error:badarg ->
                try round(list_to_float(S))
                catch error:badarg -> undefined end
            end
    end.

%% --- row transforms ---------------------------------------------------

brasileirao_row(R) ->
    match(<<"Brasileirão"/utf8>>,
          g(R, <<"home_team">>), g(R, <<"away_team">>),
          g(R, <<"home_goal">>), g(R, <<"away_goal">>),
          g(R, <<"season">>), g(R, <<"round">>),
          g(R, <<"datetime">>), undefined).

cup_row(R) ->
    match(<<"Copa do Brasil"/utf8>>,
          g(R, <<"home_team">>), g(R, <<"away_team">>),
          g(R, <<"home_goal">>), g(R, <<"away_goal">>),
          g(R, <<"season">>), g(R, <<"round">>),
          g(R, <<"datetime">>), undefined).

libertadores_row(R) ->
    match(<<"Libertadores">>,
          g(R, <<"home_team">>), g(R, <<"away_team">>),
          g(R, <<"home_goal">>), g(R, <<"away_goal">>),
          g(R, <<"season">>), undefined,
          g(R, <<"datetime">>), g(R, <<"stage">>)).

br_football_row(R) ->
    Date = parse_date(g(R, <<"date">>)),
    M = match(g(R, <<"tournament">>),
              g(R, <<"home">>), g(R, <<"away">>),
              g(R, <<"home_goal">>), g(R, <<"away_goal">>),
              undefined, undefined,
              g(R, <<"date">>), undefined),
    M#{season => season_from_date(Date),
       home_shots => parse_int(g(R, <<"home_shots">>)),
       away_shots => parse_int(g(R, <<"away_shots">>)),
       home_corner => parse_int(g(R, <<"home_corner">>)),
       away_corner => parse_int(g(R, <<"away_corner">>))}.

novo_row(R) ->
    match(<<"Brasileirão"/utf8>>,
          g(R, <<"Equipe_mandante">>), g(R, <<"Equipe_visitante">>),
          g(R, <<"Gols_mandante">>), g(R, <<"Gols_visitante">>),
          g(R, <<"Ano">>), g(R, <<"Rodada">>),
          g(R, <<"Data">>), undefined).

%% Build the canonical match map.
match(Comp, Home, Away, HG, AG, Season, Round, Date, Stage) ->
    #{competition => Comp,
      home => bsmcp_normalize:display_name(Home),
      away => bsmcp_normalize:display_name(Away),
      home_norm => bsmcp_normalize:normalize(Home),
      away_norm => bsmcp_normalize:normalize(Away),
      home_goal => parse_int(HG),
      away_goal => parse_int(AG),
      season => parse_int(Season),
      round => Round,
      date => parse_date(Date),
      stage => Stage}.

season_from_date(undefined) -> undefined;
season_from_date(<<Y:4/binary, _/binary>>) -> parse_int(Y);
season_from_date(_) -> undefined.

%% --- player transform -------------------------------------------------

player_row(R) ->
    #{id => g(R, <<"ID">>),
      name => g(R, <<"Name">>),
      age => parse_int(g(R, <<"Age">>)),
      nationality => g(R, <<"Nationality">>),
      overall => parse_int(g(R, <<"Overall">>)),
      potential => parse_int(g(R, <<"Potential">>)),
      club => g(R, <<"Club">>),
      club_norm => bsmcp_normalize:normalize(g(R, <<"Club">>)),
      position => g(R, <<"Position">>),
      jersey => g(R, <<"Jersey Number">>),
      name_norm => bsmcp_normalize:normalize(g(R, <<"Name">>)),
      nationality_norm => bsmcp_normalize:normalize(g(R, <<"Nationality">>))}.

%% --- file loading -----------------------------------------------------

default_dir() -> "data/kaggle".

%% @doc Load all match files in Dir into one flat list of canonical matches.
-spec load_matches(file:name_all()) -> [map()].
load_matches(Dir) ->
    dedup(lists:append(
            [load_match_file(filename:join(Dir, File), Fun)
             || {File, Fun} <- ?MATCH_FILES])).

%% @doc Remove duplicate fixtures that appear across overlapping source
%% files. Two rows are the same fixture when they share a (known) date and
%% the same home/away normalized teams; the first occurrence is kept so the
%% richer, canonically-named record wins.
-spec dedup([map()]) -> [map()].
dedup(Matches) ->
    {Kept, _Seen} =
        lists:foldl(
          fun(M, {Acc, Seen}) ->
                  case dedup_key(M) of
                      undefined ->
                          {[M | Acc], Seen};
                      Key ->
                          case maps:is_key(Key, Seen) of
                              true -> {Acc, Seen};
                              false -> {[M | Acc], Seen#{Key => true}}
                          end
                  end
          end, {[], #{}}, Matches),
    lists:reverse(Kept).

dedup_key(#{date := undefined}) -> undefined;
dedup_key(#{date := Date, home_norm := H, away_norm := A}) -> {Date, H, A}.

load_match_file(Path, Fun) ->
    case file:read_file(Path) of
        {ok, Bin} ->
            Rows = bsmcp_csv:parse_to_maps(Bin),
            [bsmcp_data:Fun(R) || R <- Rows];
        {error, _} ->
            []
    end.

%% @doc Load the FIFA player file into canonical player maps.
-spec load_players(file:name_all()) -> [map()].
load_players(Dir) ->
    Path = filename:join(Dir, "fifa_data.csv"),
    case file:read_file(Path) of
        {ok, Bin} ->
            Rows = bsmcp_csv:parse_to_maps(Bin),
            [player_row(R) || R <- Rows];
        {error, _} ->
            []
    end.

%% --- helpers ----------------------------------------------------------

g(Map, Key) -> maps:get(Key, Map, <<>>).
