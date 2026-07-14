%%% @doc Application entry point for the booklib service.
-module(booklib_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    booklib_sup:start_link().

stop(_State) ->
    ok.
