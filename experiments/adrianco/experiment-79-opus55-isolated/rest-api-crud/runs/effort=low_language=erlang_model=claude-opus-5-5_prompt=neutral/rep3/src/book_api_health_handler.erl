-module(book_api_health_handler).
-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Req =
        case cowboy_req:method(Req0) of
            <<"GET">> ->
                book_api_books_handler:reply(200, #{status => <<"ok">>}, Req0);
            _ ->
                book_api_books_handler:method_not_allowed(<<"GET">>, Req0)
        end,
    {ok, Req, State}.
