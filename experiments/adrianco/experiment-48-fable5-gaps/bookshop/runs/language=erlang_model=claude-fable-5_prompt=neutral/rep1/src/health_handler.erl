-module(health_handler).
-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Req = cowboy_req:reply(200,
                           #{<<"content-type">> => <<"application/json">>},
                           json:encode(#{status => <<"ok">>}),
                           Req0),
    {ok, Req, State}.
