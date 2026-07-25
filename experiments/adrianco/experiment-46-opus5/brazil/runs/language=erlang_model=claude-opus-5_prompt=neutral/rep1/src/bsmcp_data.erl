%%%-------------------------------------------------------------------
%%% @doc Dataset loader and in-memory knowledge graph.
%%%
%%% Context: a gen_server owns a set of public named ETS tables that act
%%% as the knowledge graph: match nodes, team nodes, player nodes and
%%% the edges between them (team -> matches, competition+season ->
%%% matches, club -> players, name token -> players).  Queries run in
%%% the caller process straight against ETS, so a lookup never queues
%%% behind the loader and answers come back in single-digit
%%% milliseconds.
%%%
%%% Two things are worth knowing about the load:
%%%
%%%   * Team names are canonicalised with {@link bsmcp_names}.  A key
%%%     that occurs with several states in the corpus (Botafogo RJ/SP/PB)
%%%     stays split; a bare occurrence of such a key is attached to its
%%%     most frequent state, which is how the Libertadores file's
%%%     "Botafogo" becomes Botafogo-RJ.
%%%   * The sources overlap heavily: Brasileirão 2012-2022 also lives in
%%%     novo_campeonato (2003-2019) and in BR-Football (2014-2023).
%%%     Matches are therefore de-duplicated on
%%%     {competition, season, home, away} and *merged*, so a fixture
%%%     contributes its round from one file, its stadium from another
%%%     and its shot/corner counts from a third, while a season table is
%%%     still computed from each fixture exactly once.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_data).
-behaviour(gen_server).

