-module(book_api_health).

-export([init/2]).

init(Req, _Opts) ->
    case book_api_db:health_check() of
        {ok, healthy} ->
            Body = jiffy:encode(#{status => healthy}),
            {ok, Req2} = cowboy_req:reply(200, 
                #{<<"content-type">> => <<"application/json">>}, 
                Body, Req),
            {ok, Req2, undefined};
        Error ->
            Body = jiffy:encode(#{status => unhealthy, error => atom_to_list(Error)}),
            {ok, Req2} = cowboy_req:reply(503, 
                #{<<"content-type">> => <<"application/json">>}, 
                Body, Req),
            {ok, Req2, undefined}
    end.
