-module(book_api).
-export([start/0, stop/0, start_link/0]).

start() ->
    application:start(crypto),
    application:start(inets),
    application:start(book_api).

stop() ->
    inets:stop(httpd),
    application:stop(book_api).

start_link() ->
    book_api_sup:start_link().
