%% -*- erlang -*-
%% This file is part of Book API.
%%
%% Book API is free software: you can redistribute it and/or modify
%% it under the terms of the GNU Lesser General Public License as published by
%% the Free Software Foundation, either version 3 of the License, or
%% (at your option) any later version.
%%
%% Book API is distributed in the hope that it will be useful,
%% but WITHOUT ANY WARRANTY; without even the implied warranty of
%% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
%% GNU Lesser General Public License for more details.
%%
%% You should have received a copy of the GNU Lesser General Public License
%% along with Book API. If not, see <http://www.gnu.org/licenses/>.

-module(book_api_sup).

-behaviour(supervisor).

-export([start_link/0, init/1]).

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
            type => worker,
            modules => [book_api_db]
        },
        #{
            id => book_api_routes,
            start => {book_api_routes, start_link, []},
            restart => permanent,
            shutdown => 5000,
            type => worker,
            modules => [book_api_routes]
        }
    ],

    {ok, {SupFlags, ChildSpecs}}.
