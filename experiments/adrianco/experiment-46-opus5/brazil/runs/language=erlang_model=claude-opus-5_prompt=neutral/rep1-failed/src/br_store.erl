%%%-------------------------------------------------------------------
%%% @doc In-memory store: ETS tables plus the knowledge graph.
%%%
%%% A single gen_server owns the tables (so they survive as long as the
%%% application does) but all reads go straight to ETS from the calling
%%% process, which keeps lookups in the microsecond range and lets the
%%% MCP server answer several queries concurrently.
%%%
%%% Fixtures that appear in more than one data set are merged rather
%%% than duplicated: `#match.id' is derived from competition, season and
%%% the two canonical team ids, so the 2019 Brasileirão appears once
%%% even though it is present in three of the five match files.  The
%%% first source to provide a field wins, and later sources only fill in
%%% gaps (kick-off time, stadium, shot/corner statistics).
%%% @end
%%%-------------------------------------------------------------------
-module(br_store).

-behaviour(gen_server).

-include("br_soccer.hrl").

%% API
-export([start_link/0, start_link/1,
         ensure_loaded/0, ensure_loaded/1,
         load/1,
         stop/0,
         loaded/0,
         stats/0,
         data_dir/0,
         match/1,
         all_matches/0,
         fold_matches/2,
         team_matches/1,
         team_match_ids/1,
         team/1,
         all_teams/0,
         resolve_team/1,
         search_teams/1,
         player/1,
         all_players/0,
         fold_players/2,
         players_of_club/1,
         competitions/0,
         seasons/0,
         seasons_of/1]).

%% gen_server callbacks
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(SERVER, ?MODULE).
-define(MATCHES, br_matches).
-define(TEAM_IDX, br_team_matches).
-define(TEAMS, br_teams).
-define(PLAYERS, br_players).
-define(CLUB_IDX, br_club_players).
-define(META, br_meta).

%%====================================================================
%% API
%%====================================================================

start_link() -> start_link(#{}).

start_link(Opts) when is_map(Opts) ->
    gen_server:start_link({local, ?SERVER}, ?MODULE, Opts, []).

%% @doc Start the store and load the data sets if that has not happened yet.
-spec ensure_loaded() -> ok | {error, term()}.
ensure_loaded() -> ensure_loaded(#{}).

%% The store is started under the application supervisor rather than
%% linked to the caller, so that it survives a test case or a shell
%% process going away.
-spec ensure_loaded(map()) -> ok | {error, term()}.
ensure_loaded(Opts) when map_size(Opts) =:= 0 ->
    case whereis(?SERVER) of
        undefined ->
            case application:ensure_all_started(br_soccer) of
                {ok, _} -> wait_loaded();
                {error, Reason} -> {error, Reason}
            end;
        _ -> wait_loaded()
    end;
ensure_loaded(Opts) ->
    case whereis(?SERVER) of
        undefined ->
            case start_link(Opts) of
                {ok, _Pid} -> wait_loaded();
                {error, {already_started, _}} -> wait_loaded();
                {error, Reason} -> {error, Reason}
            end;
        _ -> wait_loaded()
    end.

wait_loaded() ->
    case loaded() of
        true -> ok;
        false -> gen_server:call(?SERVER, load, infinity)
    end.

%% @doc Force a (re)load from `Dir'.
-spec load(file:filename()) -> ok | {error, term()}.
load(Dir) -> gen_server:call(?SERVER, {load, Dir}, infinity).

stop() ->
    case whereis(?SERVER) of
        undefined -> ok;
        _ -> gen_server:stop(?SERVER)
    end.

-spec loaded() -> boolean().
loaded() ->
    ets:info(?META) =/= undefined andalso meta(loaded, false) =:= true.

%% @doc Counters describing what is in memory.
-spec stats() -> map().
stats() ->
    #{matches => size_of(?MATCHES),
      teams => size_of(?TEAMS),
      players => size_of(?PLAYERS),
      graph_nodes => br_graph:node_count(),
      graph_edges => br_graph:edge_count(),
      sources => meta(sources, []),
      rows_read => meta(rows_read, 0),
      duplicates_merged => meta(duplicates, 0),
      invalid_rows => meta(invalid, 0),
      data_dir => list_to_binary(meta(data_dir, "")),
      load_time_ms => meta(load_time_ms, 0)}.

