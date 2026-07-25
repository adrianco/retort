%%%-------------------------------------------------------------------
%%% @doc UTF-8 aware text helpers.
%%%
%%% The Kaggle data sets are Brazilian Portuguese and mix accented and
%%% unaccented spellings of the same name ("Grêmio"/"Gremio", "São
%%% Paulo"/"Sao Paulo").  Every lookup in this application therefore
%%% goes through {@link normalize/1}, which folds accents, lowercases
%%% and reduces punctuation to single spaces so that all spellings of a
%%% name collapse onto one comparable key.
%%% @end
%%%-------------------------------------------------------------------
-module(br_text).

-export([to_binary/1,
         trim/1,
         normalize/1,
         slug/1,
         fold_accents/1,
         contains/2,
         tokens/1,
         join/2,
         titlecase/1]).

%%--------------------------------------------------------------------
%% @doc Coerce the usual scalar types to a UTF-8 binary.
-spec to_binary(term()) -> binary().
to_binary(B) when is_binary(B) -> B;
to_binary(L) when is_list(L) -> unicode:characters_to_binary(L);
to_binary(A) when is_atom(A) -> atom_to_binary(A, utf8);
to_binary(I) when is_integer(I) -> integer_to_binary(I);
to_binary(F) when is_float(F) -> float_to_binary(F, [{decimals, 2}, compact]).

%%--------------------------------------------------------------------
%% @doc Strip ASCII whitespace from both ends of a binary.
%%
%% `string:trim/1' is Unicode aware and therefore comparatively slow;
%% this is called once per CSV field (about two million times during a
%% full load), so the cheap version is worth having.
-spec trim(binary()) -> binary().
trim(Bin) -> trim_trailing(trim_leading(Bin)).

trim_leading(<<C, Rest/binary>>) when C =:= $\s; C =:= $\t; C =:= $\r; C =:= $\n ->
    trim_leading(Rest);
trim_leading(Bin) -> Bin.

trim_trailing(<<>>) -> <<>>;
trim_trailing(Bin) ->
    case binary:at(Bin, byte_size(Bin) - 1) of
        C when C =:= $\s; C =:= $\t; C =:= $\r; C =:= $\n ->
            trim_trailing(binary:part(Bin, 0, byte_size(Bin) - 1));
        _ -> Bin
    end.

%%--------------------------------------------------------------------
%% @doc Lowercase, accent-folded, punctuation-free comparison key.
%%
%% ```
%% <<"são paulo">>  -> <<"sao paulo">>
%% <<"América - MG">> -> <<"america mg">>
%% '''
-spec normalize(term()) -> binary().
normalize(X) ->
    Chars = unicode:characters_to_list(to_binary(X)),
    Lower = string:lowercase(Chars),
    Folded = lists:flatmap(fun fold_char/1, Lower),
    unicode:characters_to_binary(collapse(Folded, [], skip)).

%%--------------------------------------------------------------------
%% @doc Like {@link normalize/1} but with `-' instead of spaces; used
%% for identifiers of graph nodes.
-spec slug(term()) -> binary().
slug(X) ->
    binary:replace(normalize(X), <<" ">>, <<"-">>, [global]).

%%--------------------------------------------------------------------
%% @doc Remove diacritics but keep case and punctuation.
-spec fold_accents(term()) -> binary().
fold_accents(X) ->
    Chars = unicode:characters_to_list(to_binary(X)),
    unicode:characters_to_binary(lists:flatmap(fun fold_keep_case/1, Chars)).

%%--------------------------------------------------------------------
%% @doc Accent/case insensitive substring test.
-spec contains(term(), term()) -> boolean().
contains(Haystack, Needle) ->
    H = normalize(Haystack),
    case normalize(Needle) of
        <<>> -> true;
        N -> binary:match(H, N) =/= nomatch
    end.

%%--------------------------------------------------------------------
%% @doc Whitespace separated tokens of the normalised form.
-spec tokens(term()) -> [binary()].
tokens(X) ->
    case normalize(X) of
        <<>> -> [];
        N -> binary:split(N, <<" ">>, [global])
    end.

%%--------------------------------------------------------------------
%% @doc Join binaries with a separator.
-spec join([binary()], binary()) -> binary().
join([], _Sep) -> <<>>;
join([H | T], Sep) ->
    iolist_to_binary([H | [[Sep, X] || X <- T]]).

%%--------------------------------------------------------------------
%% @doc Capitalise each word ("ponte preta" -> "Ponte Preta").
-spec titlecase(term()) -> binary().
titlecase(X) ->
    Words = [W || W <- binary:split(to_binary(X), <<" ">>, [global]), W =/= <<>>],
    join([string:titlecase(W) || W <- Words], <<" ">>).

%%====================================================================
%% Internal
%%====================================================================

%% Collapse everything that is not [a-z0-9] into single spaces and trim.
%% State is `skip' while leading/duplicate separators are being dropped.
collapse([], Acc, _) -> lists:reverse(Acc);
collapse([C | T], Acc, State) ->
    case is_word_char(C) of
        true when State =:= pending -> collapse(T, [C, $\s | Acc], keep);
        true -> collapse(T, [C | Acc], keep);
        false when State =:= keep -> collapse(T, Acc, pending);
        false -> collapse(T, Acc, State)
    end.

is_word_char(C) when C >= $a, C =< $z -> true;
is_word_char(C) when C >= $0, C =< $9 -> true;
is_word_char(C) when C > 127 -> true;   % keep unmapped non-latin letters
is_word_char(_) -> false.

%% Fold a lowercased codepoint to its ASCII skeleton.  Combining marks
%% (U+0300..U+036F) are dropped so that decomposed input works too.
fold_char(C) when C >= $a, C =< $z -> [C];
fold_char(C) when C >= $0, C =< $9 -> [C];
fold_char(C) when C < 128 -> [C];
fold_char(C) when C >= 16#300, C =< 16#36F -> [];
fold_char(C) ->
    case latin_fold(C) of
        skip -> [C];
        Repl -> Repl
    end.

fold_keep_case(C) when C < 128 -> [C];
fold_keep_case(C) when C >= 16#300, C =< 16#36F -> [];
fold_keep_case(C) ->
    Lower = string:lowercase([C]),
    case Lower of
        [L] when L =/= C ->
            case latin_fold(L) of
                skip -> [C];
                Repl -> string:uppercase(Repl)
            end;
        _ ->
            case latin_fold(C) of
                skip -> [C];
                Repl -> Repl
            end
    end.

latin_fold(C) when C >= 16#E0, C =< 16#E5 -> "a";   % à á â ã ä å
latin_fold(16#E6) -> "ae";
latin_fold(16#E7) -> "c";                            % ç
latin_fold(C) when C >= 16#E8, C =< 16#EB -> "e";   % è é ê ë
latin_fold(C) when C >= 16#EC, C =< 16#EF -> "i";   % ì í î ï
latin_fold(16#F0) -> "d";
latin_fold(16#F1) -> "n";                            % ñ
latin_fold(C) when C >= 16#F2, C =< 16#F6 -> "o";   % ò ó ô õ ö
latin_fold(16#F8) -> "o";
latin_fold(C) when C >= 16#F9, C =< 16#FC -> "u";   % ù ú û ü
latin_fold(16#FD) -> "y";
latin_fold(16#FF) -> "y";
latin_fold(16#DF) -> "ss";
latin_fold(C) when C >= 16#100, C =< 16#105 -> "a";
latin_fold(C) when C >= 16#106, C =< 16#10D -> "c";
latin_fold(C) when C >= 16#10E, C =< 16#111 -> "d";
latin_fold(C) when C >= 16#112, C =< 16#11B -> "e";
latin_fold(C) when C >= 16#11C, C =< 16#123 -> "g";
latin_fold(C) when C >= 16#124, C =< 16#127 -> "h";
latin_fold(C) when C >= 16#128, C =< 16#131 -> "i";
latin_fold(C) when C >= 16#139, C =< 16#142 -> "l";
latin_fold(C) when C >= 16#143, C =< 16#14B -> "n";
latin_fold(C) when C >= 16#14C, C =< 16#151 -> "o";
latin_fold(C) when C >= 16#154, C =< 16#159 -> "r";
latin_fold(C) when C >= 16#15A, C =< 16#161 -> "s";
latin_fold(C) when C >= 16#162, C =< 16#167 -> "t";
latin_fold(C) when C >= 16#168, C =< 16#173 -> "u";
latin_fold(C) when C >= 16#174, C =< 16#177 -> "y";
latin_fold(C) when C >= 16#179, C =< 16#17E -> "z";
latin_fold(_) -> skip.
