%%%-------------------------------------------------------------------
%%% @doc GET /health — liveness/readiness probe.
%%%
%%% The check is not merely "the process answered": it touches the
%%% database, so a healthy response also means storage is reachable.
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_health_h).

-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Req =
        case cowboy_req:method(Req0) of
            Method when Method =:= <<"GET">>; Method =:= <<"HEAD">> ->
                health(Req0);
            _Other ->
                book_api_http:method_not_allowed([<<"GET">>, <<"HEAD">>], Req0)
        end,
    {ok, Req, State}.

health(Req) ->
    try book_store:count() of
        Count ->
            book_api_http:json(200,
                               #{<<"status">> => <<"ok">>,
                                 <<"database">> => <<"ok">>,
                                 <<"books">> => Count,
                                 <<"uptime_seconds">> => uptime_seconds()},
                               Req)
    catch
        Class:Reason ->
            logger:error("health check failed: ~p:~p", [Class, Reason]),
            book_api_http:json(503,
                               #{<<"status">> => <<"error">>,
                                 <<"database">> => <<"unavailable">>},
                               Req)
    end.

uptime_seconds() ->
    {Millis, _SinceLastCall} = erlang:statistics(wall_clock),
    Millis div 1000.
