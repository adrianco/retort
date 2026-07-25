%%%-------------------------------------------------------------------
%%% @doc Catch-all handler so unmatched paths get the same JSON error
%%% envelope as everything else rather than Cowboy's HTML 404.
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_notfound_h).

-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Message = ["No route for ", cowboy_req:method(Req0), " ",
               cowboy_req:path(Req0)],
    Req = book_api_http:error(404, <<"not_found">>, Message, Req0),
    {ok, Req, State}.
