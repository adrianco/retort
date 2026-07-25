%% Loads the six Kaggle CSV files into ETS and owns them via a long-lived
%% holder process. Matches from all files are unified into one store with a
%% canonical team name per side; overlapping files (the two Brasileirão
%% sources, the extended stats file) are de-duplicated on
%% {date, home, away} so statistics are not double counted.
-module(bsmcp_data).

-export([ensure_loaded/0, load/1, stop/0, default_dir/0,
         matches/0, players/0, teams/0, team_display/1, summary/0]).

-define(HOLDER, bsmcp_data_holder).
-define(MATCHES, bsmcp_matches).
-define(PLAYERS, bsmcp_players).
-define(TEAMS, bsmcp_teams).
-define(KEYS, bsmcp_keys).
-define(META, bsmcp_meta).

%%% Public API ---------------------------------------------------------------

ensure_loaded() ->
    case ets:info(?MATCHES) of
        undefined -> load(default_dir());
        _ -> {ok, summary()}
    end.

default_dir() ->
    case os:getenv("BSMCP_DATA_DIR") of
        false -> "data/kaggle";
        Dir -> Dir
    end.

load(Dir) ->
    stop(),
    Caller = self(),
    Ref = make_ref(),
    {Pid, MRef} = spawn_monitor(fun() -> holder_init(Caller, Ref, Dir) end),
    receive
        {Ref, ok} ->
            erlang:demonitor(MRef, [flush]),
            {ok, summary()};
        {'DOWN', MRef, process, Pid, Reason} ->
            {error, Reason}
    after 300000 ->
        exit(Pid, kill),
        {error, timeout}
    end.

stop() ->
    case whereis(?HOLDER) of
        undefined -> ok;
        Pid ->
            MRef = monitor(process, Pid),
            exit(Pid, kill),
            receive {'DOWN', MRef, process, Pid, _} -> ok end
    end.

-spec matches() -> [map()].
matches() ->
    [M || {_, M} <- ets:tab2list(?MATCHES)].

-spec players() -> [map()].
players() ->
    [P || {_, P} <- ets:tab2list(?PLAYERS)].

%% [{CanonicalName, DisplayName}]
teams() ->
    ets:tab2list(?TEAMS).

team_display(Canon) ->
    case ets:lookup(?TEAMS, Canon) of
        [{_, Display}] -> Display;
        [] -> Canon
    end.

summary() ->
    #{matches => ets:info(?MATCHES, size),
      players => ets:info(?PLAYERS, size),
      teams => ets:info(?TEAMS, size),
      duplicates_skipped => meta(duplicates, 0),
      files => meta(files, #{}),
      data_dir => meta(data_dir, undefined)}.

meta(Key, Default) ->
    case ets:lookup(?META, Key) of
        [{_, V}] -> V;
        [] -> Default
    end.

%%% Holder process ------------------------------------------------------------

holder_init(Caller, Ref, Dir) ->
    register(?HOLDER, self()),
    Opts = [named_table, public, set, {read_concurrency, true}],
    ets:new(?MATCHES, Opts),
    ets:new(?PLAYERS, Opts),
    ets:new(?TEAMS, Opts),
    ets:new(?KEYS, Opts),
    ets:new(?META, Opts),
    do_load(Dir),
    Caller ! {Ref, ok},
    holder_loop().

holder_loop() ->
    receive stop -> ok end.

%%% Loading -------------------------------------------------------------------

do_load(Dir) ->
    ets:insert(?META, {data_dir, unicode:characters_to_binary(Dir)}),
    Files =
        [{"Brasileirao_Matches.csv", fun load_brasileirao/1},
         {"novo_campeonato_brasileiro.csv", fun load_historical/1},
         {"Brazilian_Cup_Matches.csv", fun load_cup/1},
         {"Libertadores_Matches.csv", fun load_libertadores/1},
         {"BR-Football-Dataset.csv", fun load_extended/1},
         {"fifa_data.csv", fun load_players/1}],
    Counts = [{unicode:characters_to_binary(Name),
               Loader(filename:join(Dir, Name))}
              || {Name, Loader} <- Files],
    ets:insert(?META, {files, maps:from_list(Counts)}).

%% Header row -> #{ColumnName => Index}; data rows become tuples for O(1) access.
parse_with_header(Path) ->
    [Header | Rows] = bsmcp_csv:parse_file(Path),
    Cols = maps:from_list(lists:zip(Header, lists:seq(1, length(Header)))),
    {Cols, [list_to_tuple(R) || R <- Rows]}.

field(Cols, Name, Row) ->
    case Cols of
        #{Name := I} when I =< tuple_size(Row) -> element(I, Row);
        _ -> <<>>
    end.

