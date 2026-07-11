-module(book_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    book_db:init(),
    book_sup:start_link().

stop(_State) ->
    mnesia:stop(),
    ok.
