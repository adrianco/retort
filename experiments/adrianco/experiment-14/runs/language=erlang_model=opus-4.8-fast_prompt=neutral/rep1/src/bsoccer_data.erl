%%% =====================================================================
%%% bsoccer_data — in-memory knowledge graph + data loader.
%%%
%%% A gen_server that, on startup, parses every provided CSV and materialises
%%% two ETS tables that form the knowledge graph the MCP tools query against:
%%%
%%%   bsoccer_matches : {Id, MatchMap}   — every match from the 5 match files,
%%%                                        normalised into one common shape.
%%%   bsoccer_players : {Id, PlayerMap}  — every FIFA player, selected fields.
%%%
%%% The tables are `protected`, so any process (e.g. the MCP request handler)
%%% can fold/scan them directly without copying the whole dataset per call;
%%% only this server writes to them. The match maps use a single canonical
%%% schema regardless of source file, with `source`/`competition` tags so the
%%% origin and tournament are still queryable, and `*_key` fields holding the
%%% accent-folded keys produced by bsoccer_util for robust name matching.
%%%
%%% Match schema (atom keys):
%%%   competition season round stage date date_tuple
%%%   home away home_key away_key home_goal away_goal source extra
%%% Player schema (atom keys):
%%%   id name name_key age nationality nationality_key overall potential
%%%   club club_key position jersey height weight foot skills
%%% =====================================================================
-module(bsoccer_data).
-behaviour(gen_server).

-export([start_link/0, start_link/1, ensure_started/0, ensure_started/1,
         matches_table/0, players_table/0, stats/0, default_data_dir/0]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(MATCHES, bsoccer_matches).
-define(PLAYERS, bsoccer_players).

%% --- public API -----------------------------------------------------------

start_link() -> start_link(default_data_dir()).

start_link(DataDir) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, DataDir, []).

%% Start the server once; safe to call repeatedly (idempotent).
ensure_started() -> ensure_started(default_data_dir()).

ensure_started(DataDir) ->
    case whereis(?MODULE) of
        undefined ->
            case start_link(DataDir) of
                {ok, Pid} -> {ok, Pid};
                {error, {already_started, Pid}} -> {ok, Pid}
            end;
        Pid ->
            {ok, Pid}
    end.

matches_table() -> ?MATCHES.
players_table() -> ?PLAYERS.

%% Summary counts used by the `data_summary` MCP tool and for diagnostics.
-spec stats() -> map().
stats() ->
    gen_server:call(?MODULE, stats, 30000).

%% Locate the bundled data directory relative to the current working dir.
default_data_dir() ->
    case os:getenv("BSOCCER_DATA_DIR") of
        false -> "data/kaggle";
        Dir -> Dir
    end.

%% --- gen_server callbacks -------------------------------------------------

init(DataDir) ->
    ?MATCHES = ets:new(?MATCHES, [named_table, set, protected, {read_concurrency, true}]),
    ?PLAYERS = ets:new(?PLAYERS, [named_table, set, protected, {read_concurrency, true}]),
    MatchCount = load_all_matches(DataDir),
    PlayerCount = load_players(DataDir),
    {ok, #{data_dir => DataDir, matches => MatchCount, players => PlayerCount}}.

handle_call(stats, _From, State) ->
    {reply, build_stats(State), State};
handle_call(_Req, _From, State) ->
    {reply, {error, unknown_request}, State}.

handle_cast(_Msg, State) -> {noreply, State}.
handle_info(_Info, State) -> {noreply, State}.
terminate(_Reason, _State) -> ok.

build_stats(State) ->
    Comps = ets:foldl(
              fun({_, M}, Acc) ->
                      C = maps:get(competition, M),
                      maps:update_with(C, fun(N) -> N + 1 end, 1, Acc)
              end, #{}, ?MATCHES),
    #{matches => maps:get(matches, State),
      players => maps:get(players, State),
      data_dir => list_to_binary(maps:get(data_dir, State)),
      matches_by_competition => Comps}.

%% --- match loading --------------------------------------------------------

load_all_matches(DataDir) ->
    Files = [{"Brasileirao_Matches.csv", fun row_brasileirao/1},
             {"Brazilian_Cup_Matches.csv", fun row_cup/1},
             {"Libertadores_Matches.csv", fun row_libertadores/1},
             {"BR-Football-Dataset.csv", fun row_br_football/1},
             {"novo_campeonato_brasileiro.csv", fun row_novo/1}],
    lists:foldl(
      fun({File, RowFun}, Counter) ->
              Path = filename:join(DataDir, File),
              case filelib:is_file(Path) of
                  true ->
                      Maps = bsoccer_csv:parse_file_as_maps(Path),
                      Src = list_to_binary(File),
                      lists:foldl(
                        fun(Row, Cnt) ->
                                case RowFun(Row) of
                                    skip -> Cnt;
                                    M0 ->
                                        M = M0#{source => Src},
                                        ets:insert(?MATCHES, {Cnt, M}),
                                        Cnt + 1
                                end
                        end, Counter, Maps);
                  false ->
                      io:format(standard_error, "warning: missing ~s~n", [Path]),
                      Counter
              end
      end, 0, Files).

%% Each row_* function turns a column-keyed map into the canonical match map,
%% or returns `skip` if the row is unusable.

row_brasileirao(R) ->
    base_match(#{competition => <<"Brasileirão Série A"/utf8>>,
                 home_raw => g(R, <<"home_team">>),
                 away_raw => g(R, <<"away_team">>),
                 home_goal => g(R, <<"home_goal">>),
                 away_goal => g(R, <<"away_goal">>),
                 season => g(R, <<"season">>),
                 round => g(R, <<"round">>),
                 stage => undefined,
                 date => g(R, <<"datetime">>),
                 extra => #{home_state => g(R, <<"home_team_state">>),
                            away_state => g(R, <<"away_team_state">>)}}).

