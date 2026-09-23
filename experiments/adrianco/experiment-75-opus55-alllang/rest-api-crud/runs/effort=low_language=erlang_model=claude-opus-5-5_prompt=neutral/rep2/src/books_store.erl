%% Persistent book storage backed by DETS (Erlang's embedded disk DB).
-module(books_store).
-behaviour(gen_server).
-export([start_link/1, create/1, list/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, terminate/2]).

-define(TAB, books_dets).

start_link(File) -> gen_server:start_link({local, ?MODULE}, ?MODULE, File, []).

create(Book) -> gen_server:call(?MODULE, {create, Book}).
list(Author) -> gen_server:call(?MODULE, {list, Author}).
get(Id) -> gen_server:call(?MODULE, {get, Id}).
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

init(File) ->
    process_flag(trap_exit, true),
    {ok, ?TAB} = dets:open_file(?TAB, [{file, File}, {type, set}]),
    NextId = dets:foldl(fun({Id, _}, Max) when is_integer(Id) -> max(Id, Max);
                           (_, Max) -> Max end, 0, ?TAB) + 1,
    {ok, NextId}.

handle_call({create, Book}, _From, Next) ->
    Stored = Book#{<<"id">> => Next},
    ok = dets:insert(?TAB, {Next, Stored}),
    ok = dets:sync(?TAB),
    {reply, Stored, Next + 1};
handle_call({list, Author}, _From, Next) ->
    All = [B || {_, B} <- dets:match_object(?TAB, '_'),
                Author =:= undefined orelse maps:get(<<"author">>, B) =:= Author],
    {reply, lists:sort(fun(A, B) -> maps:get(<<"id">>, A) =< maps:get(<<"id">>, B) end, All), Next};
handle_call({get, Id}, _From, Next) ->
    {reply, lookup(Id), Next};
handle_call({update, Id, Book}, _From, Next) ->
    case lookup(Id) of
        {ok, _} ->
            Stored = Book#{<<"id">> => Id},
            ok = dets:insert(?TAB, {Id, Stored}),
            ok = dets:sync(?TAB),
            {reply, {ok, Stored}, Next};
        E -> {reply, E, Next}
    end;
handle_call({delete, Id}, _From, Next) ->
    case lookup(Id) of
        {ok, _} -> ok = dets:delete(?TAB, Id), ok = dets:sync(?TAB), {reply, ok, Next};
        E -> {reply, E, Next}
    end.

handle_cast(_, S) -> {noreply, S}.

terminate(_, _) -> dets:close(?TAB).

lookup(Id) ->
    case dets:lookup(?TAB, Id) of
        [{_, B}] -> {ok, B};
        [] -> {error, not_found}
    end.
