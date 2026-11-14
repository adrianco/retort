%%% Normalisation helpers: accent folding, team-name canonicalisation,
%%% date parsing for the several formats found in the datasets.
-module(brsoccer_norm).
-export([trim/1, fold/1, team/1, team_key/1, parse_date/1, to_int/1, competition/1,
         competition_name/1, format_date/1]).

%% Fast ASCII-whitespace trim for binaries (string:trim/1 is much slower).
-spec trim(binary()) -> binary().
trim(<<C, R/binary>>) when C =:= $\s; C =:= $\t; C =:= $\r; C =:= $\n -> trim(R);
trim(B) -> trim_right(B, byte_size(B)).

trim_right(_, 0) -> <<>>;
trim_right(B, N) ->
    case binary:at(B, N - 1) of
        C when C =:= $\s; C =:= $\t; C =:= $\r; C =:= $\n -> trim_right(B, N - 1);
        _ -> binary:part(B, 0, N)
    end.

%% ---------------------------------------------------------------- folding
%% Lower-case, strip accents (NFD + drop combining marks), collapse spaces.
-spec fold(binary() | string()) -> binary().
fold(Text) ->
    L0 = case unicode:characters_to_nfd_list(Text) of
             L when is_list(L) -> L;
             _ -> binary_to_list(iolist_to_binary(Text))   % invalid UTF-8: treat as latin-1
         end,
    L1 = [C || C <- string:lowercase(L0), not (C >= 16#300 andalso C =< 16#36F)],
    Tokens = string:lexemes(L1, " \t\r\n"),
    unicode:characters_to_binary(lists:join($\s, Tokens)).

%% ------------------------------------------------------------- team names
-define(STATES, ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
                 "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]).

%% Returns {CanonicalKey, DisplayName}.  The key is identical for all the
%% spellings of the same club ("Palmeiras-SP", "Palmeiras - SP", "Palmeiras").
-spec team(binary()) -> {binary(), binary()}.
team(Raw0) ->
    Raw = string:trim(Raw0),
    {BaseRaw, State0} = split_suffix(Raw),
    {Base, State} = canonical(fold(BaseRaw), State0),
    Key = case {State, default_state(Base)} of
              {undefined, _} -> Base;
              {S, S} -> Base;
              {_, unambiguous} -> Base;
              {S, _} -> <<Base/binary, "-", S/binary>>
          end,
    Display = case display_override(Key) of
                  undefined ->
                      case Key of
                          Base -> BaseRaw;
                          _ -> <<BaseRaw/binary, "-", (string:uppercase(State))/binary>>
                      end;
                  D -> D
              end,
    {Key, Display}.

-spec team_key(binary()) -> binary().
team_key(Raw) -> element(1, team(Raw)).

%% Split "Name-SP", "Name - SP", "Name SP", "Name (URU)", "Name-URU".
split_suffix(Raw) ->
    Forms = [{"^(.+?)\\s*-\\s*([A-Za-z]{2,3})$", any},
             {"^(.+?)\\s+\\(([A-Z]{2,3})\\)$", any},
             {"^(.+?)\\s+([A-Z]{2})$", state}],
    split_suffix(Raw, Forms).

split_suffix(Raw, []) -> {Raw, undefined};
split_suffix(Raw, [{Re, Kind} | Rest]) ->
    case re:run(Raw, Re, [unicode, {capture, all_but_first, binary}]) of
        {match, [Base, Code]} ->
            Upper = string:uppercase(Code),
            IsState = lists:member(binary_to_list(Upper), ?STATES),
            case IsState orelse (Kind =:= any andalso byte_size(Code) =:= 3 andalso Code =:= Upper) of
                true -> {string:trim(Base), string:lowercase(Code)};
                false -> split_suffix(Raw, Rest)
            end;
        nomatch -> split_suffix(Raw, Rest)
    end.

canonical(Folded0, State0) ->
    Folded = binary:replace(Folded0, [<<".">>, <<"'">>], <<>>, [global]),
    case alias(Folded, State0) of
        undefined ->
            Stripped = strip_affixes(Folded),
            case alias(Stripped, State0) of
                undefined -> {Stripped, State0};
                R -> R
            end;
        R -> R
    end.

strip_affixes(Name) ->
    N1 = lists:foldl(fun(P, N) ->
                             PS = byte_size(P),
                             case N of
                                 <<P:PS/binary, " ", R/binary>> when R =/= <<>>, N =:= Name -> R;
                                 _ -> N
                             end
                     end, Name,
                     [<<"ec">>, <<"fc">>, <<"sc">>, <<"ad">>, <<"ae">>, <<"ca">>, <<"ce">>,
                      <<"se">>, <<"ge">>, <<"cs">>]),
    lists:foldl(fun(S, N) ->
                        SS = byte_size(S) + 1, NS = byte_size(N),
                        case NS > SS andalso binary:part(N, NS - SS, SS) =:= <<" ", S/binary>> of
                            true -> binary:part(N, 0, NS - SS);
                            false -> N
                        end
                end, N1,
                [<<"futebol clube">>, <<"esporte clube">>, <<"ec">>, <<"fc">>, <<"sc">>]).

%% alias(FoldedName, State) -> {Base, State} | undefined
alias(<<"atletico">>, <<"pr">>) -> {<<"athletico">>, <<"pr">>};
alias(<<"atletico">>, <<"go">>) -> {<<"atletico">>, <<"go">>};
alias(N, S) ->
    case N of
        <<"atletico mineiro">> -> {<<"atletico">>, <<"mg">>};
        <<"clube atletico mineiro">> -> {<<"atletico">>, <<"mg">>};
        <<"atletico paranaense">> -> {<<"athletico">>, <<"pr">>};
        <<"athletico paranaense">> -> {<<"athletico">>, <<"pr">>};
        <<"club athletico paranaense">> -> {<<"athletico">>, <<"pr">>};
        <<"atletico goianiense">> -> {<<"atletico">>, <<"go">>};
        <<"atletico acreano">> -> {<<"atletico">>, <<"ac">>};
        <<"america mineiro">> -> {<<"america">>, <<"mg">>};
        <<"america fc (minas gerais)">> -> {<<"america">>, <<"mg">>};
        <<"america de natal">> -> {<<"america">>, <<"rn">>};
        <<"america fc natal">> -> {<<"america">>, <<"rn">>};
        <<"vasco da gama">> -> {<<"vasco">>, <<"rj">>};
        <<"cr vasco da gama">> -> {<<"vasco">>, <<"rj">>};
        <<"sport recife">> -> {<<"sport">>, <<"pe">>};
        <<"sport club do recife">> -> {<<"sport">>, <<"pe">>};
        <<"sport club corinthians paulista">> -> {<<"corinthians">>, <<"sp">>};
        <<"corinthians paulista">> -> {<<"corinthians">>, <<"sp">>};
        <<"se palmeiras">> -> {<<"palmeiras">>, <<"sp">>};
        <<"sociedade esportiva palmeiras">> -> {<<"palmeiras">>, <<"sp">>};
        <<"cr flamengo">> -> {<<"flamengo">>, <<"rj">>};
        <<"clube de regatas do flamengo">> -> {<<"flamengo">>, <<"rj">>};
        <<"flamengo do piaui">> -> {<<"flamengo">>, <<"pi">>};
        <<"sao paulo futebol clube">> -> {<<"sao paulo">>, <<"sp">>};
        <<"santos futebol clube">> -> {<<"santos">>, <<"sp">>};
        <<"gremio foot-ball porto alegrense">> -> {<<"gremio">>, <<"rs">>};
        <<"sport club internacional">> -> {<<"internacional">>, <<"rs">>};
        <<"inter">> -> {<<"internacional">>, <<"rs">>};
        <<"ec internacional">> when S =:= <<"sc">> -> {<<"internacional">>, <<"sc">>};
        <<"ceara sporting club">> -> {<<"ceara">>, <<"ce">>};
        <<"fortaleza esporte clube">> -> {<<"fortaleza">>, <<"ce">>};
        <<"nautico capibaribe">> -> {<<"nautico">>, <<"pe">>};
        <<"red bull bragantino">> -> {<<"bragantino">>, <<"sp">>};
        <<"rb bragantino">> -> {<<"bragantino">>, <<"sp">>};
        <<"gremio barueri">> -> {<<"barueri">>, <<"sp">>};
        <<"cs alagoano">> -> {<<"csa">>, <<"al">>};
        <<"c r b">> -> {<<"crb">>, <<"al">>};
        <<"clube do remo">> -> {<<"remo">>, <<"pa">>};
        <<"portuguesa desportos">> -> {<<"portuguesa">>, <<"sp">>};
        <<"brasil de pelotas">> -> {<<"brasil">>, <<"rs">>};
        <<"ca parana">> -> {<<"parana">>, <<"pr">>};
        <<"parana clube">> -> {<<"parana">>, <<"pr">>};
        <<"moto clube">> -> {<<"moto club">>, <<"ma">>};
        <<"moto club de sao luis">> -> {<<"moto club">>, <<"ma">>};
        <<"guarani de juazeiro">> -> {<<"guarani">>, <<"ce">>};
        <<"ind santa fe">> -> {<<"independiente santa fe">>, undefined};
        <<"tolima">> -> {<<"deportes tolima">>, undefined};
        _ -> undefined
    end.

%% Names shared by several clubs: the state is kept in the key unless it is
%% the listed default (the best-known club).  `none` = always keep the state.
default_state(Base) ->
    case Base of
        <<"atletico">> -> <<"mg">>;
        <<"america">> -> <<"mg">>;
        <<"botafogo">> -> <<"rj">>;
        <<"flamengo">> -> <<"rj">>;
        <<"fluminense">> -> <<"rj">>;
        <<"guarani">> -> <<"sp">>;
        <<"bragantino">> -> <<"sp">>;
        <<"internacional">> -> <<"rs">>;
        <<"juventude">> -> <<"rs">>;
        <<"santa cruz">> -> <<"pe">>;
        <<"nautico">> -> <<"pe">>;
        <<"vitoria">> -> <<"ba">>;
        <<"santos">> -> <<"sp">>;
        <<"portuguesa">> -> <<"sp">>;
        <<"boavista">> -> <<"rj">>;
        <<"operario">> -> <<"pr">>;
        <<"brasil">> -> <<"rs">>;
        <<"ypiranga">> -> <<"rs">>;
        <<"caxias">> -> <<"rs">>;
        <<"independente">> -> <<"pa">>;
        <<"comercial">> -> none;
        <<"nacional">> -> none;
        <<"river plate">> -> none;
        <<"universitario">> -> none;
        <<"barcelona">> -> none;
        <<"sao jose">> -> none;
        <<"sao raimundo">> -> none;
        <<"rio branco">> -> none;
        <<"river">> -> none;
        _ -> unambiguous
    end.

display_override(Key) ->
    case Key of
        <<"atletico">> -> <<"Atlético-MG"/utf8>>;
        <<"atletico-go">> -> <<"Atlético-GO"/utf8>>;
        <<"athletico">> -> <<"Athletico-PR">>;
        <<"america">> -> <<"América-MG"/utf8>>;
        <<"america-rn">> -> <<"América-RN"/utf8>>;
        <<"sao paulo">> -> <<"São Paulo"/utf8>>;
        <<"gremio">> -> <<"Grêmio"/utf8>>;
        <<"goias">> -> <<"Goiás"/utf8>>;
        <<"ceara">> -> <<"Ceará"/utf8>>;
        <<"avai">> -> <<"Avaí"/utf8>>;
        <<"vitoria">> -> <<"Vitória"/utf8>>;
        <<"nautico">> -> <<"Náutico"/utf8>>;
        <<"parana">> -> <<"Paraná"/utf8>>;
        <<"criciuma">> -> <<"Criciúma"/utf8>>;
        <<"cuiaba">> -> <<"Cuiabá"/utf8>>;
        <<"vasco">> -> <<"Vasco">>;
        <<"sport">> -> <<"Sport">>;
        <<"bragantino">> -> <<"Red Bull Bragantino">>;
        <<"botafogo">> -> <<"Botafogo">>;
        <<"flamengo">> -> <<"Flamengo">>;
        <<"fluminense">> -> <<"Fluminense">>;
        <<"internacional">> -> <<"Internacional">>;
        <<"santos">> -> <<"Santos">>;
        <<"corinthians">> -> <<"Corinthians">>;
        <<"palmeiras">> -> <<"Palmeiras">>;
        <<"csa">> -> <<"CSA">>;
        <<"crb">> -> <<"CRB">>;
        <<"abc">> -> <<"ABC">>;
        <<"asa">> -> <<"ASA">>;
        _ -> undefined
    end.

%% ------------------------------------------------------------------ dates
%% Accepts "2023-09-24", "2012-05-19 18:30:00", "29/03/2003", "2023".
-spec parse_date(binary()) -> {calendar:date(), binary() | undefined} | undefined.
parse_date(Bin0) ->
    Bin = trim(Bin0),
    case re:run(Bin, "^(\\d{4})-(\\d{1,2})-(\\d{1,2})(?:[ T](\\d{1,2}:\\d{2}(?::\\d{2})?))?",
                [{capture, all_but_first, binary}]) of
        {match, [Y, M, D | T]} -> mk_date(Y, M, D, T);
        nomatch ->
            case re:run(Bin, "^(\\d{1,2})/(\\d{1,2})/(\\d{4})(?:[ T](\\d{1,2}:\\d{2}(?::\\d{2})?))?",
                        [{capture, all_but_first, binary}]) of
                {match, [D, M, Y | T]} -> mk_date(Y, M, D, T);
                nomatch -> undefined
            end
    end.

mk_date(Y, M, D, T) ->
    Date = {binary_to_integer(Y), binary_to_integer(M), binary_to_integer(D)},
    case calendar:valid_date(Date) of
        true -> {Date, case T of [Time] when Time =/= <<>> -> Time; _ -> undefined end};
        false -> undefined
    end.

format_date(undefined) -> <<"unknown date">>;
format_date({Y, M, D}) ->
    iolist_to_binary(io_lib:format("~4..0B-~2..0B-~2..0B", [Y, M, D])).

%% "3", "3.0", 3 -> 3 ; "", "NA", "-" -> undefined
-spec to_int(term()) -> integer() | undefined.
to_int(I) when is_integer(I) -> I;
to_int(F) when is_float(F) -> round(F);
to_int(B) when is_binary(B) ->
    S = trim(B),
    try binary_to_integer(S)
    catch error:badarg ->
            try round(binary_to_float(S))
            catch error:badarg -> undefined
            end
    end;
to_int(_) -> undefined.

%% ----------------------------------------------------------- competitions
-spec competition(term()) -> atom() | undefined.
competition(A) when is_atom(A) -> A;
competition(Bin) when is_binary(Bin) ->
    F = fold(Bin),
    Has = fun(P) -> binary:match(F, P) =/= nomatch end,
    case true of
        _ when F =:= <<>> -> undefined;
        _ when F =:= <<"all">>; F =:= <<"any">> -> undefined;
        _ -> case {Has(<<"libertadores">>),
                   Has(<<"copa">>) orelse Has(<<"cup">>),
                   Has(<<"serie b">>) orelse F =:= <<"serie_b">>,
                   Has(<<"serie c">>) orelse F =:= <<"serie_c">>,
                   Has(<<"brasileir">>) orelse Has(<<"serie a">>) orelse Has(<<"serie_a">>)
                       orelse Has(<<"campeonato">>)} of
                 {true, _, _, _, _} -> libertadores;
                 {_, true, _, _, _} -> copa_do_brasil;
                 {_, _, true, _, _} -> serie_b;
                 {_, _, _, true, _} -> serie_c;
                 {_, _, _, _, true} -> serie_a;
                 _ -> unknown
             end
    end.

competition_name(serie_a) -> <<"Brasileirão"/utf8>>;
competition_name(serie_b) -> <<"Série B"/utf8>>;
competition_name(serie_c) -> <<"Série C"/utf8>>;
competition_name(copa_do_brasil) -> <<"Copa do Brasil">>;
competition_name(libertadores) -> <<"Libertadores">>;
competition_name(undefined) -> <<"all competitions">>;
competition_name(Other) -> iolist_to_binary(io_lib:format("~p", [Other])).
