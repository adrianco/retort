-module(br_soccer_mcp_main).
-export([main/1]).

main(Args) ->
    DataDir = case Args of
        [D | _] -> D;
        []      -> "data/kaggle"
    end,
    br_soccer_mcp_server:start(DataDir).
