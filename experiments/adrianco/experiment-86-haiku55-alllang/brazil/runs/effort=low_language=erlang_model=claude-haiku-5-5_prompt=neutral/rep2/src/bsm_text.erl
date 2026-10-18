%% @doc Text helpers: accent/case folding, trimming and lenient integer parsing.
-module(bsm_text).
-export([fold/1, trim/1, contains/2, parse_int/1]).

%% @doc Lower-case, strip diacritics and collapse whitespace.
%% "São Paulo", "Sao Paulo" and "SAO  PAULO" all fold to <<"sao paulo">>.
-spec fold(binary()) -> binary().
fold(Bin) ->
    Plain = [C || C <- unicode:characters_to_nfd_list(unicode:characters_to_list(Bin)),
                  not is_combining(C)],
    Lower = unicode:characters_to_binary(string:lowercase(Plain)),
    re:replace(trim(Lower), <<"\\s+">>, <<" ">>, [global, {return, binary}]).

-spec trim(binary()) -> binary().
trim(Bin) ->
    unicode:characters_to_binary(string:trim(Bin)).

%% @doc Case- and accent-insensitive substring test. An empty needle matches.
-spec contains(binary(), binary()) -> boolean().
contains(Haystack, Needle) ->
    case fold(Needle) of
        <<>> -> true;
        N -> binary:match(fold(Haystack), N) =/= nomatch
    end.

%% @doc Parse "12", "1.0" (football feeds use floats for goals) or
%% return undefined for anything else.
-spec parse_int(binary()) -> integer() | undefined.
parse_int(Bin) ->
    T = trim(Bin),
    try binary_to_integer(T)
    catch error:badarg ->
        try trunc(binary_to_float(T))
        catch error:badarg -> undefined
        end
    end.

is_combining(C) -> C >= 16#0300 andalso C =< 16#036F.
