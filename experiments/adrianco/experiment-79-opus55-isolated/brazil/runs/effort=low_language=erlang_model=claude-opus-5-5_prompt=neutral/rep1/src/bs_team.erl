%% Team name normalisation.
%%
%% The datasets spell the same club in many ways ("Palmeiras-SP",
%% "Palmeiras - SP", "Palmeiras", "Sao Paulo" / "São Paulo", "Sport Recife").
%% Every name is reduced to a canonical key:
%%   * accents, case, dots and extra whitespace are folded away
%%   * a trailing state / country code is split off
%%   * well known clubs are mapped through an alias table
%%   * other clubs keep "base-uf" as key so that e.g. "Flamengo - PI" never
%%     collides with Flamengo (RJ)
-module(bs_team).
-export([fold/1, classify/1, key/2, resolve/1, display/1, rivalries/0, club_displays/0]).

-define(UFS, [<<"AC">>, <<"AL">>, <<"AP">>, <<"AM">>, <<"BA">>, <<"CE">>, <<"DF">>,
              <<"ES">>, <<"GO">>, <<"MA">>, <<"MT">>, <<"MS">>, <<"MG">>, <<"PA">>,
              <<"PB">>, <<"PR">>, <<"PE">>, <<"PI">>, <<"RJ">>, <<"RN">>, <<"RS">>,
              <<"RO">>, <<"RR">>, <<"SC">>, <<"SP">>, <<"SE">>, <<"TO">>]).
-define(COUNTRIES, [<<"URU">>, <<"PAR">>, <<"EQU">>, <<"PER">>, <<"VEN">>, <<"ARG">>,
                    <<"CHI">>, <<"COL">>, <<"BOL">>, <<"ECU">>]).

%% {Display, UF, BareAliases, UFOnlyAliases}
%% BareAliases identify the club on their own; UFOnlyAliases only together
%% with the club's state (e.g. "Atlético" + MG).
clubs() ->
    [{<<"Flamengo">>, <<"rj">>, [<<"flamengo">>, <<"cr flamengo">>, <<"clube de regatas do flamengo">>], []},
     {<<"Fluminense">>, <<"rj">>, [<<"fluminense">>, <<"fluminense fc">>], []},
     {<<"Vasco">>, <<"rj">>, [<<"vasco">>, <<"vasco da gama">>, <<"cr vasco da gama">>], []},
     {<<"Botafogo">>, <<"rj">>, [<<"botafogo">>, <<"botafogo fr">>], []},
     {<<"Palmeiras">>, <<"sp">>, [<<"palmeiras">>, <<"se palmeiras">>], []},
     {<<"Corinthians">>, <<"sp">>, [<<"corinthians">>, <<"sc corinthians">>,
                                    <<"sport club corinthians paulista">>], []},
     {<<"São Paulo"/utf8>>, <<"sp">>, [<<"sao paulo">>, <<"sao paulo fc">>], []},
     {<<"Santos">>, <<"sp">>, [<<"santos">>, <<"santos fc">>], []},
     {<<"Grêmio"/utf8>>, <<"rs">>, [<<"gremio">>, <<"gremio fbpa">>], []},
     {<<"Internacional">>, <<"rs">>, [<<"internacional">>, <<"sc internacional">>], [<<"inter">>]},
     {<<"Cruzeiro">>, <<"mg">>, [<<"cruzeiro">>, <<"cruzeiro ec">>], []},
     {<<"Atlético-MG"/utf8>>, <<"mg">>, [<<"atletico mineiro">>, <<"atletico mg">>], [<<"atletico">>]},
     {<<"Athletico-PR">>, <<"pr">>, [<<"athletico">>, <<"athletico paranaense">>,
                                     <<"atletico paranaense">>, <<"athletico pr">>, <<"atletico pr">>],
      [<<"atletico">>]},
     {<<"Atlético-GO"/utf8>>, <<"go">>, [<<"atletico goianiense">>, <<"atletico go">>], [<<"atletico">>]},
     {<<"América-MG"/utf8>>, <<"mg">>, [<<"america mineiro">>, <<"america mg">>,
                                        <<"america fc (minas gerais)">>], [<<"america">>]},
     {<<"América-RN"/utf8>>, <<"rn">>, [<<"america rn">>, <<"america fc natal">>,
                                        <<"america de natal">>], [<<"america">>]},
     {<<"Bahia">>, <<"ba">>, [<<"bahia">>, <<"ec bahia">>], []},
     {<<"Vitória"/utf8>>, <<"ba">>, [<<"vitoria">>, <<"ec vitoria">>, <<"vitoria ec">>], []},
     {<<"Sport">>, <<"pe">>, [<<"sport">>, <<"sport recife">>, <<"sport club do recife">>], []},
     {<<"Náutico"/utf8>>, <<"pe">>, [<<"nautico">>, <<"nautico capibaribe">>], []},
     {<<"Santa Cruz">>, <<"pe">>, [<<"santa cruz">>, <<"santa cruz fc">>], []},
     {<<"Fortaleza">>, <<"ce">>, [<<"fortaleza">>, <<"fortaleza ec">>, <<"fortaleza fc">>,
                                  <<"fortaleza esporte clube">>], []},
     {<<"Ceará"/utf8>>, <<"ce">>, [<<"ceara">>, <<"ceara sc">>, <<"ceara sporting club">>], []},
     {<<"Goiás"/utf8>>, <<"go">>, [<<"goias">>, <<"goias ec">>], []},
     {<<"Coritiba">>, <<"pr">>, [<<"coritiba">>, <<"coritiba fc">>], []},
     {<<"Paraná"/utf8>>, <<"pr">>, [<<"parana">>, <<"parana clube">>, <<"ca parana">>], []},
     {<<"Chapecoense">>, <<"sc">>, [<<"chapecoense">>], []},
     {<<"Figueirense">>, <<"sc">>, [<<"figueirense">>], []},
     {<<"Avaí"/utf8>>, <<"sc">>, [<<"avai">>, <<"avai fc">>], []},
     {<<"Criciúma"/utf8>>, <<"sc">>, [<<"criciuma">>], []},
     {<<"Joinville">>, <<"sc">>, [<<"joinville">>], []},
     {<<"Juventude">>, <<"rs">>, [<<"juventude">>, <<"ec juventude">>], []},
     {<<"Bragantino">>, <<"sp">>, [<<"bragantino">>, <<"red bull bragantino">>, <<"rb bragantino">>], []},
     {<<"Ponte Preta">>, <<"sp">>, [<<"ponte preta">>], []},
     {<<"Guarani">>, <<"sp">>, [<<"guarani">>], []},
     {<<"Portuguesa">>, <<"sp">>, [<<"portuguesa">>, <<"portuguesa desportos">>], []},
     {<<"Cuiabá"/utf8>>, <<"mt">>, [<<"cuiaba">>], []},
     {<<"CSA">>, <<"al">>, [<<"csa">>, <<"cs alagoano">>], []},
     {<<"CRB">>, <<"al">>, [<<"crb">>, <<"c r b">>], []},
     {<<"Paysandu">>, <<"pa">>, [<<"paysandu">>], []},
     {<<"Remo">>, <<"pa">>, [<<"remo">>, <<"clube do remo">>], []},
     {<<"ABC">>, <<"rn">>, [<<"abc">>], []},
     {<<"Brasil de Pelotas">>, <<"rs">>, [<<"brasil de pelotas">>], [<<"brasil">>]}].

