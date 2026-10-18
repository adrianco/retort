%%% Text helpers: team-name normalisation, date parsing and integer parsing.
%%%
%%% Team names in the datasets vary: "Palmeiras-SP", "Palmeiras",
%%% "Sociedade Esportiva Palmeiras", "Vasco Da Gama RJ", "Atlético-MG".
%%% split_team/1 separates a name into a base key (lower-case, accent-free,
%%% long forms resolved) and a state code when one is present. bs_data uses
%%% the state only to tell apart clubs that share a base name.
-module(bs_text).

-export([split_team/1, normalize_team/1, title/1, fold/1, parse_date/1,
         parse_int/1, competition_name/2]).

-define(U(S), unicode:characters_to_binary(S)).

%% Long-form names mapped to a base key and a state code. The state is used
%% only when the base name is shared by clubs from different states.
-define(ALIASES, [
    {"corinthians paulista", "corinthians", "sp"},
    {"gremio foot-ball porto alegrense", "gremio", "rs"},
    {"sao paulo fc", "sao paulo", "sp"},
    {"vasco da gama", "vasco", "rj"},
    {"athletico", "atletico", "pr"},
    {"athletico paranaense", "atletico", "pr"},
    {"atletico mineiro", "atletico", "mg"},
    {"atletico goianiense", "atletico", "go"},
    {"atletico paranaense", "atletico", "pr"},
    {"recife", "sport", "pe"},
    {"ceara sporting club", "ceara", "ce"}
]).

%% Leading words stripped from long-form club names.
-define(PREFIXES, [
    "sport club ", "sociedade esportiva ", "esporte clube ", "clube de regatas ",
    "clube atletico ", "associacao atletica ", "clube de futebol ",
    "sociedade ", "clube ", "ec ", "ad ", "sc ", "ac ", "se ", "cr "
]).

%% Connecting words left behind after a prefix, e.g. "Sport Club do Recife".
-define(CONNECTORS, ["do ", "da ", "de "]).

%% Two-letter upper-case words that are not state codes.
-define(NOT_STATES, ["FC", "SC", "EC", "AC", "AD"]).

%% Returns {BaseKey, State} where State is a lower-case code or none.
-spec split_team(binary() | string()) -> {binary(), binary() | none}.
split_team(Name) ->
    {Core, State} = strip_state(strip_parens(to_list(Name))),
    {Base, AliasState} = base_key(Core),
    {Base, if State =:= none -> AliasState; true -> State end}.

-spec normalize_team(binary() | string()) -> binary().
normalize_team(Name) ->
    {Base, _State} = split_team(Name),
    Base.

%% Display form of a base key: "sao paulo" -> "Sao Paulo".
-spec title(binary()) -> binary().
title(Key) ->
    Words = string:split(binary_to_list(Key), " ", all),
    ?U(lists:join(" ", [[string:uppercase([C]) | Rest] || [C | Rest] <- Words])).

%% Lower-case and remove diacritics: "Grêmio" -> "gremio".
-spec fold(binary() | string()) -> string().
fold(Text) ->
    Decomposed = unicode:characters_to_nfd_list(to_list(Text)),
    string:lowercase([C || C <- Decomposed, not is_combining_mark(C)]).

%% Accepts ISO ("2023-09-24", "2012-05-19 18:30:00") and Brazilian
%% ("29/03/2003") dates; returns ISO "YYYY-MM-DD".
-spec parse_date(binary()) -> {ok, binary()} | error.
parse_date(<<Y:4/binary, $-, M:2/binary, $-, D:2/binary, _/binary>>) ->
    {ok, <<Y/binary, $-, M/binary, $-, D/binary>>};
parse_date(<<D:2/binary, $/, M:2/binary, $/, Y:4/binary, _/binary>>) ->
    {ok, <<Y/binary, $-, M/binary, $-, D/binary>>};
parse_date(_) ->
    error.

%% Parses "2", "1.0" (BR-Football stores goals as floats) and "  3 ".
-spec parse_int(binary()) -> {ok, integer()} | error.
parse_int(Bin) ->
    Trimmed = string:trim(Bin),
    try binary_to_integer(Trimmed) of
        N -> {ok, N}
    catch
        error:badarg ->
            try trunc(binary_to_float(Trimmed)) of
                N -> {ok, N}
            catch
                error:badarg -> error
            end
    end.

%% Maps the tournament label used by a source file to a display name.
-spec competition_name(binary(), binary()) -> binary().
competition_name(<<"Serie A">>, _) -> ?U("Brasileirão Série A");
competition_name(<<"Serie B">>, _) -> ?U("Brasileirão Série B");
competition_name(<<"Serie C">>, _) -> ?U("Brasileirão Série C");
competition_name(_, Fallback) -> Fallback.

%% --- internals -------------------------------------------------------------

to_list(B) when is_binary(B) -> unicode:characters_to_list(B);
to_list(L) when is_list(L) -> L.

%% Remove "(antigo ...)" style notes and country hints such as "(URU)".
strip_parens(S) ->
    collapse(re:replace(S, "\\s*\\([^)]*\\)", "", [global, unicode, {return, list}])).

%% Splits a trailing state code: "Palmeiras-SP", "Vasco Da Gama RJ".
%% A dash may be followed by either case; a space must be followed by upper case.
strip_state(S) ->
    case re:run(S, "^(.*?)(?:\\s*[-–]\\s*([A-Za-z]{2})|\\s+([A-Z]{2}))$",
                [unicode, {capture, [1, 2, 3], list}]) of
        {match, [Core, "", Space]} ->
            %% A space before an upper-case code may be part of the name ("Fortaleza FC").
            case lists:member(Space, ?NOT_STATES) of
                true -> {string:trim(Core), none};
                false -> {string:trim(Core), list_to_binary(string:lowercase(Space))}
            end;
        {match, [Core, Dash, _]} ->
            {string:trim(Core), list_to_binary(string:lowercase(Dash))};
        nomatch ->
            {S, none}
    end.

%% Returns {BaseKey, AliasState}; AliasState is none unless a long form matched.
base_key(Core) ->
    Folded = string:trim(collapse(fold(Core))),
    Stripped = strip_connectors(strip_prefix(Folded)),
    case lists:keyfind(Stripped, 1, ?ALIASES) of
        {_, Base, State} -> {?U(Base), list_to_binary(State)};
        false -> {?U(Stripped), none}
    end.

collapse(S) ->
    re:replace(S, "\\s+", " ", [global, unicode, {return, list}]).

%% string:prefix/2 returns the remainder, or nomatch.
strip_prefix(S) -> strip_first(S, ?PREFIXES).

strip_connectors(S) -> strip_first(S, ?CONNECTORS).

strip_first(S, Words) ->
    case lists:filtermap(fun(W) ->
                             case string:prefix(S, W) of
                                 nomatch -> false;
                                 Rest -> {true, Rest}
                             end
                         end, Words) of
        [Rest | _] -> Rest;
        [] -> S
    end.

%% Combining diacritical marks (U+0300..U+036F) left after NFD decomposition.
is_combining_mark(C) -> C >= 16#0300 andalso C =< 16#036F.
