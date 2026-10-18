%% @doc Escript entry point.
%%   brazil_soccer_mcp [DataDir]        (default: $BSM_DATA_DIR or data/kaggle)
-module(brazil_soccer_mcp).
-export([main/1]).

main(Args) ->
    DataDir = case Args of
                  [Dir | _] -> Dir;
                  [] -> case os:getenv("BSM_DATA_DIR") of
                            false -> "data/kaggle";
                            Env -> Env
                        end
              end,
    #{matches := M, players := P} = bsm_store:load(DataDir),
    io:format(standard_error, "brazil-soccer-mcp: loaded ~p matches, ~p players from ~s~n",
              [M, P, DataDir]),
    bsm_mcp:run().
