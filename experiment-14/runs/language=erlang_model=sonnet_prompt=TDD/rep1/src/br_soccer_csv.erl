-module(br_soccer_csv).
-export([parse_line/1, parse_string/1, normalize_team/1, parse_date/1]).

%% Parse a single CSV line, handling quoted fields.
parse_line(Line) ->
    parse_fields(Line, [], <<>>).

parse_fields(<<>>, Fields, Current) ->
    lists:reverse([Current | Fields]);
parse_fields(<<$,, Rest/binary>>, Fields, Current) ->
    parse_fields(Rest, [Current | Fields], <<>>);
parse_fields(<<$", Rest/binary>>, Fields, <<>>) ->
    parse_quoted(Rest, Fields, <<>>);
parse_fields(<<C, Rest/binary>>, Fields, Current) ->
    parse_fields(Rest, Fields, <<Current/binary, C>>).

parse_quoted(<<$", $,, Rest/binary>>, Fields, Current) ->
    parse_fields(Rest, [Current | Fields], <<>>);
parse_quoted(<<$", $", Rest/binary>>, Fields, Current) ->
    parse_quoted(Rest, Fields, <<Current/binary, $">>);
parse_quoted(<<$">>, Fields, Current) ->
    lists:reverse([Current | Fields]);
parse_quoted(<<C, Rest/binary>>, Fields, Current) ->
    parse_quoted(Rest, Fields, <<Current/binary, C>>);
parse_quoted(<<>>, Fields, Current) ->
    lists:reverse([Current | Fields]).

%% Parse a CSV string with header row into list of maps.
parse_string(Csv) ->
    Lines = binary:split(Csv, <<"\n">>, [global]),
    NonEmpty = [L || L <- Lines, begin T = trim_line(L), byte_size(T) > 0 end],
    case NonEmpty of
        [] -> [];
        [Header | Rows] ->
            Headers = parse_line(trim_line(Header)),
            [row_to_map(Headers, parse_line(trim_line(R))) || R <- Rows]
    end.

%% Fast binary line trimmer (strips \r and trailing spaces).
trim_line(B) ->
    trim_right(trim_right(B, $\r), $\s).

trim_right(<<>>, _C) -> <<>>;
trim_right(B, C) ->
    Sz = byte_size(B) - 1,
    case B of
        <<Rest:Sz/binary, C>> -> trim_right(Rest, C);
        _ -> B
    end.

row_to_map(Headers, Values) ->
    Pairs = lists:zip(Headers, pad_values(Values, length(Headers))),
    maps:from_list(Pairs).

pad_values(Values, Len) when length(Values) >= Len -> lists:sublist(Values, Len);
pad_values(Values, Len) -> Values ++ lists:duplicate(Len - length(Values), <<>>).

%% Normalize team name: strip state suffix like "-SP", "-RJ", etc.
normalize_team(Team) ->
    case re:run(Team, <<"^(.*)-[A-Z]{2}$">>, [{capture, [1], binary}]) of
        {match, [Base]} -> Base;
        nomatch -> Team
    end.

%% Parse date from multiple formats.
parse_date(DateBin) ->
    Str = binary_to_list(DateBin),
    try_formats(Str, [
        fun parse_iso_date/1,
        fun parse_iso_datetime/1,
        fun parse_br_date/1
    ]).

try_formats(_Str, []) -> undefined;
try_formats(Str, [F | Rest]) ->
    case F(Str) of
        {ok, Date} -> Date;
        error -> try_formats(Str, Rest)
    end.

parse_iso_date(Str) ->
    case io_lib:fread("~4d-~2d-~2d", Str) of
        {ok, [Y, M, D], _} -> {ok, {Y, M, D}};
        _ -> error
    end.

parse_iso_datetime(Str) ->
    case io_lib:fread("~4d-~2d-~2d ~2d:~2d:~2d", Str) of
        {ok, [Y, M, D | _], _} -> {ok, {Y, M, D}};
        _ -> error
    end.

parse_br_date(Str) ->
    case io_lib:fread("~2d/~2d/~4d", Str) of
        {ok, [D, M, Y], _} -> {ok, {Y, M, D}};
        _ -> error
    end.
