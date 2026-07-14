-module(bookapi_sup).

-behaviour(supervisor).

-export([init/1, start/0]).

start() ->
    application:start(bookapi).

init(_Args) ->
    SupFlags = #{strategy => one_for_one,
                 intensity => 5,
                 period => 10},
    DbChild = #{id => bookapi_db,
                start => {bookapi_db, start_link, []},
                restart => permanent,
                shutdown => 5000,
                type => worker,
                modules => [bookapi_db]},
    ServerChild = #{id => bookapi_server,
                    start => {bookapi_server, start_link, []},
                    restart => permanent,
                    shutdown => 5000,
                    type => worker,
                    modules => [bookapi_server]},
    {ok, {SupFlags, [DbChild, ServerChild]}}.
