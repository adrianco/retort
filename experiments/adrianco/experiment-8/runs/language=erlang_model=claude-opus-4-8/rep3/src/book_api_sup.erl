%%% @doc Top-level supervisor. The HTTP listener is supervised by Cowboy
%%% itself, so this supervisor currently has no children of its own.
-module(book_api_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{strategy => one_for_one, intensity => 5, period => 10},
    {ok, {SupFlags, []}}.
