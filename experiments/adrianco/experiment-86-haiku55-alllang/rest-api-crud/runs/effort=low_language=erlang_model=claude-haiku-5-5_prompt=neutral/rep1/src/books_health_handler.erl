-module(books_health_handler).
-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Req = case cowboy_req:method(Req0) of
              <<"GET">> -> health(Req0);
              _ -> method_not_allowed(<<"GET">>, Req0)
          end,
    {ok, Req, State}.

health(Req) ->
    case books_db:ping() of
        ok -> books_http:reply_json(200, #{<<"status">> => <<"ok">>}, Req);
        {error, _} -> books_http:reply_json(503, #{<<"status">> => <<"unavailable">>}, Req)
    end.

method_not_allowed(Allow, Req0) ->
    Req = cowboy_req:set_resp_header(<<"allow">>, Allow, Req0),
    books_http:reply_error(405, <<"method not allowed">>, Req).
