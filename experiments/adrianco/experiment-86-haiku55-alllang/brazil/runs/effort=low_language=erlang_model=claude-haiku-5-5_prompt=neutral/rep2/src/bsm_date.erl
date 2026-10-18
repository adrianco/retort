%% @doc Date normalisation. Accepts ISO "YYYY-MM-DD[ HH:MM:SS]" and Brazilian
%% "DD/MM/YYYY"; always returns ISO "YYYY-MM-DD" so dates compare as strings.
-module(bsm_date).
-export([parse/1]).

-spec parse(binary()) -> {ok, binary()} | error.
parse(Bin) ->
    case bsm_text:trim(Bin) of
        <<Y:4/binary, $-, M:2/binary, $-, D:2/binary, _/binary>> -> valid(Y, M, D);
        <<D:2/binary, $/, M:2/binary, $/, Y:4/binary>> -> valid(Y, M, D);
        _ -> error
    end.

valid(Y, M, D) ->
    case {to_int(Y), to_int(M), to_int(D)} of
        {Yi, Mi, Di} when is_integer(Yi), is_integer(Mi), is_integer(Di),
                          Mi >= 1, Mi =< 12, Di >= 1, Di =< 31 ->
            {ok, <<Y/binary, $-, M/binary, $-, D/binary>>};
        _ ->
            error
    end.

to_int(B) ->
    try binary_to_integer(B)
    catch error:badarg -> undefined
    end.
