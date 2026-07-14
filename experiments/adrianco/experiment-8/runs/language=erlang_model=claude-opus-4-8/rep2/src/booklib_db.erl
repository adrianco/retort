%%% @doc Persistent storage for books backed by `dets', Erlang's built-in
%%% disk-based embedded database. Runs as a gen_server that owns the table so
%%% access is serialised and the table lifecycle is tied to the supervisor.
%%%
%%% Objects stored in the table:
%%%   {Id :: pos_integer(), Book :: map()}  -- a book record
%%%   {seq, N :: non_neg_integer()}         -- the auto-increment id counter
-module(booklib_db).
-behaviour(gen_server).

-export([start_link/0, create/1, list/1, get/1, update/2, delete/1]).
-export([validate/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

-define(TABLE, booklib_books).

%%====================================================================
%% Public API
%%====================================================================

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

%% @doc Create a book from a decoded-JSON map. Returns the stored book
%% (including its generated id) or a list of validation errors.
-spec create(map()) -> {ok, map()} | {error, {validation, [binary()]}}.
create(Attrs) ->
    gen_server:call(?MODULE, {create, Attrs}).

%% @doc List all books, optionally filtered by author (exact, case-insensitive).
-spec list(binary() | undefined) -> [map()].
list(AuthorFilter) ->
    gen_server:call(?MODULE, {list, AuthorFilter}).

%% @doc Fetch a single book by id.
-spec get(pos_integer()) -> {ok, map()} | {error, not_found}.
get(Id) ->
    gen_server:call(?MODULE, {get, Id}).

%% @doc Replace the mutable fields of an existing book.
-spec update(pos_integer(), map()) ->
    {ok, map()} | {error, not_found} | {error, {validation, [binary()]}}.
update(Id, Attrs) ->
    gen_server:call(?MODULE, {update, Id, Attrs}).

%% @doc Remove a book by id.
-spec delete(pos_integer()) -> ok | {error, not_found}.
delete(Id) ->
    gen_server:call(?MODULE, {delete, Id}).

%%====================================================================
%% gen_server callbacks
%%====================================================================

init([]) ->
    process_flag(trap_exit, true),
    File = application:get_env(booklib, db_file, "books.dets"),
    {ok, ?TABLE} = dets:open_file(?TABLE, [{file, File}, {type, set}, {keypos, 1}]),
    %% Ensure the id counter exists.
    case dets:lookup(?TABLE, seq) of
        [] -> ok = dets:insert(?TABLE, {seq, 0});
        _  -> ok
    end,
    {ok, #{table => ?TABLE}}.

handle_call({create, Attrs}, _From, State) ->
    case validate(Attrs) of
        {ok, Fields} ->
            Id = dets:update_counter(?TABLE, seq, 1),
            Book = Fields#{<<"id">> => Id},
            ok = dets:insert(?TABLE, {Id, Book}),
            ok = dets:sync(?TABLE),
            {reply, {ok, Book}, State};
        {error, Errors} ->
            {reply, {error, {validation, Errors}}, State}
    end;

handle_call({list, AuthorFilter}, _From, State) ->
    Books = dets:foldl(fun({seq, _}, Acc) -> Acc;
                          ({_Id, Book}, Acc) -> [Book | Acc]
                       end, [], ?TABLE),
    Filtered = filter_by_author(Books, AuthorFilter),
    Sorted = lists:sort(fun(A, B) ->
                           maps:get(<<"id">>, A) =< maps:get(<<"id">>, B)
                        end, Filtered),
    {reply, Sorted, State};

handle_call({get, Id}, _From, State) ->
    {reply, lookup(Id), State};

handle_call({update, Id, Attrs}, _From, State) ->
    case lookup(Id) of
        {ok, _Existing} ->
            case validate(Attrs) of
                {ok, Fields} ->
                    Book = Fields#{<<"id">> => Id},
                    ok = dets:insert(?TABLE, {Id, Book}),
                    ok = dets:sync(?TABLE),
                    {reply, {ok, Book}, State};
                {error, Errors} ->
                    {reply, {error, {validation, Errors}}, State}
            end;
        {error, not_found} ->
            {reply, {error, not_found}, State}
    end;

handle_call({delete, Id}, _From, State) ->
    case lookup(Id) of
        {ok, _Book} ->
            ok = dets:delete(?TABLE, Id),
            ok = dets:sync(?TABLE),
            {reply, ok, State};
        {error, not_found} ->
            {reply, {error, not_found}, State}
    end;

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_request}, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    dets:close(?TABLE),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

%%====================================================================
%% Internal helpers
%%====================================================================

lookup(Id) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] -> {ok, Book};
        []           -> {error, not_found}
    end.

filter_by_author(Books, undefined) ->
    Books;
filter_by_author(Books, Author) ->
    Wanted = string:lowercase(Author),
    [B || B <- Books,
          string:lowercase(maps:get(<<"author">>, B, <<>>)) =:= Wanted].

%% @doc Validate and normalise incoming book attributes.
%% `title' and `author' are required and must be non-empty strings.
%% `year' is an optional integer; `isbn' is an optional string.
-spec validate(map()) -> {ok, map()} | {error, [binary()]}.
validate(Attrs) when is_map(Attrs) ->
    {Title, TErrs} = required_string(<<"title">>, Attrs),
    {Author, AErrs} = required_string(<<"author">>, Attrs),
    {Year, YErrs} = optional_integer(<<"year">>, Attrs),
    {Isbn, IErrs} = optional_string(<<"isbn">>, Attrs),
    case TErrs ++ AErrs ++ YErrs ++ IErrs of
        [] ->
            {ok, #{<<"title">> => Title,
                   <<"author">> => Author,
                   <<"year">> => Year,
                   <<"isbn">> => Isbn}};
        Errors ->
            {error, Errors}
    end;
validate(_) ->
    {error, [<<"request body must be a JSON object">>]}.

required_string(Key, Attrs) ->
    case maps:get(Key, Attrs, undefined) of
        Bin when is_binary(Bin) ->
            case string:trim(Bin) of
                <<>> -> {undefined, [<<Key/binary, " must not be empty">>]};
                _    -> {Bin, []}
            end;
        undefined ->
            {undefined, [<<Key/binary, " is required">>]};
        _ ->
            {undefined, [<<Key/binary, " must be a string">>]}
    end.

optional_string(Key, Attrs) ->
    case maps:get(Key, Attrs, null) of
        null               -> {null, []};
        Bin when is_binary(Bin) -> {Bin, []};
        _                  -> {null, [<<Key/binary, " must be a string">>]}
    end.

optional_integer(Key, Attrs) ->
    case maps:get(Key, Attrs, null) of
        null              -> {null, []};
        Int when is_integer(Int) -> {Int, []};
        _                 -> {null, [<<Key/binary, " must be an integer">>]}
    end.
