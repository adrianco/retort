-module(book_api_rest).

-export([start_link/0]).

-export([init/2]).

start_link() ->
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", book_api_health, []},
            {"/books", book_api_handler, []},
            {"/books/:id", book_api_handler, []}
        ]}
    ]),
    {ok, _} = cowboy:start_clear(book_api_http,
        [{port, 8080}],
        #{env => #{dispatch => Dispatch}}
    ),
    {ok, self()}.

init(Req, _Opts) ->
    {ok, Req, undefined}.
