%%%-------------------------------------------------------------------
%%% @doc Shared scaffolding for the test suites: throw-away database
%%% directories and a thin JSON HTTP client built on `httpc'.
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_test_helper).

-compile({no_auto_import, [get/1]}).

-export([fresh_db_dir/1, start_app/1, stop_app/1, reset_db/0]).
-export([get/1, get/2, post/2, put/3, delete/1, request/4, url/1]).

%%%===================================================================
%%% Database / application lifecycle
%%%===================================================================

%% @doc An empty directory under `_build', unique to the calling suite.
-spec fresh_db_dir(atom()) -> file:filename().
fresh_db_dir(Suite) ->
    Dir = filename:join(["_build", "test", "tmp", atom_to_list(Suite)]),
    _ = file:del_dir_r(Dir),
    ok = filelib:ensure_path(Dir),
    Dir.

%% @doc Start the whole application on an ephemeral port with a clean
%% database, and return the state needed by {@link stop_app/1}.
-spec start_app(atom()) -> file:filename().
start_app(Suite) ->
    Dir = fresh_db_dir(Suite),
    %% Environment variables win over app config, so make sure a developer's
    %% shell settings cannot redirect the tests at a real server or database.
    os:unsetenv("BOOK_API_PORT"),
    os:unsetenv("BOOK_API_DB_DIR"),
    _ = application:load(book_api),
    ok = application:set_env(book_api, port, 0),
    ok = application:set_env(book_api, db_dir, Dir),
    {ok, _} = application:ensure_all_started(book_api),
    {ok, _} = application:ensure_all_started(inets),
    Dir.

-spec stop_app(file:filename()) -> ok.
stop_app(_Dir) ->
    ok = application:stop(book_api),
    ok = book_store:stop(),
    ok.

%% @doc Truncate all data so each test starts from a known empty state.
-spec reset_db() -> ok.
reset_db() ->
    {atomic, ok} = mnesia:clear_table(book),
    {atomic, ok} = mnesia:clear_table(book_counter),
    ok.

%%%===================================================================
%%% HTTP client
%%%===================================================================

url(Path) ->
    "http://127.0.0.1:" ++ integer_to_list(book_api_app:port()) ++ Path.

get(Path) ->
    request(get, Path, undefined, undefined).

%% @doc GET with a query string built from `Params' (keys and values are
%% percent-encoded for us).
get(Path, Params) ->
    %% compose_query mirrors the type of its input; the result is always
    %% percent-encoded ASCII, so flattening it to a string is lossless.
    Query = unicode:characters_to_list(uri_string:compose_query(Params)),
    request(get, Path ++ "?" ++ Query, undefined, undefined).

post(Path, Body) ->
    request(post, Path, "application/json", Body).

put(Path, ContentType, Body) ->
    request(put, Path, ContentType, Body).

delete(Path) ->
    request(delete, Path, undefined, undefined).

%% @doc Perform a request and decode the JSON response.
%%
%% Returns `#{status, headers, body}' where `body' is the decoded JSON
%% term, or the atom `no_content' when the response has an empty body.
-spec request(atom(), string(), string() | undefined, iodata() | undefined) ->
          #{status := non_neg_integer(), headers := [{string(), string()}],
            body := term()}.
request(Method, Path, ContentType, Body) ->
    Request =
        case ContentType of
            undefined -> {url(Path), []};
            _ -> {url(Path), [], ContentType, encode_body(Body)}
        end,
    {ok, {{_Vsn, Status, _Reason}, Headers, Raw}} =
        httpc:request(Method, Request, [], [{body_format, binary}]),
    #{status => Status, headers => Headers, body => decode_body(Raw)}.

encode_body(Body) when is_binary(Body); is_list(Body) -> Body;
encode_body(Body) when is_map(Body) -> iolist_to_binary(json:encode(Body)).

decode_body(<<>>) -> no_content;
decode_body(Raw) -> json:decode(Raw).
