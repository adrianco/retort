-module(books_sup).
-behaviour(supervisor).

-export([start_link/1]).
-export([init/1]).

start_link(DbPath) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, DbPath).

init(DbPath) ->
    Flags = #{strategy => one_for_one, intensity => 5, period => 10},
    Children = [
        #{id => books_db,
          start => {books_db, start_link, [DbPath]},
          restart => permanent,
          shutdown => 5000,
          type => worker,
          modules => [books_db]}
    ],
    {ok, {Flags, Children}}.
