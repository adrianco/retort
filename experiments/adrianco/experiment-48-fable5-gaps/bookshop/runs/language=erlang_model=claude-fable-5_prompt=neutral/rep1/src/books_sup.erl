-module(books_sup).
-behaviour(supervisor).

-export([start_link/0]).
-export([init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    DataFile = application:get_env(books, data_file, "books.dets"),
    SupFlags = #{strategy => one_for_one, intensity => 5, period => 10},
    Children = [
        #{id => book_store,
          start => {book_store, start_link, [DataFile]},
          restart => permanent,
          shutdown => 5000,
          type => worker,
          modules => [book_store]}
    ],
    {ok, {SupFlags, Children}}.
