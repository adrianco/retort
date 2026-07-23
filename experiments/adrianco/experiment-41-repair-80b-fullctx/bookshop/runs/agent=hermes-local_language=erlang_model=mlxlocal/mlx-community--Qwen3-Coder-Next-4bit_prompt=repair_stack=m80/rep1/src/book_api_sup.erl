-module(book_api_sup).

-behaviour(supervisor).

-export([start_link/0]).
-export([init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{
        strategy => one_for_one,
        intensity => 5,
        period => 10
    },
    
    ChildSpecs = [
        #{
            id => book_api_db,
            start => {book_api_db, start_link, []},
            restart => permanent,
            shutdown => 5000,
            modules => [book_api_db]
        },
        #{
            id => book_api_rest,
            start => {book_api_rest, start_link, []},
            restart => permanent,
            shutdown => 5000,
            modules => [book_api_rest]
        }
    ],
    {ok, {SupFlags, ChildSpecs}}.