%% Traditional rivalries: {Name, KeyA, KeyB}
rivalries() ->
    [{<<"Fla-Flu">>, <<"flamengo">>, <<"fluminense">>},
     {<<"Clássico dos Milhões"/utf8>>, <<"flamengo">>, <<"vasco">>},
     {<<"Clássico da Rivalidade"/utf8>>, <<"botafogo">>, <<"flamengo">>},
     {<<"Clássico dos Gigantes"/utf8>>, <<"fluminense">>, <<"vasco">>},
     {<<"Clássico Vovô"/utf8>>, <<"botafogo">>, <<"fluminense">>},
     {<<"Clássico da Amizade"/utf8>>, <<"botafogo">>, <<"vasco">>},
     {<<"Derby Paulista">>, <<"corinthians">>, <<"palmeiras">>},
     {<<"Majestoso">>, <<"corinthians">>, <<"sao paulo">>},
     {<<"Choque-Rei">>, <<"palmeiras">>, <<"sao paulo">>},
     {<<"Clássico Alvinegro"/utf8>>, <<"corinthians">>, <<"santos">>},
     {<<"Clássico da Saudade"/utf8>>, <<"palmeiras">>, <<"santos">>},
     {<<"San-São"/utf8>>, <<"santos">>, <<"sao paulo">>},
     {<<"Grenal">>, <<"gremio">>, <<"internacional">>},
     {<<"Clássico Mineiro"/utf8>>, <<"atletico-mg">>, <<"cruzeiro">>},
     {<<"Ba-Vi">>, <<"bahia">>, <<"vitoria">>},
     {<<"Atletiba">>, <<"athletico-pr">>, <<"coritiba">>},
     {<<"Clássico dos Clássicos"/utf8>>, <<"nautico">>, <<"sport">>},
     {<<"Clássico das Multidões"/utf8>>, <<"santa cruz">>, <<"sport">>},
     {<<"Clássico das Emoções"/utf8>>, <<"nautico">>, <<"santa cruz">>},
     {<<"Clássico-Rei"/utf8>>, <<"ceara">>, <<"fortaleza">>},
     {<<"Clássico Goiano"/utf8>>, <<"atletico-go">>, <<"goias">>},
     {<<"Clássico de Florianópolis"/utf8>>, <<"avai">>, <<"figueirense">>},
     {<<"Re-Pa">>, <<"paysandu">>, <<"remo">>}].

