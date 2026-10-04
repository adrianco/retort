-module(books_health_handler).

-export([init/2]).

init(Req0, State) ->
    Req = case cowboy_req:method(Req0) of
              <<"GET">> -> books_handler:reply(200, #{status => <<"ok">>}, Req0);
              _ -> books_handler:reply(405, #{error => <<"method not allowed">>}, Req0)
          end,
    {ok, Req, State}.