row_cup(R) ->
    base_match(#{competition => <<"Copa do Brasil">>,
                 home_raw => g(R, <<"home_team">>),
                 away_raw => g(R, <<"away_team">>),
                 home_goal => g(R, <<"home_goal">>),
                 away_goal => g(R, <<"away_goal">>),
                 season => g(R, <<"season">>),
                 round => g(R, <<"round">>),
                 stage => undefined,
                 date => g(R, <<"datetime">>),
                 extra => #{}}).

row_libertadores(R) ->
    base_match(#{competition => <<"Copa Libertadores">>,
                 home_raw => g(R, <<"home_team">>),
                 away_raw => g(R, <<"away_team">>),
                 home_goal => g(R, <<"home_goal">>),
                 away_goal => g(R, <<"away_goal">>),
                 season => g(R, <<"season">>),
                 round => undefined,
                 stage => g(R, <<"stage">>),
                 date => g(R, <<"datetime">>),
                 extra => #{}}).

row_br_football(R) ->
    %% Column order is tournament,home,home_goal,away_goal,away,...
    Tournament = bsoccer_util:trim(g(R, <<"tournament">>)),
    Comp = case Tournament of
               <<>> -> <<"Brazilian Football">>;
               T -> normalise_tournament(T)
           end,
    base_match(#{competition => Comp,
                 home_raw => g(R, <<"home">>),
                 away_raw => g(R, <<"away">>),
                 home_goal => g(R, <<"home_goal">>),
                 away_goal => g(R, <<"away_goal">>),
                 season => undefined,        %% derived from date below
                 round => undefined,
                 stage => undefined,
                 date => g(R, <<"date">>),
                 extra => #{home_shots => bsoccer_util:parse_int(g(R, <<"home_shots">>)),
                            away_shots => bsoccer_util:parse_int(g(R, <<"away_shots">>)),
                            home_corner => bsoccer_util:parse_int(g(R, <<"home_corner">>)),
                            away_corner => bsoccer_util:parse_int(g(R, <<"away_corner">>))}}).

row_novo(R) ->
    base_match(#{competition => <<"Brasileirão Série A"/utf8>>,
                 home_raw => g(R, <<"Equipe_mandante">>),
                 away_raw => g(R, <<"Equipe_visitante">>),
                 home_goal => g(R, <<"Gols_mandante">>),
                 away_goal => g(R, <<"Gols_visitante">>),
                 season => g(R, <<"Ano">>),
                 round => g(R, <<"Rodada">>),
                 stage => undefined,
                 date => g(R, <<"Data">>),
                 extra => #{arena => bsoccer_util:trim(g(R, <<"Arena">>)),
                            home_state => g(R, <<"Mandante_UF">>),
                            away_state => g(R, <<"Visitante_UF">>)}}).

normalise_tournament(<<"Serie A">>) -> <<"Brasileirão Série A"/utf8>>;
normalise_tournament(<<"Serie B">>) -> <<"Brasileirão Série B"/utf8>>;
normalise_tournament(<<"Serie C">>) -> <<"Brasileirão Série C"/utf8>>;
normalise_tournament(Other) -> Other.