%% Accent/case-insensitive form of a string.
-spec fold(binary()) -> binary().
fold(B) when is_binary(B) ->
    case unicode:characters_to_nfd_list(B) of
        L when is_list(L) ->
            L1 = [C || C <- L, not (C >= 16#300 andalso C =< 16#36F), C =/= $.],
            Words = string:lexemes(string:lowercase(L1), [$\s, $\t, 160]),
            unicode:characters_to_binary(lists:join(" ", Words));
        _ ->
            string:lowercase(B)
    end.

%% -> {club, Key} | {uf, FoldedBase, Base, Code} | {bare, Folded, Name}
classify(Name0) ->
    Name = string:trim(Name0),
    {Alias, Pairs, _} = tables(),
    Whole = fold(Name),
    case maps:find(Whole, Alias) of
        {ok, Key} -> {club, Key};
        error ->
            case split(Name) of
                {Base, Code} ->
                    FB = strip_affixes(fold(Base)),
                    case maps:find({FB, Code}, Pairs) of
                        {ok, Key} -> {club, Key};
                        error -> {uf, FB, string:trim(Base), Code}
                    end;
                none ->
                    Stripped = strip_affixes(Whole),
                    case maps:find(Stripped, Alias) of
                        {ok, Key} -> {club, Key};
                        error -> {bare, Stripped, Name}
                    end
            end
    end.

%% "Floresta EC", "SC Genus", "Paulista Futebol Clube" -> club name proper.
strip_affixes(F) ->
    case re:run(F, "^(?:(?:ec|fc|sc|ad|ae|se|ce|ge) )?(.+?)(?: (?:ec|fc|sc|futebol clube|esporte clube))?$",
                [unicode, {capture, all_but_first, binary}]) of
        {match, [Core]} when Core =/= <<>> -> Core;
        _ -> F
    end.

%% Final key for a classified name. BareMap maps a bare folded name to the
%% single "base-uf" key it is known under (built from the loaded data).
key({club, Key}, _) -> Key;
key({uf, FB, _, Code}, _) -> <<FB/binary, "-", Code/binary>>;
key({bare, FB, _}, BareMap) -> maps:get(FB, BareMap, FB).

%% Resolve free text typed by a user to a team key present in the data.
-spec resolve(binary()) -> {ok, binary()} | not_found.
resolve(Input) ->
    Teams = persistent_term:get({brsoccer, team_counts}),
    Key = key(classify(Input), persistent_term:get({brsoccer, bare_map})),
    case Teams of
        #{Key := _} -> {ok, Key};
        _ ->
            F = fold(Input),
            Cands = [{N, K} || K := N <- Teams, F =/= <<>>, binary:match(K, F) =/= nomatch],
            case lists:reverse(lists:sort(Cands)) of
                [{_, Best} | _] -> {ok, Best};
                [] -> not_found
            end
    end.

display(Key) ->
    maps:get(Key, persistent_term:get({brsoccer, team_display}, #{}), Key).

club_displays() -> element(3, tables()).

%% --- internals -------------------------------------------------------------

split(Name) ->
    Res = [{"^(.+?)\\s+-\\s*([A-Za-z]{2,3})$", any},
           {"^(.+?)-([A-Za-z]{2,3})$", any},
           {"^(.+?)\\s+\\(([A-Za-z]{2,3})\\)$", any},
           {"^(.+?)\\s+([A-Z]{2})$", uf}],
    split(Name, Res).

split(_, []) -> none;
split(Name, [{Re, Kind} | Rest]) ->
    case re:run(Name, Re, [unicode, {capture, all_but_first, binary}]) of
        {match, [Base, Code0]} ->
            Code = string:uppercase(Code0),
            Ok = lists:member(Code, ?UFS) orelse
                 (Kind =:= any andalso lists:member(Code, ?COUNTRIES)),
            case Ok of
                true -> {Base, string:lowercase(Code)};
                false -> split(Name, Rest)
            end;
        nomatch -> split(Name, Rest)
    end.

tables() ->
    case persistent_term:get({brsoccer, club_tables}, undefined) of
        undefined ->
            T = build_tables(),
            persistent_term:put({brsoccer, club_tables}, T),
            T;
        T -> T
    end.

build_tables() ->
    lists:foldl(
      fun({Display, UF, Bare, UFOnly}, {A, P, D}) ->
              Key = fold(Display),
              A1 = lists:foldl(fun(B, M) -> M#{B => Key} end, A, Bare),
              P1 = lists:foldl(fun(B, M) -> M#{{B, UF} => Key} end, P, Bare ++ UFOnly),
              {A1, P1, D#{Key => Display}}
      end, {#{}, #{}, #{}}, clubs()).
