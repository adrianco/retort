%%%-------------------------------------------------------------------
%%% @doc Multi-format date/time parsing.
%%%
%%% The data sets carry three different conventions:
%%% <ul>
%%%   <li>ISO dates: `2023-09-24'</li>
%%%   <li>ISO date + time: `2012-05-19 18:30:00'</li>
%%%   <li>Brazilian dates: `29/03/2003'</li>
%%% </ul>
%%% @end
%%%-------------------------------------------------------------------
-module(br_date).

-export([parse/1,
         parse_date/1,
         parse_time/1,
         format/1,
         format_datetime/2,
         to_days/1,
         in_range/3,
         year/1]).

-type date() :: calendar:date().
-type time() :: calendar:time().

%%--------------------------------------------------------------------
%% @doc Parse a date, optionally followed by a time.
-spec parse(term()) -> {ok, date(), time() | undefined} | error.
%% Fast path for the two shapes that make up virtually all of the data:
%% "2012-05-19 18:30:00" and "2023-09-24".
parse(<<Y:4/binary, $-, M:2/binary, $-, D:2/binary, Sep, Rest/binary>>)
  when Sep =:= $\s; Sep =:= $T ->
    case build_date(int(Y), int(M), int(D)) of
        {ok, Date} -> {ok, Date, parse_time_opt(Rest)};
        error -> error
    end;
parse(<<Y:4/binary, $-, M:2/binary, $-, D:2/binary>>) ->
    case build_date(int(Y), int(M), int(D)) of
        {ok, Date} -> {ok, Date, undefined};
        error -> error
    end;
parse(X) ->
    case br_text:trim(br_text:to_binary(X)) of
        <<>> -> error;
        Bin ->
            {DatePart, TimePart} =
                case binary:split(Bin, [<<" ">>, <<"T">>]) of
                    [D, T] -> {D, T};
                    [D] -> {D, <<>>}
                end,
            case parse_date(DatePart) of
                {ok, Date} -> {ok, Date, parse_time_opt(TimePart)};
                error -> error
            end
    end.

%%--------------------------------------------------------------------
%% @doc Parse `YYYY-MM-DD', `DD/MM/YYYY', `YYYY/MM/DD' or `DD-MM-YYYY'.
-spec parse_date(term()) -> {ok, date()} | error.
parse_date(<<Y:4/binary, $-, M:2/binary, $-, D:2/binary>>) ->
    build_date(int(Y), int(M), int(D));
parse_date(<<D:2/binary, $/, M:2/binary, $/, Y:4/binary>>) ->
    build_date(int(Y), int(M), int(D));
parse_date(X) ->
    Bin = br_text:trim(br_text:to_binary(X)),
    Parts = binary:split(Bin, [<<"-">>, <<"/">>, <<".">>], [global]),
    case [to_int(P) || P <- Parts] of
        [{ok, A}, {ok, B}, {ok, C}] -> build_date(A, B, C);
        _ -> error
    end.

%%--------------------------------------------------------------------
%% @doc Parse `HH:MM' or `HH:MM:SS'.
-spec parse_time(term()) -> {ok, time()} | error.
parse_time(<<H:2/binary, $:, M:2/binary, $:, S:2/binary>>) ->
    build_time(int(H), int(M), int(S));
parse_time(<<H:2/binary, $:, M:2/binary>>) ->
    build_time(int(H), int(M), 0);
parse_time(X) ->
    Bin = br_text:trim(br_text:to_binary(X)),
    case [to_int(P) || P <- binary:split(Bin, <<":">>, [global])] of
        [{ok, H}, {ok, M}] -> build_time(H, M, 0);
        [{ok, H}, {ok, M}, {ok, S}] -> build_time(H, M, S);
        _ -> error
    end.

build_time(H, M, S) when H >= 0, H < 24, M >= 0, M < 60, S >= 0, S < 61 -> {ok, {H, M, S}};
build_time(_, _, _) -> error.

%%--------------------------------------------------------------------
%% @doc ISO-8601 rendering of a date (`undefined' becomes `"unknown"').
-spec format(date() | undefined) -> binary().
format(undefined) -> <<"unknown">>;
format({Y, M, D}) ->
    iolist_to_binary(io_lib:format("~4..0b-~2..0b-~2..0b", [Y, M, D])).

%%--------------------------------------------------------------------
%% @doc ISO-8601 rendering of a date and optional time.
-spec format_datetime(date() | undefined, time() | undefined) -> binary().
format_datetime(Date, undefined) -> format(Date);
format_datetime(Date, {H, M, S}) ->
    <<(format(Date))/binary,
      (iolist_to_binary(io_lib:format(" ~2..0b:~2..0b:~2..0b", [H, M, S])))/binary>>.

%%--------------------------------------------------------------------
%% @doc Sortable integer for a date; `undefined' sorts first.
-spec to_days(date() | undefined) -> integer().
to_days(undefined) -> 0;
to_days(Date) -> calendar:date_to_gregorian_days(Date).

%%--------------------------------------------------------------------
%% @doc Inclusive range test; `undefined' bounds are open.
-spec in_range(date() | undefined, date() | undefined, date() | undefined) -> boolean().
in_range(undefined, _, _) -> false;
in_range(Date, From, To) ->
    D = to_days(Date),
    (From =:= undefined orelse D >= to_days(From))
        andalso (To =:= undefined orelse D =< to_days(To)).

%%--------------------------------------------------------------------
-spec year(date() | undefined) -> integer() | undefined.
year(undefined) -> undefined;
year({Y, _, _}) -> Y.

%%====================================================================
%% Internal
%%====================================================================

parse_time_opt(<<>>) -> undefined;
parse_time_opt(Bin) ->
    case parse_time(Bin) of
        {ok, T} -> T;
        error -> undefined
    end.

%% Disambiguate by field width: a 4 digit leading field is a year.
build_date(A, B, C) when A > 31 -> valid(A, B, C);
build_date(A, B, C) when C > 31 -> valid(C, B, A);
build_date(_, _, _) -> error.

valid(Y, M, D) when Y >= 1800, Y =< 2200, M >= 1, M =< 12, D >= 1, D =< 31 ->
    case calendar:valid_date(Y, M, D) of
        true -> {ok, {Y, M, D}};
        false -> error
    end;
valid(_, _, _) -> error.

to_int(Bin) ->
    try binary_to_integer(br_text:trim(Bin)) of
        I -> {ok, I}
    catch
        error:badarg -> error
    end.

%% Digits-only conversion for the fixed width fast paths; -1 means "not
%% a number", which every guard below rejects.
int(Bin) ->
    try binary_to_integer(Bin)
    catch error:badarg -> -1
    end.
