-module(books_sup).
-behaviour(supervisor).

-export([start_link/1, init/1]).

start_link(DbFile) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, DbFile).

init(DbFile) ->
    Flags = #{strategy => one_for_one, intensity => 5, period => 10},
    Store = #{id => books_store,
              start => {books_store, start_link, [DbFile]},
              restart => permanent,
              shutdown => 5000,
              type => worker,
              modules => [books_store]},
    {ok, {Flags, [Store]}}.
