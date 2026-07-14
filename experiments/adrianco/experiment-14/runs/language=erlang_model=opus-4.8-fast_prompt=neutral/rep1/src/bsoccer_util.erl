%%% =====================================================================
%%% bsoccer_util — normalisation helpers shared across the data layer.
%%%
%%% The datasets are messy in exactly the ways the specification calls out:
%%%   * team names carry state/country suffixes ("Palmeiras-SP",
%%%     "Nacional (URU)", "América - MG") and accents ("Grêmio", "São Paulo");
%%%   * dates appear as ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00")
%%%     and Brazilian ("29/03/2003");
%%%   * goal counts appear as ints, quoted strings and floats ("2.0").
%%%
%%% This module turns all of that into a canonical form so matching and
%%% aggregation behave consistently. Two notions of a team name exist:
%%%   * display name — cleaned of suffixes but with accents/case intact;
%%%   * key          — accent-folded, lower-cased, punctuation-stripped, used
%%%                    for equality and substring matching (and run through a
%%%                    small alias table to merge well-known spelling variants).
%%% =====================================================================
-module(bsoccer_util).

-export([clean_team/1, team_key/1, fold_accents/1, norm_key/1,
         parse_date/1, parse_goal/1, parse_int/1, to_binary/1, trim/1]).

%% --- team names -----------------------------------------------------------

%% Strip trailing state/country markers and surrounding whitespace, returning
%% a human-friendly display name (accents and internal casing preserved).
-spec clean_team(binary() | string()) -> binary().
clean_team(Name0) ->
    Name = trim(to_binary(Name0)),
    strip_suffix(Name).

%% Repeatedly remove trailing "(XXX)" / " - XX" / "-XX" country/state codes.
%% Implemented with binary operations (not regex) so it stays cheap when run
%% across tens of thousands of rows at load time.
strip_suffix(Name) ->
    case strip_once(Name) of
        Name -> Name;                    %% no progress, stop
        <<>> -> Name;
        Shorter -> strip_suffix(Shorter)
    end.

strip_once(Name) ->
    case strip_parens_code(Name) of
        {ok, Base} -> Base;
        no ->
            case strip_dash_code(Name) of
                {ok, Base} -> Base;
                no -> Name
            end
    end.

%% Strip a trailing "(XX)".."(XXXX)" all-uppercase country code.
strip_parens_code(Name) ->
    Size = byte_size(Name),
    case Size > 0 andalso binary:at(Name, Size - 1) =:= $) of
        true ->
            case last_pos(Name, <<"(">>) of
                none -> no;
                P ->
                    Inside = binary:part(Name, P + 1, Size - P - 2),
                    case is_upper_code(Inside, 2, 4) of
                        true -> {ok, trim(binary:part(Name, 0, P))};
                        false -> no
                    end
            end;
        false ->
            no
    end.

%% Strip a trailing "-XX" / " - XXX" all-uppercase state/country code.
strip_dash_code(Name) ->
    case last_pos(Name, <<"-">>) of
        none -> no;
        P ->
            After = trim(binary:part(Name, P + 1, byte_size(Name) - P - 1)),
            case is_upper_code(After, 2, 3) of
                true -> {ok, trim(binary:part(Name, 0, P))};
                false -> no
            end
    end.

last_pos(Bin, Pat) ->
    case binary:matches(Bin, Pat) of
        [] -> none;
        Matches -> element(1, lists:last(Matches))
    end.

is_upper_code(Bin, Min, Max) ->
    L = byte_size(Bin),
    L >= Min andalso L =< Max andalso all_upper(Bin).

all_upper(<<>>) -> true;
all_upper(<<C, Rest/binary>>) when C >= $A, C =< $Z -> all_upper(Rest);
all_upper(_) -> false.

%% Canonical match key for a team name: cleaned, accent-folded, lower-cased,
%% punctuation removed, whitespace collapsed, then alias-normalised.
-spec team_key(binary() | string()) -> binary().
team_key(Name) ->
    Clean = clean_team(Name),
    Key = norm_key(Clean),
    team_alias(Key).

