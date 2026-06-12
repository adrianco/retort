%%% ===================================================================
%%% Brazilian Soccer MCP Server - dataset loader & in-memory store
%%%
%%% Context: A gen_server that, at startup, reads the six Kaggle CSV
%%% files from the configured data directory and loads them into two
%%% public ETS tables:
%%%   * bsoccer_matches  - one entry per match (all competitions),
%%%   * bsoccer_players  - one entry per FIFA player.
%%% The query layer (`bsoccer_query') reads these tables directly for
%%% speed; this process owns the tables and the load lifecycle.
%%%
%%% Competition labelling (chosen to avoid double-counting the two
%%% overlapping Brasileirão sources, see brazilian-soccer-mcp-guide.md
%%% "Data Quality Notes"):
%%%   Brasileirao_Matches.csv           -> "Brasileirão Série A" (2012-2022)
%%%   novo_campeonato_brasileiro.csv     -> "Brasileirão Série A" for
%%%        seasons < 2012, else "Campeonato Brasileiro (histórico)"
%%%        so the 2012-2019 rows remain loadable/queryable but do not
%%%        double the Série A figures.
%%%   Brazilian_Cup_Matches.csv          -> "Copa do Brasil"
%%%   Libertadores_Matches.csv           -> "Copa Libertadores"
%%%   BR-Football-Dataset.csv            -> "BR Football — <tournament>"
%%%
%%% A match map has keys: competition, source, season, date, round,
%%% stage, home, away, home_goal, away_goal (+ extended stats where the
%%% source provides them). Dates are normalised to ISO "YYYY-MM-DD".
%%% ===================================================================
-module(bsoccer_data).
-behaviour(gen_server).

-export([start_link/1, ready/0, matches_table/0, players_table/0, stats/0]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(MATCHES, bsoccer_matches).
-define(PLAYERS, bsoccer_players).

%%% -------------------------------------------------------------------
%%% Public API
%%% -------------------------------------------------------------------

start_link(DataDir) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, DataDir, []).

%% Block until the (synchronous) load has completed.
ready() ->
    gen_server:call(?MODULE, ready, infinity).

matches_table() -> ?MATCHES.
players_table() -> ?PLAYERS.

%% Quick counts, handy for diagnostics.
stats() ->
    #{matches => ets:info(?MATCHES, size),
      players => ets:info(?PLAYERS, size)}.

%%% -------------------------------------------------------------------
%%% gen_server callbacks
%%% -------------------------------------------------------------------

init(DataDir) ->
    ?MATCHES = ets:new(?MATCHES, [named_table, set, public, {read_concurrency, true}]),
    ?PLAYERS = ets:new(?PLAYERS, [named_table, set, public, {read_concurrency, true}]),
    ok = load_all(DataDir),
    {ok, #{data_dir => DataDir}}.

handle_call(ready, _From, State) ->
    {reply, ok, State};
handle_call(_Req, _From, State) ->
    {reply, {error, unknown}, State}.

handle_cast(_Msg, State) -> {noreply, State}.
handle_info(_Info, State) -> {noreply, State}.
terminate(_Reason, _State) -> ok.

%%% -------------------------------------------------------------------
%%% Loading
%%% -------------------------------------------------------------------

load_all(DataDir) ->
    Counter = counters:new(1, [atomics]),
    load_brasileirao(DataDir, Counter),
    load_novo(DataDir, Counter),
    load_cup(DataDir, Counter),
    load_libertadores(DataDir, Counter),
    load_brfootball(DataDir, Counter),
    load_players(DataDir),
    ok.

insert_match(Counter, Match) ->
    Id = counters:get(Counter, 1),
    counters:add(Counter, 1, 1),
    ets:insert(?MATCHES, {Id, Match}).

with_file(DataDir, File, Fun) ->
    Path = filename:join(DataDir, File),
    case bsoccer_csv:parse_file(Path) of
        {ok, {_Header, Rows}} -> lists:foreach(Fun, Rows);
        {error, Reason} ->
            error_logger:warning_msg("bsoccer: could not load ~s: ~p~n", [Path, Reason]),
            ok
    end.

load_brasileirao(DataDir, Counter) ->
    with_file(DataDir, "Brasileirao_Matches.csv",
      fun(R) ->
          case match_from(R, <<"datetime">>, <<"home_team">>, <<"away_team">>,
                          <<"home_goal">>, <<"away_goal">>, <<"season">>) of
              {ok, M0} ->
                  M = M0#{competition => <<"Brasileirão Série A"/utf8>>,
                          source => brasileirao,
                          round => maps:get(<<"round">>, R, <<>>)},
                  insert_match(Counter, M);
              skip -> ok
          end
      end).

load_novo(DataDir, Counter) ->
    with_file(DataDir, "novo_campeonato_brasileiro.csv",
      fun(R) ->
          Home = suffix_uf(cell(R, <<"Equipe_mandante">>), cell(R, <<"Mandante_UF">>)),
          Away = suffix_uf(cell(R, <<"Equipe_visitante">>), cell(R, <<"Visitante_UF">>)),
          case {parse_int(cell(R, <<"Gols_mandante">>)),
                parse_int(cell(R, <<"Gols_visitante">>)),
                parse_int(cell(R, <<"Ano">>))} of
              {{ok, HG}, {ok, AG}, {ok, Season}} when Home =/= <<>>, Away =/= <<>> ->
                  Comp = case Season < 2012 of
                             true -> <<"Brasileirão Série A"/utf8>>;
                             false -> <<"Campeonato Brasileiro (histórico)"/utf8>>
                         end,
                  M = #{competition => Comp, source => novo, season => Season,
                        date => normalise_date(cell(R, <<"Data">>)),
                        round => cell(R, <<"Rodada">>), stage => <<>>,
                        home => Home, away => Away,
                        home_goal => HG, away_goal => AG,
                        arena => cell(R, <<"Arena">>)},
                  insert_match(Counter, M);
              _ -> ok
          end
      end).

load_cup(DataDir, Counter) ->
    with_file(DataDir, "Brazilian_Cup_Matches.csv",
      fun(R) ->
          case match_from(R, <<"datetime">>, <<"home_team">>, <<"away_team">>,
                          <<"home_goal">>, <<"away_goal">>, <<"season">>) of
              {ok, M0} ->
                  M = M0#{competition => <<"Copa do Brasil"/utf8>>,
                          source => cup,
                          round => maps:get(<<"round">>, R, <<>>)},
                  insert_match(Counter, M);
              skip -> ok
          end
      end).

load_libertadores(DataDir, Counter) ->
    with_file(DataDir, "Libertadores_Matches.csv",
      fun(R) ->
          case match_from(R, <<"datetime">>, <<"home_team">>, <<"away_team">>,
                          <<"home_goal">>, <<"away_goal">>, <<"season">>) of
              {ok, M0} ->
                  M = M0#{competition => <<"Copa Libertadores"/utf8>>,
                          source => libertadores,
                          stage => maps:get(<<"stage">>, R, <<>>)},
                  insert_match(Counter, M);
              skip -> ok
          end
      end).

load_brfootball(DataDir, Counter) ->
    with_file(DataDir, "BR-Football-Dataset.csv",
      fun(R) ->
          Tournament = cell(R, <<"tournament">>),
          case {parse_int(cell(R, <<"home_goal">>)),
                parse_int(cell(R, <<"away_goal">>))} of
              {{ok, HG}, {ok, AG}} ->
                  Comp = <<"BR Football — "/utf8, Tournament/binary>>,
                  M = #{competition => Comp, source => brfootball,
                        season => season_from_date(cell(R, <<"date">>)),
                        date => normalise_date(cell(R, <<"date">>)),
                        round => <<>>, stage => <<>>,
                        home => cell(R, <<"home">>), away => cell(R, <<"away">>),
                        home_goal => HG, away_goal => AG,
                        home_shots => parse_num(cell(R, <<"home_shots">>)),
                        away_shots => parse_num(cell(R, <<"away_shots">>)),
                        home_corner => parse_num(cell(R, <<"home_corner">>)),
                        away_corner => parse_num(cell(R, <<"away_corner">>))},
                  insert_match(Counter, M);
              _ -> ok
          end
      end).

%% Build a generic match map from the "ricardomattos05" family of files.
match_from(R, DateK, HomeK, AwayK, HGK, AGK, SeasonK) ->
    Home = cell(R, HomeK),
    Away = cell(R, AwayK),
    case {parse_int(cell(R, HGK)), parse_int(cell(R, AGK))} of
        {{ok, HG}, {ok, AG}} when Home =/= <<>>, Away =/= <<>> ->
            {ok, #{season => season_or_undefined(cell(R, SeasonK)),
                   date => normalise_date(cell(R, DateK)),
                   round => <<>>, stage => <<>>,
                   home => Home, away => Away,
                   home_goal => HG, away_goal => AG}};
        _ ->
            skip
    end.

%%% -------------------------------------------------------------------
%%% Players
%%% -------------------------------------------------------------------

load_players(DataDir) ->
    Path = filename:join(DataDir, "fifa_data.csv"),
    case bsoccer_csv:parse_file(Path) of
        {ok, {_Header, Rows}} ->
            lists:foldl(
              fun(R, Id) ->
                  case cell(R, <<"Name">>) of
                      <<>> -> Id;
                      Name ->
                          P = #{name => Name,
                                age => parse_int_default(cell(R, <<"Age">>), 0),
                                nationality => cell(R, <<"Nationality">>),
                                overall => parse_int_default(cell(R, <<"Overall">>), 0),
                                potential => parse_int_default(cell(R, <<"Potential">>), 0),
                                club => cell(R, <<"Club">>),
                                position => cell(R, <<"Position">>),
                                jersey => cell(R, <<"Jersey Number">>)},
                          ets:insert(?PLAYERS, {Id, P}),
                          Id + 1
                  end
              end, 0, Rows),
            ok;
        {error, Reason} ->
            error_logger:warning_msg("bsoccer: could not load players: ~p~n", [Reason]),
            ok
    end.

%%% -------------------------------------------------------------------
%%% Field helpers
%%% -------------------------------------------------------------------

cell(R, K) ->
    case maps:get(K, R, <<>>) of
        V when is_binary(V) -> string:trim(V);
        V -> V
    end.

%% Append "-UF" to a bare team name when a non-empty state code exists,
%% matching the "Flamengo-RJ" convention used by the other files.
suffix_uf(<<>>, _) -> <<>>;
suffix_uf(Name, <<>>) -> Name;
suffix_uf(Name, UF) ->
    <<Name/binary, "-", UF/binary>>.

%% Parse an integer that may be written as "3", "3.0" or " 3 ".
parse_int(Bin) when is_binary(Bin) ->
    case string:trim(Bin) of
        <<>> -> error;
        S ->
            case string:to_integer(S) of
                {Int, <<>>} -> {ok, Int};
                {Int, <<".", _/binary>>} -> {ok, Int};   %% "1.0"
                _ -> error
            end
    end;
parse_int(_) -> error.

parse_int_default(Bin, Default) ->
    case parse_int(Bin) of
        {ok, I} -> I;
        error -> Default
    end.

%% Parse a number into a float (extended stats), 0.0 if absent.
parse_num(Bin) ->
    case string:trim(Bin) of
        <<>> -> 0.0;
        S ->
            try binary_to_float(S)
            catch _:_ ->
                case string:to_integer(S) of
                    {I, _} when is_integer(I) -> float(I);
                    _ -> 0.0
                end
            end
    end.

season_or_undefined(Bin) ->
    case parse_int(Bin) of
        {ok, I} -> I;
        error -> undefined
    end.

%% Normalise the various date spellings to ISO "YYYY-MM-DD".
normalise_date(Bin) ->
    S = string:trim(Bin),
    case S of
        <<>> -> <<>>;
        <<Y:4/binary, "-", M:2/binary, "-", D:2/binary, _/binary>> ->
            <<Y/binary, "-", M/binary, "-", D/binary>>;   %% ISO (+ optional time)
        <<D:2/binary, "/", M:2/binary, "/", Y:4/binary>> ->
            <<Y/binary, "-", M/binary, "-", D/binary>>;   %% DD/MM/YYYY
        Other -> Other
    end.

season_from_date(Bin) ->
    case normalise_date(Bin) of
        <<Y:4/binary, _/binary>> ->
            case parse_int(Y) of
                {ok, I} -> I;
                error -> undefined
            end;
        _ -> undefined
    end.
