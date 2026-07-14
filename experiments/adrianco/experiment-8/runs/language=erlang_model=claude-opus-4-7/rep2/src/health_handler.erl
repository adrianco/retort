-module(health_handler).

-export([init/2]).

init(Req0, State) ->
    Body = iolist_to_binary(json:encode(#{status => <<"ok">>})),
    Req = cowboy_req:reply(200,
        #{<<"content-type">> => <<"application/json">>},
        Body, Req0),
    {ok, Req, State}.
