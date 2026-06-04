%%% @doc Top level supervisor. Owns the database and the HTTP server.
-module(booklib_sup).
-behaviour(supervisor).

-export([start_link/0]).
-export([init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{strategy => one_for_one, intensity => 10, period => 10},
    Children = [
        #{id => booklib_db,
          start => {booklib_db, start_link, []},
          restart => permanent,
          shutdown => 5000,
          type => worker,
          modules => [booklib_db]},
        #{id => booklib_server,
          start => {booklib_server, start_link, []},
          restart => permanent,
          shutdown => 5000,
          type => worker,
          modules => [booklib_server]}
    ],
    {ok, {SupFlags, Children}}.
