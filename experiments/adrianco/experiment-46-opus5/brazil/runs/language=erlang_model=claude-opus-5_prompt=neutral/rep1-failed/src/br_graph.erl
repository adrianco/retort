%%%-------------------------------------------------------------------
%%% @doc A small labelled property graph on top of ETS.
%%%
%%% Nodes are identified by a `"type:key"' binary (`"team:flamengo"',
%%% `"player:158023"', `"competition:libertadores"', `"season:2019"',
%%% `"match:..."', `"country:brazil"', `"venue:maracana"', `"state:rj"')
%%% so that identifiers survive a round trip through JSON and can be
%%% handed straight to an LLM.
%%%
%%% Edges are directed and labelled, and are indexed in both directions
%%% so that traversal is O(degree) either way:
%%%
%%% ```
%%% match  -home_team->      team
%%% match  -away_team->      team
%%% match  -in_competition-> competition
%%% match  -in_season->      season
%%% match  -at_venue->       venue
%%% team   -played_in->      competition
%%% team   -based_in->       state
%%% player -plays_for->      team
%%% player -nationality->    country
%%% '''
%%% @end
%%%-------------------------------------------------------------------
-module(br_graph).

-export([new/0,
         delete/0,
         id/2,
         parse_id/1,
         add_node/3,
         add_node/4,
         add_edge/3,
         get_node/1,
         has_node/1,
         nodes_of_type/1,
         out/1, out/2,
         in/1, in/2,
         neighbours/1, neighbours/2,
         degree/1,
         path/3,
         node_count/0,
         edge_count/0]).

-define(NODES, br_graph_nodes).
-define(OUT, br_graph_out).
-define(IN, br_graph_in).

-type node_id() :: binary().
-type rel() :: atom().

%%--------------------------------------------------------------------
%% @doc (Re)create the graph tables.
-spec new() -> ok.
new() ->
    delete(),
    ?NODES = ets:new(?NODES, [named_table, public, set, {read_concurrency, true}]),
    ?OUT = ets:new(?OUT, [named_table, public, bag, {read_concurrency, true}]),
    ?IN = ets:new(?IN, [named_table, public, bag, {read_concurrency, true}]),
    ok.

-spec delete() -> ok.
delete() ->
    _ = [ets:delete(T) || T <- [?NODES, ?OUT, ?IN], ets:info(T) =/= undefined],
    ok.

%%--------------------------------------------------------------------
%% @doc Build a node id, e.g. `id(team, <<"santos">>)'.
-spec id(atom(), term()) -> node_id().
id(Type, Key) ->
    <<(atom_to_binary(Type, utf8))/binary, ":", (br_text:to_binary(Key))/binary>>.

%% @doc Split a node id back into `{Type, Key}'.
-spec parse_id(node_id()) -> {binary(), binary()}.
parse_id(Id) ->
    case binary:split(Id, <<":">>) of
        [Type, Key] -> {Type, Key};
        [Only] -> {<<>>, Only}
    end.

%%--------------------------------------------------------------------
-spec add_node(atom(), term(), binary()) -> node_id().
add_node(Type, Key, Label) -> add_node(Type, Key, Label, #{}).

%% @doc Insert (or update) a node and return its id.
-spec add_node(atom(), term(), binary(), map()) -> node_id().
add_node(Type, Key, Label, Props) ->
    Id = id(Type, Key),
    ets:insert(?NODES, {Id, Type, Label, Props}),
    Id.

%% @doc Insert a directed, labelled edge.
-spec add_edge(node_id(), rel(), node_id()) -> ok.
add_edge(From, Rel, To) ->
    ets:insert(?OUT, {From, Rel, To}),
    ets:insert(?IN, {To, Rel, From}),
    ok.

%%--------------------------------------------------------------------
-spec get_node(node_id()) -> {ok, map()} | error.
get_node(Id) ->
    case ets:lookup(?NODES, Id) of
        [{Id, Type, Label, Props}] ->
            {ok, #{id => Id, type => Type, label => Label, props => Props}};
        [] -> error
    end.

-spec has_node(node_id()) -> boolean().
has_node(Id) -> ets:member(?NODES, Id).

-spec nodes_of_type(atom()) -> [map()].
nodes_of_type(Type) ->
    [#{id => Id, type => T, label => L, props => P}
     || {Id, T, L, P} <- ets:match_object(?NODES, {'_', Type, '_', '_'})].

%%--------------------------------------------------------------------
%% @doc Outgoing edges as `{Rel, ToId}'.
-spec out(node_id()) -> [{rel(), node_id()}].
out(Id) -> [{R, To} || {_, R, To} <- ets:lookup(?OUT, Id)].

-spec out(node_id(), rel()) -> [node_id()].
out(Id, Rel) -> [To || {_, R, To} <- ets:lookup(?OUT, Id), R =:= Rel].

%% @doc Incoming edges as `{Rel, FromId}'.
-spec in(node_id()) -> [{rel(), node_id()}].
in(Id) -> [{R, From} || {_, R, From} <- ets:lookup(?IN, Id)].

-spec in(node_id(), rel()) -> [node_id()].
in(Id, Rel) -> [From || {_, R, From} <- ets:lookup(?IN, Id), R =:= Rel].

%% @doc All neighbours, ignoring edge direction.
-spec neighbours(node_id()) -> [{rel(), node_id(), out | in}].
neighbours(Id) ->
    [{R, To, out} || {R, To} <- out(Id)] ++ [{R, From, in} || {R, From} <- in(Id)].

-spec neighbours(node_id(), rel()) -> [node_id()].
neighbours(Id, Rel) -> out(Id, Rel) ++ in(Id, Rel).

-spec degree(node_id()) -> non_neg_integer().
degree(Id) -> length(ets:lookup(?OUT, Id)) + length(ets:lookup(?IN, Id)).

%%--------------------------------------------------------------------
%% @doc Breadth-first shortest path, ignoring edge direction.
%%
%% Returns the sequence of nodes from `From' to `To' together with the
%% relation used at each step, or `not_found' within `MaxDepth' hops.
-spec path(node_id(), node_id(), pos_integer()) ->
          {ok, [{rel() | start, node_id()}]} | not_found.
path(From, From, _MaxDepth) -> {ok, [{start, From}]};
path(From, To, MaxDepth) ->
    case has_node(From) andalso has_node(To) of
        false -> not_found;
        true -> bfs([[{start, From}]], #{From => true}, To, MaxDepth)
    end.

bfs([], _Seen, _To, _MaxDepth) -> not_found;
bfs(Queue, Seen, To, MaxDepth) ->
    case expand(Queue, Seen, To, MaxDepth, [], #{}) of
        {found, Path} -> {ok, lists:reverse(Path)};
        {continue, [], _} -> not_found;
        {continue, Next, NewSeen} -> bfs(Next, maps:merge(Seen, NewSeen), To, MaxDepth)
    end.

expand([], _Seen, _To, _MaxDepth, Acc, NewSeen) -> {continue, Acc, NewSeen};
expand([[{_, Node} | _] = Path | Rest], Seen, To, MaxDepth, Acc, NewSeen) ->
    case length(Path) > MaxDepth of
        true -> expand(Rest, Seen, To, MaxDepth, Acc, NewSeen);
        false ->
            Steps = [{R, N} || {R, N, _Dir} <- neighbours(Node)],
            case lists:keyfind(To, 2, Steps) of
                {Rel, To} -> {found, [{Rel, To} | Path]};
                false ->
                    {Acc1, NewSeen1} =
                        lists:foldl(
                          fun({Rel, N}, {A, S}) ->
                                  case maps:is_key(N, Seen) orelse maps:is_key(N, S) of
                                      true -> {A, S};
                                      false -> {[[{Rel, N} | Path] | A], S#{N => true}}
                                  end
                          end, {Acc, NewSeen}, Steps),
                    expand(Rest, Seen, To, MaxDepth, Acc1, NewSeen1)
            end
    end.

%%--------------------------------------------------------------------
-spec node_count() -> non_neg_integer().
node_count() -> table_size(?NODES).

-spec edge_count() -> non_neg_integer().
edge_count() -> table_size(?OUT).

table_size(T) ->
    case ets:info(T, size) of
        undefined -> 0;
        N -> N
    end.