%% Build the canonical match map from a loosely-typed intermediate map.
base_match(In) ->
    HomeRaw = maps:get(home_raw, In),
    AwayRaw = maps:get(away_raw, In),
    Home = bsoccer_util:clean_team(HomeRaw),
    Away = bsoccer_util:clean_team(AwayRaw),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            {DateTuple, DateIso} = case bsoccer_util:parse_date(maps:get(date, In)) of
                                       {DT, Iso} -> {DT, Iso};
                                       undefined -> {undefined, undefined}
                                   end,
            Season = season_of(maps:get(season, In), DateTuple),
            #{competition => maps:get(competition, In),
              season => Season,
              round => norm_opt(maps:get(round, In)),
              stage => norm_opt(maps:get(stage, In)),
              date => DateIso,
              date_tuple => DateTuple,
              home => Home,
              away => Away,
              %% Fuzzy keys (suffix-stripped, accent-folded, aliased) for
              %% matching loose user queries to either side of a fixture.
              home_key => bsoccer_util:team_key(HomeRaw),
              away_key => bsoccer_util:team_key(AwayRaw),
              %% Precise identity keys that PRESERVE the state/country suffix,
              %% so clubs distinguished only by it (Atlético-MG vs Atlético-GO
              %% vs Atlético-PR) stay separate when building tables/records.
              home_ident => bsoccer_util:norm_key(HomeRaw),
              away_ident => bsoccer_util:norm_key(AwayRaw),
              %% Full display names with the suffix kept, for table labels.
              home_full => bsoccer_util:trim(bsoccer_util:to_binary(HomeRaw)),
              away_full => bsoccer_util:trim(bsoccer_util:to_binary(AwayRaw)),
              home_goal => bsoccer_util:parse_goal(maps:get(home_goal, In)),
              away_goal => bsoccer_util:parse_goal(maps:get(away_goal, In)),
              extra => maps:get(extra, In, #{})}
    end.

%% Use an explicit season value when present, else fall back to the year of
%% the parsed match date.
season_of(SeasonRaw, DateTuple) ->
    case bsoccer_util:parse_int(SeasonRaw) of
        I when is_integer(I) -> I;
        undefined ->
            case DateTuple of
                {Y, _, _} -> Y;
                _ -> undefined
            end
    end.

norm_opt(undefined) -> undefined;
norm_opt(V) ->
    case bsoccer_util:trim(V) of
        <<>> -> undefined;
        T -> T
    end.

%% --- player loading -------------------------------------------------------

load_players(DataDir) ->
    Path = filename:join(DataDir, "fifa_data.csv"),
    case filelib:is_file(Path) of
        true ->
            Maps = bsoccer_csv:parse_file_as_maps(Path),
            lists:foldl(
              fun(Row, Cnt) ->
                      case build_player(Row) of
                          skip -> Cnt;
                          P ->
                              ets:insert(?PLAYERS, {Cnt, P}),
                              Cnt + 1
                      end
              end, 0, Maps);
        false ->
            io:format(standard_error, "warning: missing ~s~n", [Path]),
            0
    end.

build_player(R) ->
    Name = bsoccer_util:trim(g(R, <<"Name">>)),
    case Name of
        <<>> -> skip;
        _ ->
            Club = bsoccer_util:trim(g(R, <<"Club">>)),
            Nat = bsoccer_util:trim(g(R, <<"Nationality">>)),
            #{id => bsoccer_util:parse_int(g(R, <<"ID">>)),
              name => Name,
              name_key => bsoccer_util:norm_key(Name),
              age => bsoccer_util:parse_int(g(R, <<"Age">>)),
              nationality => Nat,
              nationality_key => bsoccer_util:norm_key(Nat),
              overall => bsoccer_util:parse_int(g(R, <<"Overall">>)),
              potential => bsoccer_util:parse_int(g(R, <<"Potential">>)),
              club => Club,
              club_key => bsoccer_util:team_key(Club),
              position => bsoccer_util:trim(g(R, <<"Position">>)),
              jersey => bsoccer_util:parse_int(g(R, <<"Jersey Number">>)),
              height => bsoccer_util:trim(g(R, <<"Height">>)),
              weight => bsoccer_util:trim(g(R, <<"Weight">>)),
              foot => bsoccer_util:trim(g(R, <<"Preferred Foot">>)),
              skills => #{finishing => bsoccer_util:parse_int(g(R, <<"Finishing">>)),
                          dribbling => bsoccer_util:parse_int(g(R, <<"Dribbling">>)),
                          short_passing => bsoccer_util:parse_int(g(R, <<"ShortPassing">>)),
                          ball_control => bsoccer_util:parse_int(g(R, <<"BallControl">>)),
                          acceleration => bsoccer_util:parse_int(g(R, <<"Acceleration">>)),
                          sprint_speed => bsoccer_util:parse_int(g(R, <<"SprintSpeed">>)),
                          stamina => bsoccer_util:parse_int(g(R, <<"Stamina">>)),
                          strength => bsoccer_util:parse_int(g(R, <<"Strength">>))}}
    end.

%% --- helpers --------------------------------------------------------------

g(Row, Key) -> maps:get(Key, Row, <<>>).
