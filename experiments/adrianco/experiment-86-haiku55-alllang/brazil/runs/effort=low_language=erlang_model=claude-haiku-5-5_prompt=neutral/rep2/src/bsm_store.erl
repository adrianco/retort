%% @doc Holds the loaded dataset in persistent_term. The data is read-only
%% after startup, so reads are lock-free and copy-free.
-module(bsm_store).
-export([load/1, matches/0, players/0]).

-spec load(file:filename()) -> #{matches := non_neg_integer(), players := non_neg_integer()}.
load(Dir) ->
    Matches = bsm_loader:matches(Dir),
    Players = bsm_loader:players(Dir),
    persistent_term:put({?MODULE, matches}, Matches),
    persistent_term:put({?MODULE, players}, Players),
    #{matches => length(Matches), players => length(Players)}.

%% Raises badarg if load/1 has not been called.
matches() -> persistent_term:get({?MODULE, matches}).
players() -> persistent_term:get({?MODULE, players}).
