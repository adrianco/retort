-module(bookapi_health_handler).

-export([init/3]).

init(Req, Opts, State) ->
    cowboy_req:reply(200,
        #{<<"content-type">> => <<"application/json">>},
        jiffy:encode(#{status => ok}), Req),
    {ok, Req, State, Opts}.
