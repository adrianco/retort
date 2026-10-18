%%% Shared helpers for the test suites: fixture locations and cached data.
-module(bs_test_support).

-export([fixture_dir/0, real_data_dir/0, fixture_data/0, u/1]).

%% Small, hand-checked CSV files under test/fixtures.
fixture_dir() ->
    filename:join(filename:dirname(?FILE), "fixtures").

%% The full Kaggle datasets under data/kaggle (may be absent).
real_data_dir() ->
    filename:join([filename:dirname(?FILE), "..", "data", "kaggle"]).

fixture_data() ->
    bs_data:load(fixture_dir()).

%% Erlang string literals cannot hold non-ASCII as <<"...">> binaries.
u(Text) -> unicode:characters_to_binary(Text).
