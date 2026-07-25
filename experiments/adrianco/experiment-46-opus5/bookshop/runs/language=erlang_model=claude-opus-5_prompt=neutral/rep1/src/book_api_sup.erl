%%%-------------------------------------------------------------------
%%% @doc Root supervisor. The HTTP acceptor pool is supervised by Ranch's
%%% own supervision tree and Mnesia by the `mnesia' application, so this
%%% supervisor currently has no children of its own; it exists to give the
%%% application a well-formed supervision tree to hang future workers off.
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_sup).

-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{strategy => one_for_one, intensity => 5, period => 10},
    {ok, {SupFlags, []}}.
