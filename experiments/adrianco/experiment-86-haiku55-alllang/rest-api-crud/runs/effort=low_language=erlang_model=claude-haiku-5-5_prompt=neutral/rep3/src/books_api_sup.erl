-module(books_api_sup).
-behaviour(supervisor).

-export([start_link/0]).
-export([init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Children = [
        #{id => books_store, start => {books_store, start_link, []}},
        #{id => books_http, start => {books_http, start_link, [http_port()]}}
    ],
    {ok, {#{strategy => one_for_one, intensity => 5, period => 10}, Children}}.

%% PORT env var overrides the http_port application setting.
http_port() ->
    case os:getenv("PORT") of
        false -> application:get_env(books_api, http_port, 8080);
        Port -> list_to_integer(Port)
    end.
