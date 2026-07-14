-module(br_soccer_mcp_server).
-export([process_line/2, start/0, start/1]).

-define(DEFAULT_DATA_DIR, "data/kaggle").

%% Process a single JSON-RPC line, returns {ok, ResponseBin} | no_response.
process_line(Line, Data) ->
    try
        Req = jsx:decode(Line, [return_maps]),
        case maps:get(<<"id">>, Req, undefined) of
            undefined ->
                %% It's a notification — fire and forget
                _ = br_soccer_mcp_handler:handle(Req, Data),
                no_response;
            _Id ->
                {ok, Resp} = br_soccer_mcp_handler:handle(Req, Data),
                {ok, jsx:encode(Resp)}
        end
    catch
        _:_ ->
            ErrResp = #{
                <<"jsonrpc">> => <<"2.0">>,
                <<"id">>      => null,
                <<"error">>   => #{<<"code">> => -32700,
                                   <<"message">> => <<"Parse error">>}
            },
            {ok, jsx:encode(ErrResp)}
    end.

%% Start the MCP server, loading data from the default directory.
start() ->
    start(?DEFAULT_DATA_DIR).

%% Start the MCP server with a custom data directory.
start(DataDir) ->
    io:setopts(standard_io, [binary]),
    io:format(standard_error, "Loading data from ~s...~n", [DataDir]),
    Data = br_soccer_data:load_all(DataDir),
    io:format(standard_error, "Data loaded. MCP server ready.~n", []),
    loop(Data).

loop(Data) ->
    case io:get_line("") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            Trimmed = trim_line(Line),
            case byte_size(Trimmed) of
                0 -> loop(Data);
                _ ->
                    case process_line(Trimmed, Data) of
                        no_response -> ok;
                        {ok, Resp}  ->
                            io:put_chars(standard_io, [Resp, <<"\n">>])
                    end,
                    loop(Data)
            end
    end.

trim_line(B) when is_binary(B) ->
    trim_right(trim_right(B, $\n), $\r);
trim_line(L) when is_list(L) ->
    trim_line(list_to_binary(L)).

trim_right(<<>>, _C) -> <<>>;
trim_right(B, C) ->
    Sz = byte_size(B) - 1,
    case B of
        <<Rest:Sz/binary, C>> -> trim_right(Rest, C);
        _ -> B
    end.
