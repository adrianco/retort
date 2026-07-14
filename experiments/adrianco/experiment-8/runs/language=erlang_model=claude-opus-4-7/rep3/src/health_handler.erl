-module(health_handler).

-export([init/2]).

init(Req0, State) ->
    Req = book_util:json_reply(200, #{status => <<"ok">>}, Req0),
    {ok, Req, State}.
