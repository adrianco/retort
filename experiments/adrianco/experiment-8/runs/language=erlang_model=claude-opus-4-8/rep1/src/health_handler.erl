%%%-------------------------------------------------------------------
%% @doc health_handler: GET /health liveness probe.
%%%-------------------------------------------------------------------
-module(health_handler).

-export([init/2]).

init(Req0, State) ->
    Body = json:encode(#{<<"status">> => <<"ok">>}),
    Req = cowboy_req:reply(200,
        #{<<"content-type">> => <<"application/json">>},
        Body,
        Req0),
    {ok, Req, State}.