load_brasileirao(Path) ->
    {Cols, Rows} = parse_with_header(Path),
    F = fun(N, R) -> field(Cols, N, R) end,
    lists:foldl(
      fun(R, Acc) ->
              Acc + add_match(#{
                  competition => <<"Brasileirão Série A"/utf8>>,
                  source => <<"Brasileirao_Matches.csv">>,
                  date => bsmcp_names:parse_date(F(<<"datetime">>, R)),
                  season => to_int(F(<<"season">>, R)),
                  round => to_int(F(<<"round">>, R)),
                  stage => undefined,
                  home => F(<<"home_team">>, R),
                  away => F(<<"away_team">>, R),
                  hg => to_int(F(<<"home_goal">>, R)),
                  ag => to_int(F(<<"away_goal">>, R)),
                  arena => undefined,
                  extra => #{}})
      end, 0, Rows).

load_historical(Path) ->
    {Cols, Rows} = parse_with_header(Path),
    F = fun(N, R) -> field(Cols, N, R) end,
    lists:foldl(
      fun(R, Acc) ->
              Acc + add_match(#{
                  competition => <<"Brasileirão Série A"/utf8>>,
                  source => <<"novo_campeonato_brasileiro.csv">>,
                  date => bsmcp_names:parse_date(F(<<"Data">>, R)),
                  season => to_int(F(<<"Ano">>, R)),
                  round => to_int(F(<<"Rodada">>, R)),
                  stage => undefined,
                  home => F(<<"Equipe_mandante">>, R),
                  away => F(<<"Equipe_visitante">>, R),
                  hg => to_int(F(<<"Gols_mandante">>, R)),
                  ag => to_int(F(<<"Gols_visitante">>, R)),
                  arena => nonempty(F(<<"Arena">>, R)),
                  extra => #{}})
      end, 0, Rows).

load_cup(Path) ->
    {Cols, Rows} = parse_with_header(Path),
    F = fun(N, R) -> field(Cols, N, R) end,
    %% The cup file only has numeric rounds; the highest round of each season
    %% is the final, which we label so "find the finals" queries work.
    MaxRound = lists:foldl(
                 fun(R, Acc) ->
                         S = to_int(F(<<"season">>, R)),
                         Rd = to_int(F(<<"round">>, R)),
                         case {S, Rd} of
                             {undefined, _} -> Acc;
                             {_, undefined} -> Acc;
                             _ -> maps:update_with(S, fun(V) -> max(V, Rd) end,
                                                   Rd, Acc)
                         end
                 end, #{}, Rows),
    lists:foldl(
      fun(R, Acc) ->
              S = to_int(F(<<"season">>, R)),
              Rd = to_int(F(<<"round">>, R)),
              Stage = case maps:get(S, MaxRound, undefined) of
                          Rd when Rd =/= undefined -> <<"final">>;
                          _ -> undefined
                      end,
              Acc + add_match(#{
                  competition => <<"Copa do Brasil">>,
                  source => <<"Brazilian_Cup_Matches.csv">>,
                  date => bsmcp_names:parse_date(F(<<"datetime">>, R)),
                  season => S,
                  round => Rd,
                  stage => Stage,
                  home => F(<<"home_team">>, R),
                  away => F(<<"away_team">>, R),
                  hg => to_int(F(<<"home_goal">>, R)),
                  ag => to_int(F(<<"away_goal">>, R)),
                  arena => undefined,
                  extra => #{}})
      end, 0, Rows).

load_libertadores(Path) ->
    {Cols, Rows} = parse_with_header(Path),
    F = fun(N, R) -> field(Cols, N, R) end,
    lists:foldl(
      fun(R, Acc) ->
              Acc + add_match(#{
                  competition => <<"Copa Libertadores">>,
                  source => <<"Libertadores_Matches.csv">>,
                  date => bsmcp_names:parse_date(F(<<"datetime">>, R)),
                  season => to_int(F(<<"season">>, R)),
                  round => undefined,
                  stage => nonempty(F(<<"stage">>, R)),
                  home => F(<<"home_team">>, R),
                  away => F(<<"away_team">>, R),
                  hg => to_int(F(<<"home_goal">>, R)),
                  ag => to_int(F(<<"away_goal">>, R)),
                  arena => undefined,
                  extra => #{}})
      end, 0, Rows).

load_extended(Path) ->
    {Cols, Rows} = parse_with_header(Path),
    F = fun(N, R) -> field(Cols, N, R) end,
    lists:foldl(
      fun(R, Acc) ->
              Date = bsmcp_names:parse_date(F(<<"date">>, R)),
              Season = case Date of
                           {Y, _, _} -> Y;
                           undefined -> undefined
                       end,
              Extra = maps:filter(
                        fun(_, V) -> V =/= undefined end,
                        #{home_corners => to_int(F(<<"home_corner">>, R)),
                          away_corners => to_int(F(<<"away_corner">>, R)),
                          home_shots => to_int(F(<<"home_shots">>, R)),
                          away_shots => to_int(F(<<"away_shots">>, R)),
                          home_attacks => to_int(F(<<"home_attack">>, R)),
                          away_attacks => to_int(F(<<"away_attack">>, R))}),
              Acc + add_match(#{
                  competition => extended_tournament(F(<<"tournament">>, R)),
                  source => <<"BR-Football-Dataset.csv">>,
                  date => Date,
                  season => Season,
                  round => undefined,
                  stage => undefined,
                  home => F(<<"home">>, R),
                  away => F(<<"away">>, R),
                  hg => to_int(F(<<"home_goal">>, R)),
                  ag => to_int(F(<<"away_goal">>, R)),
                  arena => undefined,
                  extra => Extra})
      end, 0, Rows).

extended_tournament(T) ->
    case bsmcp_names:norm_text(T) of
        <<"serie a">> -> <<"Brasileirão Série A"/utf8>>;
        <<"serie b">> -> <<"Série B"/utf8>>;
        <<"serie c">> -> <<"Série C"/utf8>>;
        <<"copa do brasil">> -> <<"Copa do Brasil">>;
        _ -> T
    end.

%% Insert one match unless home/away are missing or it duplicates an already
%% loaded match: same geo-stripped canonical team pair within +/- 1 day
%% (sources disagree by a day on some kick-off dates due to timezones).
add_match(#{home := H, away := A}) when H =:= <<>>; A =:= <<>> ->
    0;
add_match(M = #{home := H, away := A, date := Date}) ->
    HC = bsmcp_names:canonical(H),
    AC = bsmcp_names:canonical(A),
    Days = case Date of
               undefined -> undefined;
               _ -> calendar:date_to_gregorian_days(Date)
           end,
    Pair = {bsmcp_names:strip_geo(HC), bsmcp_names:strip_geo(AC)},
    Dup = Days =/= undefined andalso
        lists:any(fun(D) -> ets:member(?KEYS, {D, Pair}) end,
                  [Days - 1, Days, Days + 1]),
    case Dup of
        true ->
            ets:update_counter(?META, duplicates, 1, {duplicates, 0}),
            0;
        false ->
            Days =/= undefined andalso ets:insert(?KEYS, {{Days, Pair}}),
            record_team(HC, H),
            record_team(AC, A),
            Id = ets:update_counter(?META, next_id, 1, {next_id, 0}),
            ets:insert(?MATCHES,
                       {Id, M#{id => Id, home_canon => HC, away_canon => AC}}),
            1
    end.

record_team(Canon, Display) ->
    %% Keep the shortest display name seen for a canonical team, so
    %% "Grêmio" wins over "Grêmio - RS".
    Clean = clean_display(Display),
    case ets:lookup(?TEAMS, Canon) of
        [] -> ets:insert(?TEAMS, {Canon, Clean});
        [{_, Old}] when byte_size(Clean) < byte_size(Old) ->
            ets:insert(?TEAMS, {Canon, Clean});
        _ -> ok
    end.

clean_display(Name) ->
    unicode:characters_to_binary(string:trim(Name)).

load_players(Path) ->
    {Cols, Rows} = parse_with_header(Path),
    F = fun(N, R) -> field(Cols, N, R) end,
    lists:foldl(
      fun(R, Acc) ->
              Name = F(<<"Name">>, R),
              case Name of
                  <<>> -> Acc;
                  _ ->
                      Id = ets:update_counter(?META, next_player_id, 1,
                                              {next_player_id, 0}),
                      P = #{id => Id,
                            fifa_id => to_int(F(<<"ID">>, R)),
                            name => Name,
                            name_canon => bsmcp_names:norm_text(Name),
                            age => to_int(F(<<"Age">>, R)),
                            nationality => F(<<"Nationality">>, R),
                            nat_canon => bsmcp_names:norm_text(F(<<"Nationality">>, R)),
                            overall => to_int(F(<<"Overall">>, R)),
                            potential => to_int(F(<<"Potential">>, R)),
                            club => F(<<"Club">>, R),
                            club_canon => bsmcp_names:norm_text(F(<<"Club">>, R)),
                            position => F(<<"Position">>, R),
                            jersey => to_int(F(<<"Jersey Number">>, R)),
                            height => F(<<"Height">>, R),
                            weight => F(<<"Weight">>, R),
                            value => F(<<"Value">>, R),
                            wage => F(<<"Wage">>, R),
                            foot => F(<<"Preferred Foot">>, R)},
                      ets:insert(?PLAYERS, {Id, P}),
                      Acc + 1
              end
      end, 0, Rows).

%%% Value parsing --------------------------------------------------------------

nonempty(<<>>) -> undefined;
nonempty(B) -> B.

%% "2" -> 2, "1.0" -> 1, "" -> undefined
to_int(<<>>) ->
    undefined;
to_int(B) ->
    S = string:trim(B),
    try binary_to_integer(S)
    catch
        _:_ ->
            try round(binary_to_float(S))
            catch _:_ -> undefined
            end
    end.
