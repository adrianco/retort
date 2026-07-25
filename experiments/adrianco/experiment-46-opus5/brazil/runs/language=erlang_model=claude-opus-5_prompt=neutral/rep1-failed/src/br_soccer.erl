%%%-------------------------------------------------------------------
%%% @doc Command line entry point (the escript's `main/1').
%%%
%%% ```
%%% br_soccer_mcp serve            # MCP server on stdin/stdout (default)
%%% br_soccer_mcp ask "Who won the 2019 Brasileirao?"
%%% br_soccer_mcp call standings '{"season":2019}'
%%% br_soccer_mcp demo             # answer every sample question
%%% br_soccer_mcp tools            # list the MCP tools
%%% br_soccer_mcp info             # what is loaded
%%% '''
%%% @end
%%%-------------------------------------------------------------------
-module(br_soccer).

-export([main/1, start/0, stop/0]).

%%--------------------------------------------------------------------
%% @doc escript entry point.
-spec main([string()]) -> no_return().
main(Args) ->
    br_mcp_stdio:configure_logging(),
    case Args of
        [] -> serve();
        ["serve" | _] -> serve();
        ["ask" | Rest] -> ask(string:join(Rest, " "));
        ["call", Tool | Rest] -> call(Tool, Rest);
        ["demo" | _] -> demo();
        ["tools" | _] -> tools();
        ["info" | _] -> info();
        ["-h" | _] -> usage();
        ["--help" | _] -> usage();
        ["help" | _] -> usage();
        Other ->
            io:format(standard_error, "unknown arguments: ~p~n", [Other]),
            usage(),
            halt(2)
    end.

%%--------------------------------------------------------------------
%% @doc Start the application (loads the data sets).
-spec start() -> ok | {error, term()}.
start() ->
    case application:ensure_all_started(br_soccer) of
        {ok, _} -> ok;
        {error, Reason} -> {error, Reason}
    end.

-spec stop() -> ok.
stop() -> application:stop(br_soccer).

%%====================================================================
%% Modes
%%====================================================================

serve() ->
    ok = ensure_started(),
    br_mcp_stdio:run(),
    halt(0).

ask(Question) ->
    ok = ensure_started(),
    case br_nl:answer(Question) of
        {ok, #{answer := Answer, interpretation := How}} ->
            io:format("~ts~n~n[~ts]~n", [Answer, How]),
            halt(0);
        {error, Error} ->
            io:format(standard_error, "~ts~n", [br_format:error_text(Error)]),
            halt(1)
    end.

call(Tool, Rest) ->
    ok = ensure_started(),
    Args = case Rest of
               [] -> #{};
               [Json | _] ->
                   case br_json:decode(iolist_to_binary(Json)) of
                       {ok, Map} when is_map(Map) -> Map;
                       _ ->
                           io:format(standard_error, "arguments must be a JSON object~n", []),
                           halt(2)
                   end
           end,
    Name = iolist_to_binary(Tool),
    case br_mcp_tools:invoke(Name, Args) of
        {ok, Result} ->
            io:format("~ts~n", [br_mcp_tools:render(Name, Result)]),
            halt(0);
        {error, Error} ->
            io:format(standard_error, "~ts~n", [br_format:error_text(Error)]),
            halt(1)
    end.

demo() ->
    ok = ensure_started(),
    Questions = br_samples:questions(),
    lists:foreach(
      fun(Q) ->
              io:format("~n~s~n? ~ts~n", [lists:duplicate(72, $=), Q]),
              case timer:tc(fun() -> br_nl:answer(Q) end) of
                  {Micros, {ok, #{answer := Answer, interpretation := How}}} ->
                      io:format("~ts~n[~ts, ~.1f ms]~n", [Answer, How, Micros / 1000]);
                  {_, {error, Error}} ->
                      io:format("!! ~ts~n", [br_format:error_text(Error)])
              end
      end, Questions),
    io:format("~n~p questions answered~n", [length(Questions)]),
    halt(0).

tools() ->
    lists:foreach(fun(#{name := Name, description := Description}) ->
                          io:format("~-20s ~ts~n", [Name, first_sentence(Description)])
                  end, br_mcp_tools:list()),
    halt(0).

info() ->
    ok = ensure_started(),
    {ok, Summary} = br_query:dataset_summary(#{}),
    io:format("~ts~n", [br_format:render(dataset_summary, Summary)]),
    halt(0).

usage() ->
    io:format(
      "brazilian soccer MCP server~n~n"
      "  br_soccer_mcp serve              MCP server on stdin/stdout (default)~n"
      "  br_soccer_mcp ask \"question\"     answer one question~n"
      "  br_soccer_mcp call TOOL 'JSON'   call one tool~n"
      "  br_soccer_mcp demo               answer every sample question~n"
      "  br_soccer_mcp tools              list the MCP tools~n"
      "  br_soccer_mcp info               show what is loaded~n~n"
      "The data directory is found automatically; override it with~n"
      "BR_SOCCER_DATA_DIR=/path/to/data/kaggle.~n", []),
    ok.

%%====================================================================

ensure_started() ->
    %% Check for the data before starting the tree, so that the usual
    %% mistake gets one clear line instead of a supervisor report.
    case br_loader:data_dir() of
        undefined ->
            io:format(standard_error,
                      "cannot find the data: expected data/kaggle with ~s and the other "
                      "CSV files.~nSet BR_SOCCER_DATA_DIR=/path/to/data/kaggle or run "
                      "from the repository root.~n",
                      [br_loader:source_file(brasileirao_matches)]),
            halt(1);
        _ ->
            case start() of
                ok -> ok;
                {error, Reason} ->
                    io:format(standard_error, "failed to load the data sets: ~p~n",
                              [Reason]),
                    halt(1)
            end
    end.

first_sentence(Description) ->
    case binary:split(Description, <<". ">>) of
        [First | _] -> First;
        [] -> Description
    end.
