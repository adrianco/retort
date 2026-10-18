%% Persistent book storage backed by DETS (OTP's built-in disk-based table).
%% All access is serialised through this gen_server.
-module(books_store).
-behaviour(gen_server).

-export([start_link/1, create/1, get/1, list/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(TABLE, books).
-define(COUNTER, counter).

start_link(DbFile) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, DbFile, []).

-spec create(map()) -> {ok, map()}.
create(Attrs) -> gen_server:call(?MODULE, {create, Attrs}).

-spec get(pos_integer()) -> {ok, map()} | {error, not_found}.
get(Id) -> gen_server:call(?MODULE, {get, Id}).

-spec list(binary() | undefined) -> {ok, [map()]}.
list(Author) -> gen_server:call(?MODULE, {list, Author}).

-spec update(pos_integer(), map()) -> {ok, map()} | {error, not_found}.
update(Id, Attrs) -> gen_server:call(?MODULE, {update, Id, Attrs}).

-spec delete(pos_integer()) -> ok | {error, not_found}.
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

init(DbFile) ->
    {ok, ?TABLE} = dets:open_file(?TABLE, [{file, DbFile}, {type, set}]),
    case dets:member(?TABLE, ?COUNTER) of
        true -> ok;
        false -> ok = dets:insert(?TABLE, {?COUNTER, 0})
    end,
    {ok, no_state}.

handle_call({create, Attrs}, _From, State) ->
    Id = dets:update_counter(?TABLE, ?COUNTER, 1),
    Book = Attrs#{id => Id},
    ok = dets:insert(?TABLE, {Id, Book}),
    {reply, {ok, Book}, State};
handle_call({get, Id}, _From, State) ->
    {reply, fetch(Id), State};
handle_call({list, Author}, _From, State) ->
    Matches = [{Id, B} || {Id, B} <- dets:match_object(?TABLE, '_'),
                          is_integer(Id), matches_author(B, Author)],
    Books = [B || {_, B} <- lists:keysort(1, Matches)],
    {reply, {ok, Books}, State};
handle_call({update, Id, Attrs}, _From, State) ->
    case fetch(Id) of
        {ok, _} ->
            Book = Attrs#{id => Id},
            ok = dets:insert(?TABLE, {Id, Book}),
            {reply, {ok, Book}, State};
        Error ->
            {reply, Error, State}
    end;
handle_call({delete, Id}, _From, State) ->
    case fetch(Id) of
        {ok, _} ->
            ok = dets:delete(?TABLE, Id),
            {reply, ok, State};
        Error ->
            {reply, Error, State}
    end.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Msg, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    dets:close(?TABLE),
    ok.

fetch(Id) when is_integer(Id) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] -> {ok, Book};
        [] -> {error, not_found}
    end;
fetch(_) ->
    {error, not_found}.

matches_author(_, undefined) -> true;
matches_author(#{author := Author}, Author) -> true;
matches_author(_, _) -> false.
