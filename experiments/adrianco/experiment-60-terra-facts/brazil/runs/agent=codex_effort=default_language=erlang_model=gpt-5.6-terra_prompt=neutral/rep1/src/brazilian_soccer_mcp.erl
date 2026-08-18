%% Public application entry point.  Keep the protocol loop in soccer_mcp so it
%% is also easy to exercise directly in unit tests, while this module provides
%% the conventional zero-arity Erlang entry points used by launchers.
-module(brazilian_soccer_mcp).

-export([main/0, main/1, run/0, run/1]).

main() -> main(init:get_plain_arguments()).
main(Args) -> soccer_mcp:main(Args).

run() -> main().
run(Args) -> main(Args).
