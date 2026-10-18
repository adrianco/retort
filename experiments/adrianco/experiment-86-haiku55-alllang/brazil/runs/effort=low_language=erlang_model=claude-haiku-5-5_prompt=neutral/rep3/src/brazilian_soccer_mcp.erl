%%% Escript entry point.
%%%
%%% Usage: brazilian_soccer_mcp [DataDir]
%%% DataDir defaults to $BS_DATA_DIR, then data/kaggle relative to the
%%% current directory. The dataset is loaded once and then served over stdio.
-module(brazilian_soccer_mcp).

-export([main/1]).

-spec main([string()]) -> ok.
main(Args) ->
    Dir = data_dir(Args),
    {Micros, Data} = timer:tc(bs_data, load, [Dir]),
    io:format(standard_error, "Loaded ~B matches, ~B players from ~ts in ~.2fs~n",
              [length(maps:get(matches, Data)), length(maps:get(players, Data)),
               Dir, Micros / 1000000]),
    io:setopts(standard_io, [{encoding, unicode}]),
    bs_mcp:run(Data).

data_dir([Dir | _]) -> Dir;
data_dir([]) ->
    case os:getenv("BS_DATA_DIR") of
        false -> "data/kaggle";
        Dir -> Dir
    end.
