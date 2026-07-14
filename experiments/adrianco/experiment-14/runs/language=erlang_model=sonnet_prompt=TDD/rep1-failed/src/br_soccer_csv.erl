-module(br_soccer_csv).
-export([parse_line/1, strip_bom/1, normalize_team/1, parse_date/1, parse_int/1, parse_float/1,
         read_csv/1]).

%% Parse a CSV line into a list of string fields, handling quoted fields.
parse_line(Line) ->
    parse_fields(Line, []).

parse_fields([], Acc) ->
    lists:reverse(Acc);
parse_fields(Line, Acc) ->
    {Field, Rest} = parse_field(Line),
    case Rest of
        [] -> lists:reverse([Field | Acc]);
        [$, | Tail] -> parse_fields(Tail, [Field | Acc])
    end.

parse_field([$" | Rest]) ->
    parse_quoted_field(Rest, []);
parse_field(Line) ->
    parse_unquoted_field(Line, []).

parse_quoted_field([], Acc) ->
    {lists:reverse(Acc), []};
parse_quoted_field([$" | Rest], Acc) ->
    {lists:reverse(Acc), Rest};
parse_quoted_field([C | Rest], Acc) ->
    parse_quoted_field(Rest, [C | Acc]).

parse_unquoted_field([], Acc) ->
    {lists:reverse(Acc), []};
parse_unquoted_field([$, | _] = Rest, Acc) ->
    {lists:reverse(Acc), Rest};
parse_unquoted_field([C | Rest], Acc) ->
    parse_unquoted_field(Rest, [C | Acc]).

%% Strip UTF-8 BOM (EF BB BF) from the start of a string.
strip_bom([16#EF, 16#BB, 16#BF | Rest]) -> Rest;
strip_bom(S) -> S.

%% Remove state suffix like "-SP", "-RJ", " - RJ" from team names.
normalize_team(Name) ->
    %% Handle " - XX" pattern (with spaces) first
    case re:run(Name, "^(.*?)\\s+-\\s+[A-Z]{2}$", [{capture, all_but_first, list}]) of
        {match, [Base]} -> Base;
        nomatch ->
            %% Handle "-XX" pattern at end (two uppercase letters)
            case re:run(Name, "^(.*?)-[A-Z]{2}$", [{capture, all_but_first, list}]) of
                {match, [Base]} -> Base;
                nomatch -> Name
            end
    end.

%% Parse various date formats into {Year, Month, Day}.
parse_date(S) ->
    S2 = string:trim(S),
    case re:run(S2, "^(\\d{4})-(\\d{2})-(\\d{2})", [{capture, all_but_first, list}]) of
        {match, [Y, M, D]} ->
            {list_to_integer(Y), list_to_integer(M), list_to_integer(D)};
        nomatch ->
            case re:run(S2, "^(\\d{2})/(\\d{2})/(\\d{4})$", [{capture, all_but_first, list}]) of
                {match, [D, M, Y]} ->
                    {list_to_integer(Y), list_to_integer(M), list_to_integer(D)};
                nomatch ->
                    {0, 0, 0}
            end
    end.

%% Parse an integer string, returning 0 for empty/invalid.
parse_int("") -> 0;
parse_int(S) ->
    try list_to_integer(string:trim(S))
    catch _:_ -> 0
    end.

%% Parse a float string, returning 0.0 for empty/invalid.
parse_float("") -> 0.0;
parse_float(S) ->
    S2 = string:trim(S),
    try
        case string:find(S2, ".") of
            nomatch -> float(list_to_integer(S2));
            _ -> list_to_float(S2)
        end
    catch _:_ -> 0.0
    end.

%% Read a CSV file and return list of maps (header -> value).
read_csv(Filename) ->
    {ok, Bin} = file:read_file(Filename),
    Content = strip_bom(binary_to_list(Bin)),
    Lines = string:split(Content, "\n", all),
    NonEmpty = [L || L <- Lines, string:trim(L) =/= ""],
    case NonEmpty of
        [] -> [];
        [Header | Rows] ->
            Keys = parse_line(Header),
            [begin
                 Vals = parse_line(Row),
                 PaddedVals = pad_or_trim(Vals, length(Keys)),
                 maps:from_list(lists:zip(Keys, PaddedVals))
             end || Row <- Rows]
    end.

pad_or_trim(Vals, Len) when length(Vals) >= Len ->
    lists:sublist(Vals, Len);
pad_or_trim(Vals, Len) ->
    Vals ++ lists:duplicate(Len - length(Vals), "").
