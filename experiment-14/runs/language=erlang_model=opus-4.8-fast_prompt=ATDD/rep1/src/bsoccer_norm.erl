%%% ===================================================================
%%% Brazilian Soccer MCP Server - text & name normalisation
%%%
%%% Context: The datasets spell the same club in many ways:
%%%   "Palmeiras-SP", "Palmeiras", "São Paulo", "Sao Paulo",
%%%   "Atlético - MG", "Nacional (URU)".
%%% To match a user's query ("Flamengo") against the stored spelling
%%% ("Flamengo-RJ") this module produces:
%%%   * fold/1     - an accent-folded, lower-cased comparison key for any
%%%                  free text (UTF-8 aware),
%%%   * base_key/1 - the same, with a trailing state/country suffix
%%%                  ("-SP", " - MG", "(URU)") removed, so "Flamengo"
%%%                  and "Flamengo-RJ" collapse to the same key while
%%%                  "Atletico-MG" and "Atletico-PR" stay distinct only
%%%                  by their suffix (see team_matches/2).
%%%   * team_matches/2 - whether a user query identifies a given team.
%%%
%%% Matching deliberately does NOT strip the suffix when comparing two
%%% full dataset names, so the three different "Atlético" clubs are kept
%%% apart in standings; the suffix is only stripped to let a bare query
%%% ("Flamengo") find the suffixed spelling.
%%% ===================================================================
-module(bsoccer_norm).

-export([fold/1, base_key/1, team_matches/2, contains_fold/2]).

%% Accent-fold + lowercase a UTF-8 binary into a comparison key.
-spec fold(binary() | string()) -> binary().
fold(Bin) when is_binary(Bin) ->
    Chars = unicode:characters_to_list(Bin, utf8),
    fold(Chars);
fold(Chars) when is_list(Chars) ->
    Folded = lists:map(fun fold_char/1, Chars),
    Lower = string:to_lower(lists:flatten(Folded)),
    unicode:characters_to_binary(string:trim(Lower), utf8).

%% Build a base key with any trailing state/country suffix removed.
-spec base_key(binary() | string()) -> binary().
base_key(Name) ->
    Folded = fold(Name),
    strip_suffix(Folded).

%% Does a user query identify a given team name?
%%
%% A bare query ("Flamengo") matches on the suffix-stripped base key, so
%% it finds "Flamengo-RJ". But a *state-qualified* query ("Atletico-MG")
%% keeps its suffix and must match the team's full folded name, so it
%% does NOT also match "Atletico-PR". This is how the three different
%% "Atlético" clubs are kept distinct when the caller is specific.
-spec team_matches(binary() | string(), binary() | string()) -> boolean().
team_matches(Query, TeamName) ->
    QFull = fold(Query),
    QBase = strip_suffix(QFull),
    case QBase of
        <<>> -> false;
        _ ->
            case QFull =:= QBase of
                true ->
                    %% bare query -> match on base key (with containment)
                    TBase = base_key(TeamName),
                    QBase =:= TBase orelse is_sub(QBase, TBase);
                false ->
                    %% qualified query -> require full-name equality
                    QFull =:= fold(TeamName)
            end
    end.

%% Case/accent-insensitive substring test for free-text fields
%% (player name, club, nationality, position, competition).
-spec contains_fold(binary() | string(), binary() | string()) -> boolean().
contains_fold(Haystack, Needle) ->
    H = fold(Haystack),
    N = fold(Needle),
    N =:= <<>> orelse is_sub(N, H).

%% --- internals -----------------------------------------------------

is_sub(Needle, Haystack) ->
    binary:match(Haystack, Needle) =/= nomatch.

%% Remove a trailing "(...)", " - XX", or "-XX" state/country suffix.
strip_suffix(Bin) ->
    S = unicode:characters_to_list(Bin, utf8),
    Stripped = strip_parens(strip_state(S)),
    unicode:characters_to_binary(string:trim(Stripped), utf8).

%% Drop a trailing parenthesised group, e.g. "nacional (uru)".
strip_parens(S) ->
    case re:run(S, "^(.*?)\\s*\\([^)]*\\)\\s*$",
                [unicode, {capture, all_but_first, list}]) of
        {match, [Base]} -> Base;
        nomatch -> S
    end.

%% Drop a trailing " - mg" / "-sp" style 2-4 letter suffix.
strip_state(S) ->
    case re:run(S, "^(.*?)\\s*-\\s*[a-z]{2,4}\\s*$",
                [unicode, {capture, all_but_first, list}]) of
        {match, [Base]} -> Base;
        nomatch -> S
    end.

%% Fold a single codepoint to its ASCII base (Portuguese diacritics).
fold_char(C) ->
    case C of
        $á -> $a; $à -> $a; $â -> $a; $ã -> $a; $ä -> $a; $å -> $a;
        $Á -> $A; $À -> $A; $Â -> $A; $Ã -> $A; $Ä -> $A;
        $é -> $e; $è -> $e; $ê -> $e; $ë -> $e;
        $É -> $E; $È -> $E; $Ê -> $E; $Ë -> $E;
        $í -> $i; $ì -> $i; $î -> $i; $ï -> $i;
        $Í -> $I; $Ì -> $I; $Î -> $I; $Ï -> $I;
        $ó -> $o; $ò -> $o; $ô -> $o; $õ -> $o; $ö -> $o;
        $Ó -> $O; $Ò -> $O; $Ô -> $O; $Õ -> $O; $Ö -> $O;
        $ú -> $u; $ù -> $u; $û -> $u; $ü -> $u;
        $Ú -> $U; $Ù -> $U; $Û -> $U; $Ü -> $U;
        $ç -> $c; $Ç -> $C;
        $ñ -> $n; $Ñ -> $N;
        _ -> C
    end.
