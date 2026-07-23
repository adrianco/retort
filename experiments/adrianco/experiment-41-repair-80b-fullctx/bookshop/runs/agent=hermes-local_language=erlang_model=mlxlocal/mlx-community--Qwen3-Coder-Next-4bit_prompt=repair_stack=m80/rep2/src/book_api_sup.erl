-module(book_api_sup).
-behaviour(supervisor).

-export([start_link/0]).
-export([init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    ChildSpecs = [
        #{
            id => book_api_db,
            start => {book_api_db, start_link, []},
            restart => permanent,
            shutdown => 5000,
            type => worker,
            modules => [book_api_db]
        },
        #{
            id => book_api_http,
            start => {book_api_http, start, []},
            restart => permanent,
            shutdown => 5000,
            type => worker,
            modules => [book_api_http]
        }
    ],
    {ok, {{one_for_one, 3, 10}, ChildSpecs}}.