%% Generic normalisation used for any free-text key (teams, clubs, names,
%% nationalities): fold accents, lower-case, drop punctuation, collapse spaces.
-spec norm_key(binary() | string()) -> binary().
norm_key(Bin0) ->
    Chars = unicode:characters_to_list(to_binary(Bin0)),
    %% Single pass: accent-fold, lower-case, and map every non-alphanumeric
    %% character to a space. Then collapse whitespace runs and trim. The
    %% result is pure ASCII [a-z0-9 ], so list_to_binary is safe.
    Cleaned = [clean_char(fold_char(C)) || C <- Chars],
    Words = string:lexemes(Cleaned, " "),
    list_to_binary(lists:join(" ", Words)).

%% After accent folding a char is ASCII or an unmapped code point; keep
%% alphanumerics (lower-casing letters) and turn everything else into a space.
clean_char(C) when C >= $A, C =< $Z -> C + 32;
clean_char(C) when C >= $a, C =< $z -> C;
clean_char(C) when C >= $0, C =< $9 -> C;
clean_char(_) -> $\s.

%% A small alias table that merges spelling variants the substring matcher
%% cannot bridge on its own. Keys are already norm_key/1 normalised.
team_alias(<<"athletico paranaense">>) -> <<"atletico paranaense">>;
team_alias(<<"athletico pr">>) -> <<"atletico paranaense">>;
team_alias(<<"atletico pr">>) -> <<"atletico paranaense">>;
team_alias(<<"atletico mg">>) -> <<"atletico mineiro">>;
team_alias(<<"sao paulo fc">>) -> <<"sao paulo">>;
team_alias(<<"vasco da gama">>) -> <<"vasco">>;
team_alias(<<"red bull bragantino">>) -> <<"bragantino">>;
team_alias(<<"sport recife">>) -> <<"sport">>;
team_alias(Other) -> Other.

%% --- accent folding -------------------------------------------------------

%% Map common Latin-1/Portuguese accented code points down to plain ASCII.
%% Operates on the UTF-8 binary code point by code point.
-spec fold_accents(binary()) -> binary().
fold_accents(Bin) ->
    unicode:characters_to_binary([fold_char(C) || C <- unicode:characters_to_list(Bin)]).

fold_char(C) when C >= $A, C =< $Z -> C;
fold_char(C) when C >= $a, C =< $z -> C;
fold_char(C) when C >= $0, C =< $9 -> C;
fold_char(C) ->
    case C of
        $á -> $a; $à -> $a; $â -> $a; $ã -> $a; $ä -> $a; $å -> $a;
        $é -> $e; $è -> $e; $ê -> $e; $ë -> $e;
        $í -> $i; $ì -> $i; $î -> $i; $ï -> $i;
        $ó -> $o; $ò -> $o; $ô -> $o; $õ -> $o; $ö -> $o;
        $ú -> $u; $ù -> $u; $û -> $u; $ü -> $u;
        $ç -> $c; $ñ -> $n; $ý -> $y;
        $Á -> $A; $À -> $A; $Â -> $A; $Ã -> $A; $Ä -> $A;
        $É -> $E; $È -> $E; $Ê -> $E; $Ë -> $E;
        $Í -> $I; $Ì -> $I; $Î -> $I; $Ï -> $I;
        $Ó -> $O; $Ò -> $O; $Ô -> $O; $Õ -> $O; $Ö -> $O;
        $Ú -> $U; $Ù -> $U; $Û -> $U; $Ü -> $U;
        $Ç -> $C; $Ñ -> $N;
        _ -> C
    end.

%% --- dates ----------------------------------------------------------------

%% Parse the various date encodings into {{Y,M,D}, IsoBinary}. Returns
%% `undefined` when the input cannot be interpreted.
-spec parse_date(binary() | string()) ->
          {calendar:date(), binary()} | undefined.