-spec data_dir() -> string().
data_dir() -> meta(data_dir, "").

%%--------------------------------------------------------------------
%% Matches
%%--------------------------------------------------------------------

-spec match(binary()) -> {ok, #match{}} | error.
match(Id) ->
    case ets:lookup(?MATCHES, Id) of
        [{Id, M}] -> {ok, M};
        [] -> error
    end.

-spec all_matches() -> [#match{}].
all_matches() -> [M || {_, M} <- ets:tab2list(?MATCHES)].

-spec fold_matches(fun((#match{}, Acc) -> Acc), Acc) -> Acc.
fold_matches(Fun, Acc0) ->
    ets:foldl(fun({_, M}, Acc) -> Fun(M, Acc) end, Acc0, ?MATCHES).

-spec team_match_ids(binary()) -> [binary()].
team_match_ids(TeamId) -> [Id || {_, Id} <- ets:lookup(?TEAM_IDX, TeamId)].

-spec team_matches(binary()) -> [#match{}].
team_matches(TeamId) ->
    lists:filtermap(fun(Id) ->
                            case match(Id) of
                                {ok, M} -> {true, M};
                                error -> false
                            end
                    end, team_match_ids(TeamId)).

%%--------------------------------------------------------------------
%% Teams
%%--------------------------------------------------------------------

-spec team(binary()) -> {ok, #team{}} | error.
team(Id) ->
    case ets:lookup(?TEAMS, Id) of
        [{Id, T}] -> {ok, T};
        [] -> error
    end.

-spec all_teams() -> [#team{}].
all_teams() -> [T || {_, T} <- ets:tab2list(?TEAMS)].

%%--------------------------------------------------------------------
%% @doc Turn user input ("flamengo", "Sao Paulo-SP", "gremio") into a
%% team id.
%%
%% Tries the canonical id first, then an exact match on any spelling
%% seen in the data, then a substring match.  When several teams match,
%% the one with the most matches in the data wins - "santos" means the
%% Serie A club, not "Santos - AP" from a single cup tie.
-spec resolve_team(term()) -> {ok, binary()} | {error, {unknown_team, binary(), [binary()]}}.
resolve_team(Query) ->
    Bin = string:trim(br_text:to_binary(Query)),
    Id = br_names:canonical_id(Bin),
    case ets:member(?TEAMS, Id) orelse ets:member(?CLUB_IDX, Id) of
        true -> {ok, Id};
        false ->
            Norm = br_text:normalize(Bin),
            case exact_alias(Norm) of
                [Best | _] -> {ok, Best};
                [] ->
                    case search_teams(Bin) of
                        [#team{id = Best} | _] -> {ok, Best};
                        [] -> {error, {unknown_team, Bin, []}}
                    end
            end
    end.

%% @doc Teams whose name or any observed spelling contains the query,
%% most played first.
-spec search_teams(term()) -> [#team{}].
search_teams(Query) ->
    Norm = br_text:normalize(Query),
    Matches = [T || T <- all_teams(), team_matches_query(T, Norm)],
    lists:sort(fun(#team{match_count = A}, #team{match_count = B}) -> A >= B end, Matches).

team_matches_query(_T, <<>>) -> false;
team_matches_query(#team{id = Id, name = Name, aliases = Aliases}, Norm) ->
    lists:any(fun(Candidate) ->
                      binary:match(br_text:normalize(Candidate), Norm) =/= nomatch
              end, [Id, Name | Aliases]).

exact_alias(Norm) ->
    Ids = [Id || #team{id = Id, name = Name, aliases = Aliases} <- all_teams(),
                 lists:any(fun(C) -> br_text:normalize(C) =:= Norm end, [Name | Aliases])],
    lists:sort(fun(A, B) -> count_of(A) >= count_of(B) end, Ids).

count_of(Id) ->
    case team(Id) of
        {ok, #team{match_count = C}} -> C;
        error -> 0
    end.

%%--------------------------------------------------------------------
%% Players
%%--------------------------------------------------------------------

-spec player(integer()) -> {ok, #player{}} | error.
player(Id) ->
    case ets:lookup(?PLAYERS, Id) of
        [{Id, P}] -> {ok, P};
        [] -> error
    end.

-spec all_players() -> [#player{}].
all_players() -> [P || {_, P} <- ets:tab2list(?PLAYERS)].

-spec fold_players(fun((#player{}, Acc) -> Acc), Acc) -> Acc.
fold_players(Fun, Acc0) ->
    ets:foldl(fun({_, P}, Acc) -> Fun(P, Acc) end, Acc0, ?PLAYERS).

-spec players_of_club(binary()) -> [#player{}].
players_of_club(ClubId) ->
    lists:filtermap(fun({_, PlayerId}) ->
                            case player(PlayerId) of
                                {ok, P} -> {true, P};
                                error -> false
                            end
                    end, ets:lookup(?CLUB_IDX, ClubId)).

%%--------------------------------------------------------------------
%% Competitions / seasons
%%--------------------------------------------------------------------

-spec competitions() -> [binary()].
competitions() -> meta(competitions, []).

-spec seasons() -> [integer()].
seasons() -> meta(seasons, []).

-spec seasons_of(binary()) -> [integer()].
seasons_of(Competition) ->
    proplists:get_value(Competition, meta(comp_seasons, []), []).

%%====================================================================
%% gen_server
%%====================================================================

init(Opts) ->
    process_flag(trap_exit, true),
    create_tables(),
    case maps:get(load, Opts, true) of
        true ->
            Dir = maps:get(data_dir, Opts, br_loader:data_dir()),
            case do_load(Dir) of
                ok -> {ok, #{opts => Opts}};
                {error, Reason} -> {stop, Reason}
            end;
        false ->
            {ok, #{opts => Opts}}
    end.

handle_call(load, _From, State) ->
    Dir = maps:get(data_dir, maps:get(opts, State, #{}), br_loader:data_dir()),
    {reply, do_load(Dir), State};
handle_call({load, Dir}, _From, State) ->
    {reply, do_load(Dir), State};
handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast(_Msg, State) -> {noreply, State}.

handle_info(_Info, State) -> {noreply, State}.

terminate(_Reason, _State) ->
    ok.

%%====================================================================
%% Loading
%%====================================================================

create_tables() ->
    Opts = [named_table, public, {read_concurrency, true}],
    new_table(?MATCHES, [set | Opts]),
    new_table(?TEAMS, [set | Opts]),
    new_table(?PLAYERS, [set | Opts]),
    new_table(?TEAM_IDX, [bag | Opts]),
    new_table(?CLUB_IDX, [bag | Opts]),
    new_table(?META, [set | Opts]),
    br_graph:new(),
    ok.

new_table(Name, Opts) ->
    case ets:info(Name) of
        undefined -> ets:new(Name, Opts);
        _ -> ets:delete_all_objects(Name), Name
    end.

do_load(undefined) ->
    {error, {data_dir_not_found,
             "set BR_SOCCER_DATA_DIR or run from the repository root"}};
do_load(Dir) ->
    Start = erlang:monotonic_time(millisecond),
    create_tables(),
    ets:insert(?META, {data_dir, Dir}),
    try
        Rows = lists:sum([load_source(S, Dir) || S <- br_loader:sources()]),
        index_matches(),
        PlayerRows = load_players(Dir),
        ets:insert(?META, {rows_read, Rows + PlayerRows}),
        ets:insert(?META, {sources, br_loader:sources() ++ [fifa_players]}),
        ets:insert(?META, {load_time_ms, erlang:monotonic_time(millisecond) - Start}),
        ets:insert(?META, {loaded, true}),
        ok
    catch
        Class:Reason:Stack ->
            logger:error("data load failed: ~p:~p~n~p", [Class, Reason, Stack]),
            {error, {load_failed, Reason}}
    end.

load_source(Source, Dir) ->
    Matches = br_loader:load_matches(Source, Dir),
    lists:foreach(fun insert_match/1, Matches),
    length(Matches).

%% Insert or merge into an already known fixture.
%%
%% A handful of rows in Brazilian_Cup_Matches.csv name the same club as
%% home and away (the 2019 Bragantino-PA rows, where the opponent's
%% state was lost in the export).  Such a fixture cannot exist, so it is
%% counted and dropped rather than creating a team that played itself.
insert_match(#match{home = Same, away = Same}) ->
    ets:update_counter(?META, invalid, {2, 1}, {invalid, 0}),
    ok;
insert_match(#match{id = Id} = M) ->
    case ets:lookup(?MATCHES, Id) of
        [] -> ets:insert(?MATCHES, {Id, M});
        [{Id, Existing}] ->
            ets:update_counter(?META, duplicates, {2, 1}, {duplicates, 0}),
            ets:insert(?MATCHES, {Id, merge_match(Existing, M)})
    end.

merge_match(#match{} = A, #match{} = B) ->
    A#match{sources = lists:usort(A#match.sources ++ B#match.sources),
            date = first(A#match.date, B#match.date),
            time = first(A#match.time, B#match.time),
            round = first(A#match.round, B#match.round),
            stage = first(A#match.stage, B#match.stage),
            home_goals = first(A#match.home_goals, B#match.home_goals),
            away_goals = first(A#match.away_goals, B#match.away_goals),
            venue = first(A#match.venue, B#match.venue),
            stats = maps:merge(B#match.stats, A#match.stats)}.

first(undefined, V) -> V;
first(V, _) -> V.

%%--------------------------------------------------------------------
%% Second pass: team records, per-team index and graph edges.
index_matches() ->
    Acc0 = #{teams => #{}, names => #{}, comps => #{}, seasons => #{}},
    Acc = fold_matches(fun index_match/2, Acc0),
    #{teams := Teams, names := Names, comps := Comps, seasons := Seasons} = Acc,
    maps:foreach(
      fun(Id, #{count := Count, comps := TComps, seasons := TSeasons,
                state := State, country := Country}) ->
              Name = best_name(Id, Names),
              Aliases = lists:usort(maps:keys(maps:get(Id, Names, #{}))),
              Team = #team{id = Id, name = Name, state = State, country = Country,
                           aliases = Aliases, match_count = Count,
                           competitions = lists:usort(TComps),
                           seasons = lists:usort(TSeasons)},
              ets:insert(?TEAMS, {Id, Team}),
              add_team_node(Team)
      end, Teams),
    CompSeasons = [{C, lists:usort(S)} || {C, S} <- maps:to_list(Comps)],
    ets:insert(?META, {competitions, lists:sort(maps:keys(Comps))}),
    ets:insert(?META, {comp_seasons, CompSeasons}),
    ets:insert(?META, {seasons, lists:usort(maps:keys(Seasons))}),
    lists:foreach(fun({C, _}) ->
                          br_graph:add_node(competition, C, br_names:competition_display(C))
                  end, CompSeasons),
    lists:foreach(fun(S) ->
                          br_graph:add_node(season, S, integer_to_binary(S))
                  end, lists:usort(maps:keys(Seasons))),
    %% Second pass: match nodes, now that every team has a display name.
    fold_matches(fun(M, _) -> add_match_node(M, M#match.venue) end, ok),
    ok.

index_match(#match{} = M, Acc) ->
    #match{id = Id, home = Home, away = Away, home_name = HN, away_name = AN,
           competition = Comp, season = Season} = M,
    ets:insert(?TEAM_IDX, {Home, Id}),
    ets:insert(?TEAM_IDX, {Away, Id}),
    Acc1 = note_team(Home, HN, Comp, Season, Acc),
    Acc2 = note_team(Away, AN, Comp, Season, Acc1),
    note_competition(Comp, Season, Acc2).

note_team(Id, Name, Comp, Season, #{teams := Teams, names := Names} = Acc) ->
    Entry = maps:get(Id, Teams, undefined),
    {St, Co} = case Entry of
                   undefined ->
                       {_, _, S, C} = br_names:canonical(Name),
                       {S, C};
                   #{state := S, country := C} -> {S, C}
               end,
    Updated = case Entry of
                  undefined ->
                      #{count => 1, comps => [Comp], seasons => season_list(Season),
                        state => St, country => Co};
                  #{count := N, comps := Cs, seasons := Ss} = E ->
                      E#{count => N + 1,
                         comps => [Comp | Cs],
                         seasons => season_list(Season) ++ Ss}
              end,
    NameCounts = maps:get(Id, Names, #{}),
    Acc#{teams => Teams#{Id => Updated},
         names => Names#{Id => NameCounts#{Name => maps:get(Name, NameCounts, 0) + 1}}}.

season_list(undefined) -> [];
season_list(S) -> [S].

note_competition(Comp, Season, #{comps := Comps, seasons := Seasons} = Acc) ->
    Acc#{comps => Comps#{Comp => season_list(Season) ++ maps:get(Comp, Comps, [])},
         seasons => case Season of
                        undefined -> Seasons;
                        _ -> Seasons#{Season => true}
                    end}.

%% Registry name if the club is curated, otherwise the spelling that
%% occurs most often (ties broken towards the accented, longer form).
best_name(Id, Names) ->
    case br_names:known(Id) of
        true -> br_names:display(Id);
        false ->
            Counts = maps:to_list(maps:get(Id, Names, #{})),
            case lists:sort(fun({NA, CA}, {NB, CB}) ->
                                    {CA, byte_size(NA)} >= {CB, byte_size(NB)}
                            end, Counts) of
                [{Name, _} | _] -> Name;
                [] -> br_names:display(Id)
            end
    end.

add_team_node(#team{id = Id, name = Name, state = State, country = Country,
                    match_count = Count, competitions = Comps}) ->
    NodeId = br_graph:add_node(team, Id, Name,
                               #{state => State, country => Country, matches => Count}),
    case State of
        undefined -> ok;
        _ ->
            StateNode = br_graph:add_node(state, br_text:normalize(State), State),
            br_graph:add_edge(NodeId, based_in, StateNode)
    end,
    case Country of
        undefined -> ok;
        _ ->
            CountryNode = br_graph:add_node(country, br_text:normalize(Country), Country),
            br_graph:add_edge(NodeId, from_country, CountryNode)
    end,
    lists:foreach(fun(C) ->
                          CompNode = br_graph:add_node(competition, C,
                                                       br_names:competition_display(C)),
                          br_graph:add_edge(NodeId, played_in, CompNode)
                  end, Comps),
    ok.

add_match_node(#match{} = M, Venue) ->
    #match{id = Id, home = Home, away = Away, competition = Comp, season = Season} = M,
    MatchNode = br_graph:add_node(match, Id, br_format:match_line(M),
                                  #{competition => Comp, season => Season}),
    br_graph:add_edge(MatchNode, home_team, br_graph:id(team, Home)),
    br_graph:add_edge(MatchNode, away_team, br_graph:id(team, Away)),
    br_graph:add_edge(MatchNode, in_competition, br_graph:id(competition, Comp)),
    case Season of
        undefined -> ok;
        _ -> br_graph:add_edge(MatchNode, in_season, br_graph:id(season, Season))
    end,
    case Venue of
        undefined -> ok;
        _ ->
            VenueNode = br_graph:add_node(venue, br_text:slug(Venue), Venue),
            br_graph:add_edge(MatchNode, at_venue, VenueNode)
    end,
    ok.

%%--------------------------------------------------------------------
load_players(Dir) ->
    Players = br_loader:load_players(Dir),
    lists:foreach(fun insert_player/1, Players),
    length(Players).

insert_player(#player{id = Id, club_id = ClubId, nationality = Nat, name = Name,
                      overall = Overall, position = Pos} = P) ->
    ets:insert(?PLAYERS, {Id, P}),
    NodeId = br_graph:add_node(player, Id, Name,
                               #{overall => Overall, position => Pos,
                                 nationality => Nat}),
    case ClubId of
        undefined -> ok;
        _ ->
            ets:insert(?CLUB_IDX, {ClubId, Id}),
            TeamNode = br_graph:id(team, ClubId),
            case br_graph:has_node(TeamNode) of
                true -> ok;
                false -> br_graph:add_node(team, ClubId, P#player.club, #{matches => 0})
            end,
            br_graph:add_edge(NodeId, plays_for, TeamNode)
    end,
    case Nat of
        undefined -> ok;
        _ ->
            CountryNode = br_graph:add_node(country, br_text:normalize(Nat), Nat),
            br_graph:add_edge(NodeId, nationality, CountryNode)
    end,
    ok.

%%====================================================================
%% Helpers
%%====================================================================

meta(Key, Default) ->
    case ets:info(?META) of
        undefined -> Default;
        _ ->
            case ets:lookup(?META, Key) of
                [{Key, V}] -> V;
                [] -> Default
            end
    end.

size_of(Table) ->
    case ets:info(Table, size) of
        undefined -> 0;
        N -> N
    end.