-export([start_link/0, start_link/1, load/1, ensure_loaded/0, reload/0,
         data_dir/0, status/0,
         match/1, matches/0, fold_matches/2,
         team/1, teams/0, resolve_team/1, resolve_team_all/1, search_teams/1,
         team_match_ids/1, competition_match_ids/2,
         competitions/0, competition_name/1, seasons/1,
         player/1, players/0, fold_players/2, players_by_nationality/1,
         players_by_club/1, players_by_token/1]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(SERVER, ?MODULE).
-define(T_MATCH, bsmcp_match).
-define(T_TEAM, bsmcp_team).
-define(T_TEAM_LOOKUP, bsmcp_team_lookup).
-define(T_TEAM_KEY, bsmcp_team_key).
-define(T_TEAM_MATCH, bsmcp_team_match).
-define(T_COMP_MATCH, bsmcp_comp_match).
-define(T_PLAYER, bsmcp_player).
-define(T_PLAYER_TOKEN, bsmcp_player_token).
-define(T_CLUB_PLAYER, bsmcp_club_player).
-define(T_NAT_PLAYER, bsmcp_nat_player).
-define(T_META, bsmcp_meta).

-define(TABLES, [?T_MATCH, ?T_TEAM, ?T_TEAM_LOOKUP, ?T_TEAM_KEY, ?T_TEAM_MATCH,
                 ?T_COMP_MATCH, ?T_PLAYER, ?T_PLAYER_TOKEN, ?T_CLUB_PLAYER,
                 ?T_NAT_PLAYER, ?T_META]).

-define(BAGS, [?T_TEAM_KEY, ?T_TEAM_MATCH, ?T_COMP_MATCH, ?T_PLAYER_TOKEN,
               ?T_CLUB_PLAYER, ?T_NAT_PLAYER]).

%% source file -> {source tag, priority}. Lower priority number wins on
%% conflicting values when duplicate fixtures are merged.
-define(SOURCES,
        [{"Brasileirao_Matches.csv", brasileirao, 1},
         {"Brazilian_Cup_Matches.csv", brazilian_cup, 1},
         {"Libertadores_Matches.csv", libertadores, 1},
         {"novo_campeonato_brasileiro.csv", novo_campeonato, 2},
         {"BR-Football-Dataset.csv", br_football, 3}]).

-define(PLAYER_FILE, "fifa_data.csv").

%%====================================================================
%% API
%%====================================================================

start_link() -> start_link(#{}).

start_link(Opts) when is_map(Opts) ->
    gen_server:start_link({local, ?SERVER}, ?MODULE, Opts, []).

%% @doc Start the application (and therefore load the data) if needed.
ensure_loaded() ->
    case whereis(?SERVER) of
        undefined ->
            {ok, _} = application:ensure_all_started(bsmcp),
            ok;
        _ ->
            ok
    end.

reload() -> gen_server:call(?SERVER, reload, 120000).

status() -> meta(status, #{}).

-spec data_dir() -> file:filename().
data_dir() ->
    case application:get_env(bsmcp, data_dir) of
        {ok, Dir} ->
            Dir;
        undefined ->
            case os:getenv("BSMCP_DATA_DIR") of
                false -> discover_data_dir();
                Dir -> Dir
            end
    end.

%%--------------------------------------------------------------------
%% Matches
%%--------------------------------------------------------------------

-spec match(integer()) -> map() | undefined.
match(Id) ->
    case ets:lookup(?T_MATCH, Id) of
        [{_, M}] -> M;
        [] -> undefined
    end.

-spec matches() -> [map()].
matches() -> [M || {_, M} <- ets:tab2list(?T_MATCH)].

fold_matches(Fun, Acc0) ->
    ets:foldl(fun({_, M}, Acc) -> Fun(M, Acc) end, Acc0, ?T_MATCH).

team_match_ids(TeamId) ->
    [Id || {_, Id} <- ets:lookup(?T_TEAM_MATCH, TeamId)].

competition_match_ids(CompKey, Season) ->
    [Id || {_, Id} <- ets:lookup(?T_COMP_MATCH, {CompKey, Season})].

%%--------------------------------------------------------------------
%% Teams
%%--------------------------------------------------------------------

-spec team(binary()) -> map() | undefined.
team(TeamId) ->
    case ets:lookup(?T_TEAM, TeamId) of
        [{_, T}] -> T;
        [] -> undefined
    end.

teams() -> [T || {_, T} <- ets:tab2list(?T_TEAM)].

%% @doc Best team for a user supplied name, e.g. <<"sao paulo fc">>.
-spec resolve_team(binary()) -> map() | undefined.
resolve_team(Name) ->
    case resolve_team_all(Name) of
        [] -> undefined;
        [T | _] -> T
    end.

%% @doc All plausible teams for a name, best first (most matches played).
-spec resolve_team_all(binary()) -> [map()].
resolve_team_all(Name) when is_binary(Name) ->
    {Key, State, _Core} = bsmcp_names:resolve(Name),
    Exact = case ets:lookup(?T_TEAM_LOOKUP, {Key, State}) of
                [{_, Id}] -> [team(Id)];
                [] -> []
            end,
    case Exact of
        [_ | _] ->
            Exact;
        [] ->
            ByKey = [team(Id) || {_, Id} <- ets:lookup(?T_TEAM_KEY, Key)],
            case ByKey of
                [_ | _] -> sort_teams(ByKey);
                [] -> search_teams(Name)
            end
    end;
resolve_team_all(Name) ->
    resolve_team_all(bsmcp_text:bin(Name)).

%% @doc Substring search over team keys and display names.
-spec search_teams(binary()) -> [map()].
search_teams(Query) ->
    Norm = bsmcp_text:normalize(Query),
    case Norm of
        <<>> ->
            [];
        _ ->
            sort_teams([T || T <- teams(), team_matches_query(T, Norm)])
    end.

team_matches_query(#{key := Key, name := Name, variants := Vs}, Norm) ->
    binary:match(Key, Norm) =/= nomatch
        orelse binary:match(bsmcp_text:normalize(Name), Norm) =/= nomatch
        orelse lists:any(fun(V) ->
                                 binary:match(bsmcp_text:normalize(V), Norm) =/= nomatch
                         end, Vs).

sort_teams(Teams) ->
    lists:sort(fun(#{match_count := A, id := IdA}, #{match_count := B, id := IdB}) ->
                       {B, IdA} =< {A, IdB}
               end, [T || T <- Teams, T =/= undefined]).

%%--------------------------------------------------------------------
%% Competitions
%%--------------------------------------------------------------------

competitions() -> meta(competitions, []).

competition_name(Key) ->
    maps:get(Key, competition_names(), bsmcp_text:bin(Key)).

competition_names() ->
    #{serie_a => <<"Brasileirão Série A"/utf8>>,
      serie_b => <<"Brasileirão Série B"/utf8>>,
      serie_c => <<"Brasileirão Série C"/utf8>>,
      copa_do_brasil => <<"Copa do Brasil">>,
      libertadores => <<"Copa Libertadores">>}.

seasons(CompKey) ->
    maps:get(CompKey, meta(seasons, #{}), []).

%%--------------------------------------------------------------------
%% Players
%%--------------------------------------------------------------------

player(Id) ->
    case ets:lookup(?T_PLAYER, Id) of
        [{_, P}] -> P;
        [] -> undefined
    end.

players() -> [P || {_, P} <- ets:tab2list(?T_PLAYER)].

fold_players(Fun, Acc0) ->
    ets:foldl(fun({_, P}, Acc) -> Fun(P, Acc) end, Acc0, ?T_PLAYER).

players_by_nationality(Nat) ->
    ids_to_players(?T_NAT_PLAYER, bsmcp_text:normalize(Nat)).

players_by_club(ClubKey) ->
    ids_to_players(?T_CLUB_PLAYER, ClubKey).

players_by_token(Token) ->
    ids_to_players(?T_PLAYER_TOKEN, bsmcp_text:normalize(Token)).

ids_to_players(Tab, Key) ->
    [player(Id) || {_, Id} <- ets:lookup(Tab, Key)].

meta(Key, Default) ->
    case ets:info(?T_META) of
        undefined ->
            Default;
        _ ->
            case ets:lookup(?T_META, Key) of
                [{_, V}] -> V;
                [] -> Default
            end
    end.

%%====================================================================
%% gen_server
%%====================================================================

init(Opts) ->
    process_flag(trap_exit, true),
    create_tables(),
    Dir = maps:get(data_dir, Opts, data_dir()),
    {ok, Status} = load(Dir),
    {ok, #{dir => Dir, status => Status}}.

handle_call(reload, _From, State = #{dir := Dir}) ->
    [ets:delete_all_objects(T) || T <- ?TABLES],
    {ok, Status} = load(Dir),
    {reply, {ok, Status}, State#{status := Status}};
handle_call(status, _From, State = #{status := Status}) ->
    {reply, Status, State};
handle_call(_Req, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast(_Msg, State) -> {noreply, State}.
handle_info(_Info, State) -> {noreply, State}.
terminate(_Reason, _State) -> ok.

create_tables() ->
    [ensure_table(T, case lists:member(T, ?BAGS) of true -> bag; false -> set end)
     || T <- ?TABLES],
    ok.

ensure_table(Name, Type) ->
    case ets:info(Name) of
        undefined ->
            ets:new(Name, [named_table, public, Type, {read_concurrency, true}]);
        _ ->
            Name
    end.

%%====================================================================
%% Loading
%%====================================================================

%% @doc Parse every CSV under `Dir' and populate the tables.
-spec load(file:filename()) -> {ok, map()}.
load(Dir) ->
    T0 = erlang:monotonic_time(millisecond),
    Files = [{File, Src, Prio} || {File, Src, Prio} <- ?SOURCES],
    Parsed = pmap(fun({File, Src, Prio}) ->
                          {Src, Prio, read_matches(Dir, File, Src)}
                  end, Files),
    RawMatches = lists:append([Rows || {_, _, Rows} <- Parsed]),
    FileStats = [#{file => list_to_binary(F), source => S, rows => length(R)}
                 || {{F, S, _}, {_, _, R}} <- lists:zip(Files, Parsed)],
    {Registry, Cache} = build_team_registry(RawMatches),
    Merged = merge_matches(RawMatches, Registry, Cache),
    ok = insert_matches(Merged),
    ok = recount_teams(),
    PlayerCount = load_players(Dir, Registry),
    Status = build_status(Dir, FileStats, PlayerCount,
                          erlang:monotonic_time(millisecond) - T0),
    ets:insert(?T_META, {status, Status}),
    {ok, Status}.

pmap(Fun, List) ->
    Parent = self(),
    Refs = [begin
                Ref = make_ref(),
                spawn_link(fun() -> Parent ! {Ref, Fun(Item)} end),
                Ref
            end || Item <- List],
    [receive {Ref, Result} -> Result after 120000 -> error(load_timeout) end
     || Ref <- Refs].

%%--------------------------------------------------------------------
%% Reading one CSV into raw match maps
%%--------------------------------------------------------------------

read_matches(Dir, File, Source) ->
    Path = filename:join(Dir, File),
    case bsmcp_csv:parse_file(Path) of
        {ok, Table} ->
            [R || Row <- bsmcp_csv:rows(Table),
                  R <- [row_to_match(Source, Row, Table)],
                  R =/= skip];
        {error, _} ->
            []
    end.

row_to_match(brasileirao, Row, T) ->
    Home = f(Row, T, <<"home_team">>),
    Away = f(Row, T, <<"away_team">>),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            DateTime = f(Row, T, <<"datetime">>),
            base_match(brasileirao, 1, serie_a,
                       #{season => bsmcp_text:to_int(f(Row, T, <<"season">>)),
                         date => bsmcp_text:parse_date(DateTime),
                         time => bsmcp_text:parse_time(DateTime),
                         round => nonempty(f(Row, T, <<"round">>)),
                         home_raw => Home,
                         away_raw => Away,
                         home_goal => bsmcp_text:to_int(f(Row, T, <<"home_goal">>)),
                         away_goal => bsmcp_text:to_int(f(Row, T, <<"away_goal">>))})
    end;
row_to_match(brazilian_cup, Row, T) ->
    Home = f(Row, T, <<"home_team">>),
    Away = f(Row, T, <<"away_team">>),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            DateTime = f(Row, T, <<"datetime">>),
            Date = bsmcp_text:parse_date(DateTime),
            base_match(brazilian_cup, 1, copa_do_brasil,
                       #{season => season_or_year(f(Row, T, <<"season">>), Date),
                         date => Date,
                         time => bsmcp_text:parse_time(DateTime),
                         round => nonempty(f(Row, T, <<"round">>)),
                         home_raw => Home,
                         away_raw => Away,
                         home_goal => bsmcp_text:to_int(f(Row, T, <<"home_goal">>)),
                         away_goal => bsmcp_text:to_int(f(Row, T, <<"away_goal">>))})
    end;
row_to_match(libertadores, Row, T) ->
    Home = f(Row, T, <<"home_team">>),
    Away = f(Row, T, <<"away_team">>),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            DateTime = f(Row, T, <<"datetime">>),
            Date = bsmcp_text:parse_date(DateTime),
            base_match(libertadores, 1, libertadores,
                       #{season => season_or_year(f(Row, T, <<"season">>), Date),
                         date => Date,
                         time => bsmcp_text:parse_time(DateTime),
                         stage => nonempty(f(Row, T, <<"stage">>)),
                         home_raw => Home,
                         away_raw => Away,
                         home_goal => bsmcp_text:to_int(f(Row, T, <<"home_goal">>)),
                         away_goal => bsmcp_text:to_int(f(Row, T, <<"away_goal">>))})
    end;
row_to_match(novo_campeonato, Row, T) ->
    Home = f(Row, T, <<"Equipe_mandante">>),
    Away = f(Row, T, <<"Equipe_visitante">>),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            Date = bsmcp_text:parse_date(f(Row, T, <<"Data">>)),
            base_match(novo_campeonato, 2, serie_a,
                       #{season => season_or_year(f(Row, T, <<"Ano">>), Date),
                         date => Date,
                         round => nonempty(f(Row, T, <<"Rodada">>)),
                         venue => nonempty(f(Row, T, <<"Arena">>)),
                         home_raw => Home,
                         away_raw => Away,
                         home_goal => bsmcp_text:to_int(f(Row, T, <<"Gols_mandante">>)),
                         away_goal => bsmcp_text:to_int(f(Row, T, <<"Gols_visitante">>))})
    end;
row_to_match(br_football, Row, T) ->
    Home = f(Row, T, <<"home">>),
    Away = f(Row, T, <<"away">>),
    Tournament = f(Row, T, <<"tournament">>),
    case {Home, Away, tournament_key(Tournament)} of
        {<<>>, _, _} -> skip;
        {_, <<>>, _} -> skip;
        {_, _, undefined} -> skip;
        {_, _, CompKey} ->
            Date = bsmcp_text:parse_date(f(Row, T, <<"date">>)),
            base_match(br_football, 3, CompKey,
                       #{season => br_football_season(CompKey, Date),
                         date => Date,
                         time => bsmcp_text:parse_time(f(Row, T, <<"time">>)),
                         home_raw => Home,
                         away_raw => Away,
                         home_goal => bsmcp_text:to_int(f(Row, T, <<"home_goal">>)),
                         away_goal => bsmcp_text:to_int(f(Row, T, <<"away_goal">>)),
                         stats => match_stats(Row, T)})
    end.

base_match(Source, Prio, CompKey, Fields) ->
    Defaults = #{source => Source, priority => Prio, competition => CompKey,
                 season => undefined, date => undefined, time => undefined,
                 round => undefined, stage => undefined, venue => undefined,
                 stats => #{}},
    maps:merge(Defaults, Fields).

match_stats(Row, T) ->
    Pairs = [{home_corners, <<"home_corner">>}, {away_corners, <<"away_corner">>},
             {home_shots, <<"home_shots">>}, {away_shots, <<"away_shots">>},
             {home_attacks, <<"home_attack">>}, {away_attacks, <<"away_attack">>},
             {total_corners, <<"total_corners">>}],
    maps:from_list([{K, V} || {K, Col} <- Pairs,
                              V <- [bsmcp_text:to_int(f(Row, T, Col))],
                              V =/= undefined]).

tournament_key(Name) ->
    case bsmcp_text:normalize(Name) of
        <<"serie a">> -> serie_a;
        <<"serie b">> -> serie_b;
        <<"serie c">> -> serie_c;
        <<"copa brasil">> -> copa_do_brasil;   % "Copa do Brasil", "do" is a stop word
        <<"copa do brasil">> -> copa_do_brasil;
        _ -> undefined
    end.

%% The extended stats file has no season column.  League seasons that
%% spill into the next calendar year (the 2020 Brasileirão finished in
%% February 2021) are pulled back to the season they belong to.
br_football_season(_CompKey, undefined) -> undefined;
br_football_season(CompKey, {Y, M, _}) ->
    IsLeague = lists:member(CompKey, [serie_a, serie_b, serie_c]),
    case IsLeague andalso M =< 2 of
        true -> Y - 1;
        false -> Y
    end.

season_or_year(Raw, Date) ->
    case bsmcp_text:to_int(Raw) of
        undefined -> bsmcp_text:date_year(Date);
        Season -> Season
    end.

f(Row, Table, Name) -> bsmcp_csv:field(Row, Table, Name).

nonempty(<<>>) -> undefined;
nonempty(Bin) ->
    case string:trim(Bin) of
        <<>> -> undefined;
        <<"NA">> -> undefined;
        Trimmed -> binary:copy(Trimmed)
    end.

%%--------------------------------------------------------------------
%% Team registry
%%--------------------------------------------------------------------

%% Occurrence counting pass: {Key, State} -> #{count, variants, display}.
%% `Cache' memoises the (comparatively expensive) name resolution so the
%% second pass over ~48k team mentions is a plain map lookup.
build_team_registry(RawMatches) ->
    {Occurrences, Cache} =
        lists:foldl(fun(#{home_raw := H, away_raw := A}, Acc) ->
                            add_occurrence(A, add_occurrence(H, Acc))
                    end, {#{}, #{}}, RawMatches),
    %% Group by key to detect names that denote several clubs.
    ByKey = maps:fold(fun({Key, State}, Info, Acc) ->
                              maps:update_with(Key, fun(L) -> [{State, Info} | L] end,
                                               [{State, Info}], Acc)
                      end, #{}, Occurrences),
    {maps:fold(fun assign_ids/3, #{}, ByKey), Cache}.

add_occurrence(Raw, {Acc, Cache0}) ->
    {Resolved, Cache} = cached_resolve(Raw, Cache0),
    {Key, State, Core} = Resolved,
    Entry = maps:get({Key, State}, Acc,
                     #{count => 0, variants => #{}, display => Core}),
    #{count := N, variants := Vs} = Entry,
    Display = better_display(maps:get(display, Entry), Core),
    {Acc#{{Key, State} =>
              Entry#{count := N + 1,
                     variants := Vs#{binary:copy(Raw) => true},
                     display := Display}},
     Cache}.

cached_resolve(Raw, Cache) ->
    case maps:find(Raw, Cache) of
        {ok, Resolved} ->
            {Resolved, Cache};
        error ->
            {Key, State, Core} = bsmcp_names:resolve(Raw),
            Resolved = {Key, State, binary:copy(Core)},
            {Resolved, Cache#{binary:copy(Raw) => Resolved}}
    end.

%% Prefer the spelling that kept its accents, then the shorter one.
better_display(<<>>, B) -> B;
better_display(A, <<>>) -> A;
better_display(A, B) ->
    case {accent_score(A), byte_size(A), accent_score(B), byte_size(B)} of
        {SA, _, SB, _} when SA > SB -> A;
        {SA, _, SB, _} when SB > SA -> B;
        {_, LA, _, LB} when LA =< LB -> A;
        _ -> B
    end.

accent_score(Bin) -> byte_size(Bin) - byte_size(bsmcp_text:fold_accents(Bin)).

assign_ids(Key, StateEntries, Registry) ->
    States = [S || {S, _} <- StateEntries, S =/= undefined],
    Distinct = lists:usort(States),
    case Distinct of
        [] ->
            %% never seen with a state marker
            [{undefined, Info}] = StateEntries,
            add_team(Registry, Key, Key, undefined, Info, false);
        [Single] ->
            %% one club: fold the state-less spellings into it
            Info = merge_infos([I || {_, I} <- StateEntries]),
            add_team(Registry, Key, Key, Single, Info, false);
        _ ->
            %% ambiguous key (Botafogo RJ / SP / PB): keep them apart and
            %% attach bare occurrences to the most frequent state
            Stated = [{S, I} || {S, I} <- StateEntries, S =/= undefined],
            {TopState, _} = hd(lists:sort(fun({_, #{count := A}}, {_, #{count := B}}) ->
                                                  A >= B
                                          end, Stated)),
            Bare = [I || {undefined, I} <- StateEntries],
            R1 = lists:foldl(
                   fun({S, I}, Acc) ->
                           Info = case S =:= TopState of
                                      true -> merge_infos([I | Bare]);
                                      false -> I
                                  end,
                           TeamId = <<Key/binary, "|", S/binary>>,
                           add_team(Acc, TeamId, Key, S, Info, true)
                   end, Registry, Stated),
            case Bare of
                [] -> R1;
                _ -> maps:put({Key, undefined}, <<Key/binary, "|", TopState/binary>>, R1)
            end
    end.

merge_infos(Infos) ->
    lists:foldl(fun(#{count := C, variants := V, display := D},
                    #{count := C0, variants := V0, display := D0}) ->
                        #{count => C + C0, variants => maps:merge(V, V0),
                          display => better_display(D0, D)}
                end, #{count => 0, variants => #{}, display => <<>>}, Infos).

add_team(Registry, TeamId, Key, State, Info, Ambiguous) ->
    #{count := Count, variants := Variants, display := Display0} = Info,
    Display = bsmcp_names:display_core(Display0),
    Name = case Ambiguous andalso State =/= undefined of
               true -> <<Display/binary, "-", State/binary>>;
               false -> Display
           end,
    Team = #{id => TeamId, key => Key, state => State, name => Name,
             short_name => Display, ambiguous => Ambiguous,
             variants => lists:sort(maps:keys(Variants)),
             match_count => Count},
    ets:insert(?T_TEAM, {TeamId, Team}),
    ets:insert(?T_TEAM_KEY, {Key, TeamId}),
    ets:insert(?T_TEAM_LOOKUP, {{Key, State}, TeamId}),
    maps:put({Key, State}, TeamId, Registry).

lookup_team_id(Registry, Cache, Raw) ->
    {Key, State, _} = case maps:find(Raw, Cache) of
                          {ok, R} -> R;
                          error -> bsmcp_names:resolve(Raw)
                      end,
    case maps:find({Key, State}, Registry) of
        {ok, Id} -> Id;
        error ->
            case maps:find({Key, undefined}, Registry) of
                {ok, Id} -> Id;
                error -> Key
            end
    end.

%%--------------------------------------------------------------------
%% De-duplication / merge
%%--------------------------------------------------------------------

merge_matches(RawMatches, Registry, Cache) ->
    Sorted = lists:sort(fun(#{priority := A}, #{priority := B}) -> A =< B end,
                        RawMatches),
    {Map, Order} =
        lists:foldl(
          fun(Raw, {Acc, Ord}) ->
                  HomeId = lookup_team_id(Registry, Cache, maps:get(home_raw, Raw)),
                  AwayId = lookup_team_id(Registry, Cache, maps:get(away_raw, Raw)),
                  M = Raw#{home_team => HomeId, away_team => AwayId,
                           sources => [maps:get(source, Raw)]},
                  Key = {maps:get(competition, Raw), maps:get(season, Raw),
                         HomeId, AwayId},
                  case maps:find(Key, Acc) of
                      {ok, Existing} ->
                          {Acc#{Key := merge_match(Existing, M)}, Ord};
                      error ->
                          {Acc#{Key => M}, [Key | Ord]}
                  end
          end, {#{}, []}, Sorted),
    [maps:get(K, Map) || K <- lists:reverse(Order)].

%% Keep the high-priority record and fill its gaps from the duplicate.
merge_match(Keep, Extra) ->
    Filled = lists:foldl(fun(Field, Acc) ->
                                 case maps:get(Field, Acc, undefined) of
                                     undefined ->
                                         maps:put(Field, maps:get(Field, Extra, undefined), Acc);
                                     _ ->
                                         Acc
                                 end
                         end, Keep,
                         [date, time, round, stage, venue, home_goal, away_goal]),
    Stats = maps:merge(maps:get(stats, Extra, #{}), maps:get(stats, Keep, #{})),
    Sources = lists:usort(maps:get(sources, Keep, []) ++ maps:get(sources, Extra, [])),
    Filled#{stats => Stats, sources => Sources}.

%%--------------------------------------------------------------------
%% Insertion + indexes
%%--------------------------------------------------------------------

insert_matches(Matches) ->
    lists:foldl(fun(M0, Id) ->
                        M = finalise_match(M0, Id),
                        ets:insert(?T_MATCH, {Id, M}),
                        #{home_team := H, away_team := A,
                          competition := C, season := S} = M,
                        ets:insert(?T_TEAM_MATCH, {H, Id}),
                        ets:insert(?T_TEAM_MATCH, {A, Id}),
                        ets:insert(?T_COMP_MATCH, {{C, S}, Id}),
                        Id + 1
                end, 1, Matches),
    ok.

%% `match_count' from the occurrence pass counts raw CSV rows; after
%% de-duplication it must reflect distinct fixtures.
recount_teams() ->
    lists:foreach(
      fun({TeamId, Team}) ->
              N = length(ets:lookup(?T_TEAM_MATCH, TeamId)),
              ets:insert(?T_TEAM, {TeamId, Team#{match_count => N}})
      end, ets:tab2list(?T_TEAM)),
    ok.

finalise_match(M, Id) ->
    #{home_goal := HG, away_goal := AG, home_team := H, away_team := A} = M,
    Result = result_of(HG, AG),
    HomeName = team_name(H),
    AwayName = team_name(A),
    maps:without([priority, home_raw, away_raw],
                 M#{id => Id,
                    result => Result,
                    home_name => HomeName,
                    away_name => AwayName,
                    played => HG =/= undefined andalso AG =/= undefined,
                    home_raw_name => maps:get(home_raw, M),
                    away_raw_name => maps:get(away_raw, M)}).

result_of(undefined, _) -> undefined;
result_of(_, undefined) -> undefined;
result_of(HG, AG) when HG > AG -> home;
result_of(HG, AG) when AG > HG -> away;
result_of(_, _) -> draw.

team_name(TeamId) ->
    case team(TeamId) of
        #{name := Name} -> Name;
        undefined -> TeamId
    end.

%%--------------------------------------------------------------------
%% Players
%%--------------------------------------------------------------------

load_players(Dir, Registry) ->
    Path = filename:join(Dir, ?PLAYER_FILE),
    case bsmcp_csv:parse_file(Path) of
        {ok, Table} ->
            {N, _Cache} =
                lists:foldl(fun(Row, Acc) -> insert_player(Row, Table, Registry, Acc) end,
                            {0, #{}}, bsmcp_csv:rows(Table)),
            N;
        {error, _} ->
            0
    end.

insert_player(Row, T, Registry, {N, Cache0}) ->
    Name = nonempty(f(Row, T, <<"Name">>)),
    case Name of
        undefined ->
            {N, Cache0};
        _ ->
            Id = case bsmcp_text:to_int(f(Row, T, <<"ID">>)) of
                     undefined -> -N;
                     I -> I
                 end,
            Club = nonempty(f(Row, T, <<"Club">>)),
            Nationality = nonempty(f(Row, T, <<"Nationality">>)),
            NameKey = bsmcp_text:normalize(Name),
            NatKey = bsmcp_text:normalize(Nationality),
            %% club names repeat across ~18k rows: memoise the resolution
            {ClubKey, TeamId, Cache} =
                case Club of
                    undefined ->
                        {undefined, undefined, Cache0};
                    _ ->
                        case maps:find(Club, Cache0) of
                            {ok, {CK, TI}} ->
                                {CK, TI, Cache0};
                            error ->
                                {Key, State, _} = bsmcp_names:resolve(Club),
                                TI = club_team_id(Registry, Key, State),
                                {Key, TI, Cache0#{Club => {Key, TI}}}
                        end
                end,
            Player = #{id => Id,
                       name => Name,
                       name_key => NameKey,
                       age => bsmcp_text:to_int(f(Row, T, <<"Age">>)),
                       nationality => Nationality,
                       nationality_key => NatKey,
                       overall => bsmcp_text:to_int(f(Row, T, <<"Overall">>)),
                       potential => bsmcp_text:to_int(f(Row, T, <<"Potential">>)),
                       club => Club,
                       club_key => ClubKey,
                       team_id => TeamId,
                       position => nonempty(f(Row, T, <<"Position">>)),
                       jersey_number => bsmcp_text:to_int(f(Row, T, <<"Jersey Number">>)),
                       height => nonempty(f(Row, T, <<"Height">>)),
                       weight => nonempty(f(Row, T, <<"Weight">>)),
                       value => nonempty(f(Row, T, <<"Value">>)),
                       wage => nonempty(f(Row, T, <<"Wage">>)),
                       preferred_foot => nonempty(f(Row, T, <<"Preferred Foot">>)),
                       work_rate => nonempty(f(Row, T, <<"Work Rate">>)),
                       joined => nonempty(f(Row, T, <<"Joined">>)),
                       contract_until => nonempty(f(Row, T, <<"Contract Valid Until">>)),
                       skills => skills(Row, T)},
            ets:insert(?T_PLAYER, {Id, Player}),
            [ets:insert(?T_PLAYER_TOKEN, {Tok, Id})
             || Tok <- binary:split(NameKey, <<" ">>, [global, trim_all])],
            case ClubKey of
                undefined -> ok;
                _ -> ets:insert(?T_CLUB_PLAYER, {ClubKey, Id})
            end,
            case TeamId of
                undefined -> ok;
                ClubKey -> ok;
                _ -> ets:insert(?T_CLUB_PLAYER, {TeamId, Id})
            end,
            case Nationality of
                undefined -> ok;
                _ -> ets:insert(?T_NAT_PLAYER, {NatKey, Id})
            end,
            {N + 1, Cache}
    end.

%% A FIFA club name that resolves to a team seen in the match data
%% becomes a cross-dataset edge (player -> team -> matches).
club_team_id(Registry, Key, State) ->
    case maps:find({Key, State}, Registry) of
        {ok, Id} -> Id;
        error ->
            case maps:find({Key, undefined}, Registry) of
                {ok, Id} -> Id;
                error -> undefined
            end
    end.

skills(Row, T) ->
    Cols = [<<"Crossing">>, <<"Finishing">>, <<"HeadingAccuracy">>,
            <<"ShortPassing">>, <<"Volleys">>, <<"Dribbling">>, <<"Curve">>,
            <<"FKAccuracy">>, <<"LongPassing">>, <<"BallControl">>,
            <<"Acceleration">>, <<"SprintSpeed">>, <<"Agility">>,
            <<"Reactions">>, <<"Balance">>, <<"ShotPower">>, <<"Jumping">>,
            <<"Stamina">>, <<"Strength">>, <<"LongShots">>, <<"Aggression">>,
            <<"Interceptions">>, <<"Positioning">>, <<"Vision">>,
            <<"Penalties">>, <<"Composure">>, <<"Marking">>,
            <<"StandingTackle">>, <<"SlidingTackle">>, <<"GKDiving">>,
            <<"GKHandling">>, <<"GKKicking">>, <<"GKPositioning">>,
            <<"GKReflexes">>],
    maps:from_list([{C, V} || C <- Cols,
                              V <- [bsmcp_text:to_int(f(Row, T, C))],
                              V =/= undefined]).

%%--------------------------------------------------------------------
%% Status / metadata
%%--------------------------------------------------------------------

build_status(Dir, FileStats, PlayerCount, Millis) ->
    {Comps, Seasons} =
        fold_matches(fun(#{competition := C, season := S}, {Cs, Ss}) ->
                             {maps:update_with(C, fun(N) -> N + 1 end, 1, Cs),
                              case S of
                                  undefined -> Ss;
                                  _ -> maps:update_with(C, fun(L) -> [S | L] end, [S], Ss)
                              end}
                     end, {#{}, #{}}),
    SeasonMap = maps:map(fun(_, L) -> lists:usort(L) end, Seasons),
    ets:insert(?T_META, {seasons, SeasonMap}),
    ets:insert(?T_META, {competitions, lists:sort(maps:keys(Comps))}),
    CompStats = [#{key => C,
                   name => competition_name(C),
                   matches => N,
                   seasons => maps:get(C, SeasonMap, [])}
                 || {C, N} <- lists:sort(maps:to_list(Comps))],
    #{data_dir => bsmcp_text:bin(Dir),
      files => FileStats,
      source_rows => lists:sum([R || #{rows := R} <- FileStats]),
      matches => ets:info(?T_MATCH, size),
      teams => ets:info(?T_TEAM, size),
      players => PlayerCount,
      competitions => CompStats,
      load_time_ms => Millis}.

%%--------------------------------------------------------------------
%% Data directory discovery
%%--------------------------------------------------------------------

discover_data_dir() ->
    Roots = ancestors(cwd(), 6) ++ ancestors(lib_root(), 8),
    Candidates = [filename:join([R, "data", "kaggle"]) || R <- Roots],
    case [C || C <- Candidates, filelib:is_dir(C)] of
        [Dir | _] -> Dir;
        [] -> filename:join(["data", "kaggle"])
    end.

cwd() ->
    {ok, Cwd} = file:get_cwd(),
    Cwd.

lib_root() ->
    case code:lib_dir(bsmcp) of
        {error, _} -> cwd();
        Dir -> Dir
    end.

ancestors(Dir, 0) -> [Dir];
ancestors(Dir, N) ->
    Parent = filename:dirname(Dir),
    case Parent of
        Dir -> [Dir];
        _ -> [Dir | ancestors(Parent, N - 1)]
    end.