parse_date(Raw0) ->
    Raw = trim(to_binary(Raw0)),
    %% Drop any trailing time component.
    DatePart = case binary:split(Raw, <<" ">>) of
                   [D | _] -> D;
                   [] -> Raw
               end,
    case binary:split(DatePart, <<"-">>, [global]) of
        [Yr, Mo, Dy] ->
            %% ISO: YYYY-MM-DD
            mk_date(parse_int(Yr), parse_int(Mo), parse_int(Dy));
        _ ->
            case binary:split(DatePart, <<"/">>, [global]) of
                [Dy, Mo, Yr] ->
                    %% Brazilian: DD/MM/YYYY
                    mk_date(parse_int(Yr), parse_int(Mo), parse_int(Dy));
                _ ->
                    undefined
            end
    end.

mk_date(Y, M, D) when is_integer(Y), is_integer(M), is_integer(D),
                      M >= 1, M =< 12, D >= 1, D =< 31, Y > 0 ->
    Iso = iolist_to_binary(io_lib:format("~4..0w-~2..0w-~2..0w", [Y, M, D])),
    {{Y, M, D}, Iso};
mk_date(_, _, _) ->
    undefined.

%% --- numbers --------------------------------------------------------------

%% Parse a goal/score cell that may be "2", "2.0", or quoted. Returns the
%% integer value or `undefined` on missing/garbage data.
-spec parse_goal(binary() | string()) -> integer() | undefined.
parse_goal(V) -> parse_int(V).

%% Lenient integer parse: accepts ints and integer-valued floats, ignoring
%% surrounding whitespace; returns `undefined` otherwise.
-spec parse_int(binary() | string()) -> integer() | undefined.
parse_int(V0) ->
    V = trim(to_binary(V0)),
    case V of
        <<>> -> undefined;
        _ ->
            S = binary_to_list(V),
            case string:to_integer(S) of
                {Int, ""} -> Int;
                {Int, "." ++ Rest} ->
                    %% Float form like "2.0"; accept when the fraction is zero.
                    case lists:all(fun(C) -> C =:= $0 end, Rest) of
                        true -> Int;
                        false -> round_float(S)
                    end;
                _ -> undefined
            end
    end.

round_float(S) ->
    case string:to_float(S) of
        {F, _} when is_float(F) -> round(F);
        _ -> undefined
    end.

%% --- generic helpers ------------------------------------------------------

-spec to_binary(binary() | string() | atom() | integer()) -> binary().
to_binary(B) when is_binary(B) -> B;
to_binary(L) when is_list(L) -> unicode:characters_to_binary(L);
to_binary(A) when is_atom(A) -> atom_to_binary(A, utf8);
to_binary(I) when is_integer(I) -> integer_to_binary(I).

%% Fast ASCII-whitespace trim. string:trim/1 is surprisingly expensive per
%% call (it runs the full Unicode grapheme machinery), which dominates load
%% time when applied to tens of thousands of fields — so we trim spaces, tabs
%% and CR/LF directly and return the input unchanged (no allocation) when, as
%% is almost always the case, there is nothing to strip.
-spec trim(binary()) -> binary().
trim(<<>>) -> <<>>;
trim(B) ->
    S = byte_size(B),
    case is_ws(binary:at(B, 0)) orelse is_ws(binary:at(B, S - 1)) of
        false -> B;
        true -> trim_trailing(trim_leading(B))
    end.

trim_leading(<<C, Rest/binary>>) when C =:= $\s; C =:= $\t; C =:= $\r; C =:= $\n ->
    trim_leading(Rest);
trim_leading(B) -> B.

trim_trailing(B) ->
    S = byte_size(B),
    case S > 0 andalso is_ws(binary:at(B, S - 1)) of
        true -> trim_trailing(binary:part(B, 0, S - 1));
        false -> B
    end.

is_ws($\s) -> true;
is_ws($\t) -> true;
is_ws($\r) -> true;
is_ws($\n) -> true;
is_ws(_) -> false.
