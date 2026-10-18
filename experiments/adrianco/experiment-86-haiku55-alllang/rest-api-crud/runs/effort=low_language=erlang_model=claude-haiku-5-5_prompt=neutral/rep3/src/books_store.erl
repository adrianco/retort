%% Persistent book storage backed by DETS (OTP's embedded disk-based store).
%% All access is serialised through this gen_server.
-module(books_store).
-behaviour(gen_server).

-export([start_link/0, start_link/1]).
-export([create/1, get/1, list/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(TABLE, books).

start_link() ->
    start_link(#{}).

%% Opts: #{file => FileName}; defaults to the db_file application setting.
start_link(Opts) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, Opts, []).

%% Attrs is a map with binary keys; the store assigns the id.
create(Attrs) ->
    gen_server:call(?MODULE, {create, Attrs}).

get(Id) ->
    gen_server:call(?MODULE, {get, Id}).

%% Author is undefined (no filter) or a binary, compared case-insensitively.
list(Author) ->
    gen_server:call(?MODULE, {list, Author}).

%% Changes is merged over the existing book.
update(Id, Changes) ->
    gen_server:call(?MODULE, {update, Id, Changes}).

delete(Id) ->
    gen_server:call(?MODULE, {delete, Id}).

init(Opts) ->
    File = maps:get(file, Opts, default_file()),
    {ok, Tab} = dets:open_file(?TABLE, [{file, File}, {type, set}]),
    Next = dets:foldl(fun({Id, _}, Max) -> max(Id, Max) end, 0, Tab) + 1,
    {ok, #{tab => Tab, next => Next}}.

handle_call({create, Attrs}, _From, #{tab := Tab, next := Id} = State) ->
    Book = Attrs#{<<"id">> => Id},
    ok = dets:insert(Tab, {Id, Book}),
    {reply, {ok, Book}, State#{next := Id + 1}};
handle_call({get, Id}, _From, #{tab := Tab} = State) ->
    {reply, lookup(Tab, Id), State};
handle_call({list, Author}, _From, #{tab := Tab} = State) ->
    All = dets:foldl(fun({_, Book}, Acc) -> [Book | Acc] end, [], Tab),
    Matching = [B || B <- All, matches_author(B, Author)],
    Sorted = lists:sort(fun(A, B) -> maps:get(<<"id">>, A) =< maps:get(<<"id">>, B) end, Matching),
    {reply, {ok, Sorted}, State};
handle_call({update, Id, Changes}, _From, #{tab := Tab} = State) ->
    case lookup(Tab, Id) of
        {ok, Book} ->
            Updated = maps:merge(Book, Changes),
            ok = dets:insert(Tab, {Id, Updated}),
            {reply, {ok, Updated}, State};
        not_found ->
            {reply, not_found, State}
    end;
handle_call({delete, Id}, _From, #{tab := Tab} = State) ->
    case lookup(Tab, Id) of
        {ok, _} ->
            ok = dets:delete(Tab, Id),
            {reply, ok, State};
        not_found ->
            {reply, not_found, State}
    end.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Msg, State) ->
    {noreply, State}.

terminate(_Reason, #{tab := Tab}) ->
    dets:close(Tab),
    ok.

default_file() ->
    application:get_env(books_api, db_file, "books.dets").

lookup(Tab, Id) ->
    case dets:lookup(Tab, Id) of
        [{_, Book}] -> {ok, Book};
        [] -> not_found
    end.

matches_author(_Book, undefined) ->
    true;
matches_author(#{<<"author">> := Author}, Filter) ->
    string:casefold(Author) =:= string:casefold(Filter).
