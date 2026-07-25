%% Team-name / text normalization, competition canonicalization and date
%% handling. The datasets mix conventions ("Palmeiras-SP", "Palmeiras",
%% "São Paulo - SP", "Sao Paulo", "Sport Club Corinthians Paulista"), so every
%% name is folded to a canonical lowercase ASCII form before comparison.
-module(bsmcp_names).
-compile({no_auto_import, [alias/1]}).

-export([norm_text/1, canonical/1, strip_geo/1, same_team/2,
         competition/1, parse_date/1, format_date/1]).

%% Fold arbitrary UTF-8 text: drop "(...)" asides, decompose accents and strip
%% combining marks, lowercase, map non-alphanumerics to spaces, collapse runs.
-spec norm_text(unicode:chardata()) -> binary().
norm_text(Text) ->
    L0 = unicode:characters_to_list(Text),
    L1 = drop_parens(L0, 0),
    L2 = [C || C <- unicode:characters_to_nfd_list(L1),
               not (C >= 16#300 andalso C =< 16#36F)],
    L3 = string:lowercase(L2),
    L4 = [case is_alnum(C) of true -> C; false -> $\s end || C <- L3],
    unicode:characters_to_binary(string:trim(collapse(L4))).

is_alnum(C) -> (C >= $a andalso C =< $z) orelse (C >= $0 andalso C =< $9).

drop_parens([], _) -> [];
drop_parens([$( | T], D) -> drop_parens(T, D + 1);
drop_parens([$) | T], D) when D > 0 -> drop_parens(T, D - 1);
drop_parens([_ | T], D) when D > 0 -> drop_parens(T, D);
drop_parens([H | T], 0) -> [H | drop_parens(T, 0)].

collapse([$\s, $\s | T]) -> collapse([$\s | T]);
collapse([H | T]) -> [H | collapse(T)];
collapse([]) -> [].

%% Canonical club identifier: normalized text, then alias resolution (with a
%% second attempt after removing a trailing state/country token, so
%% "Grêmio - RS" and "Gremio" agree). Unknown names keep their geo token to
%% avoid conflating e.g. América-MG with América-RN.
-spec canonical(unicode:chardata()) -> binary().
canonical(Name) ->
    N = norm_text(Name),
    case alias(N) of
        {ok, Canon} -> Canon;
        error ->
            case strip_geo(N) of
                N -> N;
                Stripped ->
                    case alias(Stripped) of
                        {ok, Canon} -> Canon;
                        error -> N
                    end
            end
    end.

%% Remove a trailing 2-3 letter state/country token ("america mg" -> "america").
-spec strip_geo(binary()) -> binary().
strip_geo(Canon) ->
    case lists:reverse(binary:split(Canon, <<" ">>, [global])) of
        [Last | Rest = [_ | _]] ->
            case is_geo_token(Last) of
                true -> unicode:characters_to_binary(
                            lists:join(<<" ">>, lists:reverse(Rest)));
                false -> Canon
            end;
        _ -> Canon
    end.

is_geo_token(T) ->
    lists:member(T, [
        %% Brazilian state abbreviations
        <<"ac">>, <<"al">>, <<"ap">>, <<"am">>, <<"ba">>, <<"ce">>, <<"df">>,
        <<"es">>, <<"go">>, <<"ma">>, <<"mt">>, <<"ms">>, <<"mg">>, <<"pa">>,
        <<"pb">>, <<"pr">>, <<"pe">>, <<"pi">>, <<"rj">>, <<"rn">>, <<"rs">>,
        <<"ro">>, <<"rr">>, <<"sc">>, <<"sp">>, <<"se">>, <<"to">>,
        %% Country codes seen in the Libertadores file
        <<"arg">>, <<"bol">>, <<"bra">>, <<"chi">>, <<"col">>, <<"ecu">>,
        <<"equ">>, <<"mex">>, <<"par">>, <<"per">>, <<"uru">>, <<"ven">>,
        %% Generic club-type suffixes ("Fortaleza FC" ~ "Fortaleza")
        <<"fc">>, <<"ec">>, <<"afc">>]).

%% Loose equality used by queries: exact canonical match, or equal once a
%% geo suffix is removed from either side ("ceara" ~ "ceara ce").
-spec same_team(binary(), binary()) -> boolean().
same_team(A, A) -> true;
same_team(A, B) ->
    strip_geo(A) =:= B orelse A =:= strip_geo(B) orelse
        strip_geo(A) =:= strip_geo(B).

alias(N) ->
    M = #{
        <<"palmeiras sp">> => <<"palmeiras">>,
        <<"se palmeiras">> => <<"palmeiras">>,
        <<"flamengo rj">> => <<"flamengo">>,
        <<"cr flamengo">> => <<"flamengo">>,
        <<"clube de regatas do flamengo">> => <<"flamengo">>,
        <<"fluminense rj">> => <<"fluminense">>,
        <<"botafogo rj">> => <<"botafogo">>,
        <<"botafogo fr">> => <<"botafogo">>,
        <<"corinthians sp">> => <<"corinthians">>,
        <<"sport club corinthians paulista">> => <<"corinthians">>,
        <<"sao paulo sp">> => <<"sao paulo">>,
        <<"sao paulo fc">> => <<"sao paulo">>,
        <<"santos sp">> => <<"santos">>,
        <<"santos fc">> => <<"santos">>,
        <<"gremio rs">> => <<"gremio">>,
        <<"gremio fbpa">> => <<"gremio">>,
        <<"internacional rs">> => <<"internacional">>,
        <<"sc internacional">> => <<"internacional">>,
        <<"cruzeiro mg">> => <<"cruzeiro">>,
        <<"atletico mg">> => <<"atletico mineiro">>,
        <<"atletico mineiro mg">> => <<"atletico mineiro">>,
        <<"atletico pr">> => <<"athletico paranaense">>,
        <<"athletico pr">> => <<"athletico paranaense">>,
        <<"atletico paranaense">> => <<"athletico paranaense">>,
        <<"atletico paranaense pr">> => <<"athletico paranaense">>,
        <<"athletico paranaense pr">> => <<"athletico paranaense">>,
        <<"atletico go">> => <<"atletico goianiense">>,
        <<"atletico goianiense go">> => <<"atletico goianiense">>,
        <<"vasco rj">> => <<"vasco">>,
        <<"vasco da gama">> => <<"vasco">>,
        <<"vasco da gama rj">> => <<"vasco">>,
        <<"bahia ba">> => <<"bahia">>,
        <<"ec bahia">> => <<"bahia">>,
        <<"vitoria ba">> => <<"vitoria">>,
        <<"sport pe">> => <<"sport">>,
        <<"sport recife">> => <<"sport">>,
        <<"sport recife pe">> => <<"sport">>,
        <<"chapecoense sc">> => <<"chapecoense">>,
        <<"coritiba pr">> => <<"coritiba">>,
        <<"goias go">> => <<"goias">>,
        <<"fortaleza ce">> => <<"fortaleza">>,
        <<"fortaleza esporte clube">> => <<"fortaleza">>,
        <<"fortaleza ec">> => <<"fortaleza">>,
        <<"fortaleza fc">> => <<"fortaleza">>,
        <<"ceara ce">> => <<"ceara">>,
        <<"ceara sc">> => <<"ceara">>,
        <<"america mineiro">> => <<"america mg">>,
        <<"bragantino sp">> => <<"bragantino">>,
        <<"red bull bragantino">> => <<"bragantino">>,
        <<"rb bragantino">> => <<"bragantino">>,
        <<"avai sc">> => <<"avai">>,
        <<"figueirense sc">> => <<"figueirense">>,
        <<"ponte preta sp">> => <<"ponte preta">>,
        <<"portuguesa sp">> => <<"portuguesa">>,
        <<"juventude rs">> => <<"juventude">>,
        <<"cuiaba mt">> => <<"cuiaba">>,
        <<"csa al">> => <<"csa">>,
        <<"parana pr">> => <<"parana">>,
        <<"nautico pe">> => <<"nautico">>,
        <<"santa cruz pe">> => <<"santa cruz">>,
        <<"joinville sc">> => <<"joinville">>,
        <<"criciuma sc">> => <<"criciuma">>,
        <<"guarani sp">> => <<"guarani">>,
        <<"santo andre sp">> => <<"santo andre">>,
        <<"sao caetano sp">> => <<"sao caetano">>,
        <<"paysandu pa">> => <<"paysandu">>,
        <<"brasiliense df">> => <<"brasiliense">>
    },
    case M of
        #{N := Canon} -> {ok, Canon};
        _ -> error
    end.

%% Map a user-supplied competition string to the canonical competition name
%% used in the match store; `any` when absent/unrecognized.
-spec competition(unicode:chardata() | undefined) -> binary() | any.
competition(undefined) -> any;
competition(Text) ->
    N = norm_text(Text),
    Has = fun(Sub) -> binary:match(N, Sub) =/= nomatch end,
    if
        N =:= <<>> -> any;
        true ->
            case Has(<<"libertadores">>) of
                true -> <<"Copa Libertadores">>;
                false ->
                    case Has(<<"copa do brasil">>) orelse Has(<<"cup">>) of
                        true -> <<"Copa do Brasil">>;
                        false ->
                            case Has(<<"serie b">>) of
                                true -> <<"Série B"/utf8>>;
                                false ->
                                    case Has(<<"serie c">>) of
                                        true -> <<"Série C"/utf8>>;
                                        false ->
                                            case Has(<<"brasileir">>) orelse
                                                 Has(<<"serie a">>) of
                                                true -> <<"Brasileirão Série A"/utf8>>;
                                                false -> any
                                            end
                                    end
                            end
                    end
            end
    end.

%% Accepts "YYYY-MM-DD[ HH:MM:SS]" and "DD/MM/YYYY"; undefined otherwise.
-spec parse_date(binary()) -> calendar:date() | undefined.
parse_date(<<Y:4/binary, "-", M:2/binary, "-", D:2/binary, _/binary>>) ->
    mk_date(Y, M, D);
parse_date(<<D:2/binary, "/", M:2/binary, "/", Y:4/binary, _/binary>>) ->
    mk_date(Y, M, D);
parse_date(_) ->
    undefined.

mk_date(Y, M, D) ->
    try {binary_to_integer(Y), binary_to_integer(M), binary_to_integer(D)} of
        Date = {Yi, Mi, Di} when Mi >= 1, Mi =< 12, Di >= 1, Di =< 31, Yi > 1800 ->
            Date;
        _ -> undefined
    catch
        _:_ -> undefined
    end.

-spec format_date(calendar:date() | undefined) -> binary().
format_date({Y, M, D}) ->
    iolist_to_binary(io_lib:format("~4..0B-~2..0B-~2..0B", [Y, M, D]));
format_date(undefined) ->
    <<"unknown date">>.
