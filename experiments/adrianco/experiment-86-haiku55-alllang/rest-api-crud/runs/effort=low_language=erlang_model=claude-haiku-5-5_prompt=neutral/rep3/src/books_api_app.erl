-module(books_api_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    books_api_sup:start_link().

stop(_State) ->
    ok.
