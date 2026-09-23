-module(books_app).
-behaviour(application).
-export([start/2, stop/1]).

start(_Type, _Args) ->
    {ok, Port} = application:get_env(books, port),
    {ok, File} = application:get_env(books, db_file),
    ok = books_store:open(File),
    {ok, Pid} = inets:start(httpd, [{port, Port},
                                    {server_name, "books"},
                                    {server_root, "."},
                                    {document_root, "."},
                                    {bind_address, any},
                                    {modules, [books_http]}]),
    persistent_term:put(books_httpd, Pid),
    {ok, spawn_link(fun() -> receive stop -> ok end end)}.

stop(_) ->
    catch inets:stop(httpd, persistent_term:get(books_httpd)),
    books_store:close(),
    ok.
