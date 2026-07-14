%% @doc Team-name normalization.
%%
%% The datasets spell the same club many ways: "Palmeiras-SP",
%% "Palmeiras", "América - MG", "Nacional (URU)", "São Paulo" vs
%% "Sao Paulo", and BR-Football's full names ("Atletico Mineiro",
%% "EC Bahia"). `normalize/1' reduces a name to a canonical key for
%% matching; `display_name/1' keeps it human readable but drops the suffix.
%%
%% Stripping a trailing state code is right for unambiguous clubs
%% ("Palmeiras-SP" == "Palmeiras") but wrong for the three Atléticos and
%% two Américas, which only differ by that code. A small alias table
%% (see {@link bsmcp_aliases}) keeps those distinct and folds the
%% full-name spellings onto the same key.
-module(bsmcp_normalize).

-export([normalize/1, display_name/1, same_team/2]).

%% @doc Canonical matching key for a team name.
-spec normalize(binary()) -> binary().
normalize(Name) ->
    Base = base_form(Name),
    case bsmcp_aliases:lookup(Base) of
        {ok, Canon} ->
            Canon;
        error ->
            Stripped = strip_suffix_bin(Base),
            case bsmcp_aliases:lookup(Stripped) of
                {ok, Canon} -> Canon;
                error -> Stripped
            end
    end.

%% @doc Human-readable name with the state/country suffix removed but
%% accents and original casing preserved.
-spec display_name(binary()) -> binary().
display_name(Name) ->
    case has_state_suffix(normalize(Name)) of
        true -> trim(Name);
        false -> trim(strip_suffix(trim(Name)))
    end.

%% True when a canonical key keeps a "-XX" state code (an ambiguous club).
has_state_suffix(Norm) ->
    case strip_state(lists:reverse(unicode:characters_to_list(Norm))) of
        {true, _} -> true;
        false -> false
    end.

%% @doc True when two names refer to the same team.
-spec same_team(binary(), binary()) -> boolean().
same_team(A, B) ->
    normalize(A) =:= normalize(B).

%% --- internal ---------------------------------------------------------

%% Lowercase, accent-free, single-spaced, with " - XX" suffix separators
%% tightened to "-XX". Does NOT strip the suffix.
base_form(Name) ->
    Lower = string:lowercase(remove_accents(trim(Name))),
    Collapsed = collapse_spaces(unicode:characters_to_list(Lower)),
    tighten_hyphen(Collapsed).

collapse_spaces(S) -> collapse_spaces(S, []).
collapse_spaces([$\s, $\s | T], Acc) -> collapse_spaces([$\s | T], Acc);
collapse_spaces([C | T], Acc) -> collapse_spaces(T, [C | Acc]);
collapse_spaces([], Acc) -> lists:reverse(Acc).

%% Turn "america - mg" / "america- mg" / "america -mg" into "america-mg".
tighten_hyphen(S) ->
    tighten_hyphen(string:trim(S), []).
tighten_hyphen([$\s, $- | T], Acc) -> tighten_hyphen([$- | T], Acc);
tighten_hyphen([$-, $\s | T], Acc) -> tighten_hyphen([$- | T], Acc);
tighten_hyphen([C | T], Acc) -> tighten_hyphen(T, [C | Acc]);
tighten_hyphen([], Acc) -> unicode:characters_to_binary(lists:reverse(Acc)).

trim(Bin) ->
    unicode:characters_to_binary(string:trim(unicode:characters_to_list(Bin))).

strip_suffix_bin(Bin) ->
    trim(strip_suffix(Bin)).

%% Remove a trailing "(XXX)" parenthetical or a "-XX"/" - XX" state/country
%% suffix (2-3 ASCII letters).
strip_suffix(Bin) ->
    strip_suffix_list(unicode:characters_to_list(Bin)).

strip_suffix_list(S) ->
    S1 = string:trim(S, trailing),
    case strip_paren(S1) of
        {true, R} -> strip_suffix_list(R);
        false ->
            case strip_state(lists:reverse(S1)) of
                {true, R} -> strip_suffix_list(R);
                false -> unicode:characters_to_binary(S1)
            end
    end.

strip_paren(S) ->
    case lists:reverse(S) of
        [$) | Rev] ->
            case drop_until_open(Rev) of
                {true, Before} -> {true, string:trim(Before, trailing)};
                false -> false
            end;
        _ -> false
    end.

drop_until_open([$( | Rest]) -> {true, lists:reverse(Rest)};
drop_until_open([_ | Rest]) -> drop_until_open(Rest);
drop_until_open([]) -> false.

strip_state(Rev) ->
    case take_letters(Rev, 0, []) of
        {N, Rest} when N >= 2, N =< 3 ->
            Rest1 = drop_spaces(Rest),
            case Rest1 of
                [$- | Before] -> {true, lists:reverse(drop_spaces(Before))};
                _ -> false
            end;
        _ -> false
    end.

take_letters([C | Rest], N, Acc) when C >= $A, C =< $Z; C >= $a, C =< $z ->
    take_letters(Rest, N + 1, [C | Acc]);
take_letters(Rest, N, _Acc) ->
    {N, Rest}.

drop_spaces([$\s | Rest]) -> drop_spaces(Rest);
drop_spaces(L) -> L.

%% Decompose to NFD and drop combining diacritical marks (U+0300..U+036F).
remove_accents(Bin) ->
    Decomposed = unicode:characters_to_nfd_list(unicode:characters_to_list(Bin)),
    unicode:characters_to_binary([C || C <- Decomposed, not is_combining(C)]).

is_combining(C) -> C >= 16#300 andalso C =< 16#36F.
