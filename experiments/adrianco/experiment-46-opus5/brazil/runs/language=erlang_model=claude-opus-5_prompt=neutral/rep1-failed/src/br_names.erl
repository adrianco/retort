%%%-------------------------------------------------------------------
%%% @doc Canonicalisation of team, competition and position names.
%%%
%%% The five match data sets spell the same club in at least four ways:
%%% `"Palmeiras-SP"', `"Palmeiras - SP"', `"Palmeiras"' and
%%% `"Sociedade Esportiva Palmeiras"'.  Worse, the *same* short name can
%%% mean different clubs: `"Flamengo-RJ"' and `"Flamengo - PI"' are two
%%% unrelated teams, as are `"América - MG"' and `"América - RN"'.
%%%
%%% {@link canonical/1} therefore:
%%% <ol>
%%%   <li>normalises the spelling (accents, case, punctuation),</li>
%%%   <li>splits off a trailing region code - a Brazilian UF such as
%%%       `SP' or a CONMEBOL country code such as `URU',</li>
%%%   <li>strips generic club-type affixes (`FC', `EC', `Esporte
%%%       Clube', ...) as long as something is left,</li>
%%%   <li>looks the result up in a curated registry, keyed either by
%%%       `{alias, region}' (weak aliases such as `"atletico"', which
%%%       only identify a club together with their state) or by alias
%%%       alone (strong aliases such as `"atletico mineiro"').</li>
%%% </ol>
%%% Anything not in the registry falls back to a deterministic slug
%%% that keeps the region, so unknown clubs still merge across files
%%% without ever being confused with a registered club.
%%% @end
%%%-------------------------------------------------------------------
-module(br_names).

-export([canonical/1,
         canonical_id/1,
         registry/0,
         known/1,
         info/1,
         display/1,
         region/1,
         states/0,
         competition/1,
         competition_display/1,
         competitions/0,
         rivalries/0,
         rivalry_of/2,
         strip_affixes/1,
         split_region/1]).

-type team_id() :: binary().

%%--------------------------------------------------------------------
%% @doc Canonicalise a team name found in a data set.
%%
%% Returns `{Id, Display, State, Country}'.  `Display' is the curated
%% name for registered clubs and a title-cased version of the input
%% otherwise.
-spec canonical(term()) -> {team_id(), binary(), binary() | undefined, binary() | undefined}.
canonical(Name) ->
    Norm = br_text:normalize(Name),
    {Base0, Region} = split_region(Norm),
    Base = merge_initials(Base0),
    Stripped = strip_affixes(Base),
    Candidates = case Stripped of
                     Base -> [Base];
                     <<>> -> [Base];
                     _ -> [Base, Stripped]
                 end,
    case lookup(Candidates, Region) of
        {ok, Id} ->
            #{display := Display, state := St, country := Co} = info(Id),
            {Id, Display, St, Co};
        error ->
            Key = case Stripped of
                      <<>> -> Base;
                      _ -> Stripped
                  end,
            generic(Key, Region, Name)
    end.

%%--------------------------------------------------------------------
%% @doc Just the canonical id.
-spec canonical_id(term()) -> team_id().
canonical_id(Name) ->
    {Id, _, _, _} = canonical(Name),
    Id.

%%--------------------------------------------------------------------
%% @doc Is this id a curated club?
-spec known(team_id()) -> boolean().
known(Id) -> maps:is_key(Id, by_id()).

%%--------------------------------------------------------------------
%% @doc Registry entry for an id (or a synthesised one).
-spec info(team_id()) -> map().
info(Id) ->
    case maps:find(Id, by_id()) of
        {ok, Entry} -> Entry;
        error ->
            #{id => Id, display => br_text:titlecase(binary:replace(Id, <<"-">>, <<" ">>, [global])),
              state => undefined, country => undefined, strong => [], weak => []}
    end.

-spec display(team_id()) -> binary().
display(Id) -> maps:get(display, info(Id)).

%% @doc The state (Brazilian club) or country (international club).
-spec region(team_id()) -> binary() | undefined.
region(Id) ->
    case info(Id) of
        #{state := undefined, country := C} -> C;
        #{state := S} -> S
    end.

%%--------------------------------------------------------------------
%% @doc The 27 Brazilian federal units.
-spec states() -> [binary()].
states() ->
    [<<"AC">>, <<"AL">>, <<"AM">>, <<"AP">>, <<"BA">>, <<"CE">>, <<"DF">>, <<"ES">>,
     <<"GO">>, <<"MA">>, <<"MG">>, <<"MS">>, <<"MT">>, <<"PA">>, <<"PB">>, <<"PE">>,
     <<"PI">>, <<"PR">>, <<"RJ">>, <<"RN">>, <<"RO">>, <<"RR">>, <<"RS">>, <<"SC">>,
     <<"SE">>, <<"SP">>, <<"TO">>].

countries() ->
    [<<"ARG">>, <<"BOL">>, <<"BRA">>, <<"CHI">>, <<"COL">>, <<"EQU">>, <<"MEX">>,
     <<"PAR">>, <<"PER">>, <<"URU">>, <<"VEN">>].

%%--------------------------------------------------------------------
%% @doc Canonical competition id from any spelling.
-spec competition(term()) -> binary() | undefined.
competition(Name) ->
    N = br_text:normalize(Name),
    case N of
        <<>> -> undefined;
        _ ->
            case maps:find(N, competition_aliases()) of
                {ok, Id} -> Id;
                error -> fuzzy_competition(N)
            end
    end.

-spec competition_display(binary()) -> binary().
competition_display(Id) ->
    maps:get(Id, competition_names(), br_text:titlecase(Id)).

-spec competitions() -> [{binary(), binary()}].
competitions() ->
    [{Id, competition_display(Id)}
     || Id <- [<<"brasileirao_serie_a">>, <<"brasileirao_serie_b">>,
               <<"brasileirao_serie_c">>, <<"copa_do_brasil">>, <<"libertadores">>]].

competition_names() ->
    #{<<"brasileirao_serie_a">> => <<"Brasileirão Série A"/utf8>>,
      <<"brasileirao_serie_b">> => <<"Brasileirão Série B"/utf8>>,
      <<"brasileirao_serie_c">> => <<"Brasileirão Série C"/utf8>>,
      <<"copa_do_brasil">> => <<"Copa do Brasil">>,
      <<"libertadores">> => <<"Copa Libertadores">>}.

competition_aliases() ->
    A = <<"brasileirao_serie_a">>,
    B = <<"brasileirao_serie_b">>,
    C = <<"brasileirao_serie_c">>,
    Cup = <<"copa_do_brasil">>,
    Lib = <<"libertadores">>,
    maps:from_list(
      [{br_text:normalize(N), Id}
       || {N, Id} <- [{"brasileirao", A}, {"brasileirao serie a", A}, {"serie a", A},
                      {"campeonato brasileiro", A}, {"campeonato brasileiro serie a", A},
                      {"brazilian league", A}, {"brasileiro", A}, {"a", A},
                      {"brasileirao serie b", B}, {"serie b", B}, {"segunda divisao", B},
                      {"brasileirao serie c", C}, {"serie c", C},
                      {"copa do brasil", Cup}, {"brazilian cup", Cup}, {"cup", Cup},
                      {"copa", Cup}, {"copa brasil", Cup},
                      {"libertadores", Lib}, {"copa libertadores", Lib},
                      {"conmebol libertadores", Lib}, {"copa libertadores da america", Lib}]]).

fuzzy_competition(N) ->
    case binary:match(N, <<"libertadores">>) of
        nomatch ->
            case {binary:match(N, <<"copa">>), binary:match(N, <<"brasil">>)} of
                {{_, _}, {_, _}} -> <<"copa_do_brasil">>;
                _ ->
                    case binary:match(N, <<"brasileir">>) of
                        nomatch -> undefined;
                        _ -> <<"brasileirao_serie_a">>
                    end
            end;
        _ -> <<"libertadores">>
    end.

%%--------------------------------------------------------------------
%% @doc Traditional derbies ("clássicos"), used by the derby queries.
-spec rivalries() -> [{binary(), team_id(), team_id()}].
rivalries() ->
    [{<<"Fla-Flu">>, <<"flamengo">>, <<"fluminense">>},
     {<<"Clássico dos Milhões"/utf8>>, <<"flamengo">>, <<"vasco">>},
     {<<"Clássico da Rivalidade"/utf8>>, <<"flamengo">>, <<"botafogo">>},
     {<<"Clássico Vovô"/utf8>>, <<"botafogo">>, <<"fluminense">>},
     {<<"Clássico dos Gigantes"/utf8>>, <<"botafogo">>, <<"vasco">>},
     {<<"Clássico dos Clássicos (RJ)"/utf8>>, <<"fluminense">>, <<"vasco">>},
     {<<"Derby Paulista"/utf8>>, <<"corinthians">>, <<"palmeiras">>},
     {<<"Majestoso">>, <<"corinthians">>, <<"sao-paulo">>},
     {<<"Clássico Alvinegro"/utf8>>, <<"corinthians">>, <<"santos">>},
     {<<"San-São"/utf8>>, <<"santos">>, <<"sao-paulo">>},
     {<<"Choque-Rei">>, <<"palmeiras">>, <<"sao-paulo">>},
     {<<"Clássico da Saudade"/utf8>>, <<"palmeiras">>, <<"santos">>},
     {<<"Gre-Nal">>, <<"gremio">>, <<"internacional">>},
     {<<"Clássico Mineiro"/utf8>>, <<"atletico-mg">>, <<"cruzeiro">>},
     {<<"Atletiba">>, <<"athletico-pr">>, <<"coritiba">>},
     {<<"Clássico dos Clássicos"/utf8>>, <<"nautico">>, <<"sport-recife">>},
     {<<"Ba-Vi">>, <<"bahia">>, <<"vitoria">>},
     {<<"Clássico-Rei"/utf8>>, <<"ceara">>, <<"fortaleza">>},
     {<<"Clássico do Interior"/utf8>>, <<"ponte-preta">>, <<"guarani">>},
     {<<"Superclássico das Américas"/utf8>>, <<"boca-juniors">>, <<"river-plate">>}].

%% @doc Name of the derby between two teams, if any.
-spec rivalry_of(team_id(), team_id()) -> binary() | undefined.
rivalry_of(A, B) ->
    case [N || {N, X, Y} <- rivalries(),
               (X =:= A andalso Y =:= B) orelse (X =:= B andalso Y =:= A)] of
        [Name | _] -> Name;
        [] -> undefined
    end.

%%====================================================================
%% Name parsing
%%====================================================================

%% @doc Split a trailing state/country code off a normalised name.
-spec split_region(binary()) -> {binary(), binary() | undefined}.
split_region(Norm) ->
    case lists:reverse(binary:split(Norm, <<" ">>, [global])) of
        [Last | RevRest] when RevRest =/= [] ->
            Up = string:uppercase(Last),
            case lists:member(Up, states()) orelse lists:member(Up, countries()) of
                true -> {br_text:join(lists:reverse(RevRest), <<" ">>), Up};
                false -> {Norm, undefined}
            end;
        _ -> {Norm, undefined}
    end.

%% "c s a" -> "csa"; run-together sequences of single letters that come
%% from dotted abbreviations such as "C.S.A.".
merge_initials(Base) ->
    Parts = binary:split(Base, <<" ">>, [global]),
    br_text:join(merge_initials(Parts, []), <<" ">>).

merge_initials([], Acc) -> lists:reverse(Acc);
merge_initials([A, B | T], Acc) when byte_size(A) =:= 1, byte_size(B) =:= 1 ->
    {Run, Rest} = take_singles([A, B | T], []),
    merge_initials(Rest, [iolist_to_binary(Run) | Acc]);
merge_initials([H | T], Acc) -> merge_initials(T, [H | Acc]).

take_singles([H | T], Acc) when byte_size(H) =:= 1 -> take_singles(T, [H | Acc]);
take_singles(Rest, Acc) -> {lists:reverse(Acc), Rest}.

%% @doc Drop generic club-type words as long as a name remains.
-spec strip_affixes(binary()) -> binary().
strip_affixes(Base) ->
    Tokens = [T || T <- binary:split(Base, <<" ">>, [global]), T =/= <<>>],
    Stripped = strip_tail(strip_head(Tokens)),
    case Stripped of
        [] -> Base;
        _ -> br_text:join(Stripped, <<" ">>)
    end.

affixes() ->
    [<<"fc">>, <<"ec">>, <<"sc">>, <<"ac">>, <<"cf">>, <<"ca">>, <<"ad">>, <<"cr">>,
     <<"cs">>, <<"ge">>, <<"aa">>, <<"cd">>, <<"se">>, <<"esporte">>, <<"esportiva">>,
     <<"futebol">>, <<"clube">>, <<"club">>, <<"ltda">>, <<"associacao">>, <<"sociedade">>,
     <<"regatas">>, <<"foot">>, <<"ball">>].

strip_head([H | T] = All) ->
    case lists:member(H, affixes()) andalso T =/= [] of
        true -> strip_head(T);
        false -> All
    end;
strip_head([]) -> [].

strip_tail(Tokens) ->
    case lists:reverse(Tokens) of
        [H | T] when T =/= [] ->
            case lists:member(H, affixes()) of
                true -> strip_tail(lists:reverse(T));
                false -> Tokens
            end;
        _ -> Tokens
    end.

generic(Base, undefined, Original) ->
    {br_text:slug(Base), display_of(Original), undefined, undefined};
generic(Base, Region, Original) ->
    Id = <<(br_text:slug(Base))/binary, "-", (br_text:normalize(Region))/binary>>,
    {State, Country} = case lists:member(Region, states()) of
                           true -> {Region, <<"BRA">>};
                           false -> {undefined, Region}
                       end,
    {Id, display_of(Original), State, Country}.

%% Keep the original spelling (accents included) as the display name of
%% clubs that are not in the curated registry.
display_of(Original) ->
    string:trim(br_text:to_binary(Original)).

lookup(Candidates, Region) ->
    case Region of
        undefined -> lookup_strong(Candidates, undefined);
        _ ->
            case lookup_weak(Candidates, Region) of
                {ok, Id} -> {ok, Id};
                error -> lookup_strong(Candidates, Region)
            end
    end.

lookup_weak([], _) -> error;
lookup_weak([C | T], Region) ->
    case maps:find({C, Region}, weak_index()) of
        {ok, Id} -> {ok, Id};
        error -> lookup_weak(T, Region)
    end.

lookup_strong([], _) -> error;
lookup_strong([C | T], Region) ->
    case maps:find(C, strong_index()) of
        {ok, Id} ->
            %% A strong alias only wins when the name carries no region,
            %% or a region that agrees with the registered club.
            case Region =:= undefined orelse Region =:= region(Id) of
                true -> {ok, Id};
                false -> lookup_strong(T, Region)
            end;
        error -> lookup_strong(T, Region)
    end.

%%====================================================================
%% Registry
%%====================================================================

%% {Id, Display, State, Country, StrongAliases, WeakAliases}
%%
%% Strong aliases identify the club on their own.  Weak aliases only do
%% so in combination with the club's state/country.
-spec registry() -> [{binary(), binary(), binary() | undefined, binary(), [string()], [string()]}].
registry() ->
    [%% --- Rio de Janeiro ---
     {<<"flamengo">>, <<"Flamengo">>, <<"RJ">>, <<"BRA">>,
      ["flamengo", "clube de regatas do flamengo", "cr flamengo", "flamengo rj"], []},
     {<<"fluminense">>, <<"Fluminense">>, <<"RJ">>, <<"BRA">>,
      ["fluminense", "fluminense football club"], []},
     {<<"botafogo">>, <<"Botafogo">>, <<"RJ">>, <<"BRA">>,
      ["botafogo", "botafogo de futebol e regatas"], []},
     {<<"vasco">>, <<"Vasco da Gama">>, <<"RJ">>, <<"BRA">>,
      ["vasco", "vasco da gama", "club de regatas vasco da gama"], []},
     %% --- São Paulo ---
     {<<"palmeiras">>, <<"Palmeiras">>, <<"SP">>, <<"BRA">>,
      ["palmeiras", "sociedade esportiva palmeiras", "se palmeiras"], []},
     {<<"corinthians">>, <<"Corinthians">>, <<"SP">>, <<"BRA">>,
      ["corinthians", "corinthians paulista", "sport club corinthians paulista"], []},
     {<<"sao-paulo">>, <<"São Paulo"/utf8>>, <<"SP">>, <<"BRA">>,
      ["sao paulo", "sao paulo futebol clube", "sao paulo fc"], []},
     {<<"santos">>, <<"Santos">>, <<"SP">>, <<"BRA">>,
      ["santos", "santos futebol clube"], []},
     {<<"ponte-preta">>, <<"Ponte Preta">>, <<"SP">>, <<"BRA">>,
      ["ponte preta", "associacao atletica ponte preta"], []},
     {<<"portuguesa">>, <<"Portuguesa">>, <<"SP">>, <<"BRA">>,
      ["portuguesa", "portuguesa desportos", "associacao portuguesa de desportos"], []},
     {<<"red-bull-bragantino">>, <<"Red Bull Bragantino">>, <<"SP">>, <<"BRA">>,
      ["red bull bragantino", "bragantino"], []},
     {<<"guarani">>, <<"Guarani">>, <<"SP">>, <<"BRA">>, ["guarani"], []},
     {<<"sao-caetano">>, <<"São Caetano"/utf8>>, <<"SP">>, <<"BRA">>,
      ["sao caetano", "associacao desportiva sao caetano"], []},
     {<<"santo-andre">>, <<"Santo André"/utf8>>, <<"SP">>, <<"BRA">>, ["santo andre"], []},
     {<<"ituano">>, <<"Ituano">>, <<"SP">>, <<"BRA">>, ["ituano"], []},
     {<<"mirassol">>, <<"Mirassol">>, <<"SP">>, <<"BRA">>, ["mirassol"], []},
     {<<"novorizontino">>, <<"Novorizontino">>, <<"SP">>, <<"BRA">>,
      ["novorizontino", "gremio novorizontino"], []},
     %% --- Minas Gerais ---
     {<<"cruzeiro">>, <<"Cruzeiro">>, <<"MG">>, <<"BRA">>,
      ["cruzeiro", "cruzeiro esporte clube"], []},
     {<<"atletico-mg">>, <<"Atlético Mineiro"/utf8>>, <<"MG">>, <<"BRA">>,
      ["atletico mineiro", "clube atletico mineiro"], ["atletico"]},
     {<<"america-mg">>, <<"América Mineiro"/utf8>>, <<"MG">>, <<"BRA">>,
      ["america mineiro", "america minas gerais", "america fc minas gerais", "america mg"],
      ["america"]},
     {<<"tombense">>, <<"Tombense">>, <<"MG">>, <<"BRA">>, ["tombense"], []},
     {<<"ipatinga">>, <<"Ipatinga">>, <<"MG">>, <<"BRA">>, ["ipatinga"], []},
     %% --- Rio Grande do Sul ---
     {<<"gremio">>, <<"Grêmio"/utf8>>, <<"RS">>, <<"BRA">>,
      ["gremio", "gremio foot ball porto alegrense", "gremio porto alegrense"], []},
     {<<"internacional">>, <<"Internacional">>, <<"RS">>, <<"BRA">>,
      ["internacional", "sport club internacional"], []},
     {<<"juventude">>, <<"Juventude">>, <<"RS">>, <<"BRA">>,
      ["juventude", "esporte clube juventude"], []},
     {<<"caxias">>, <<"Caxias">>, <<"RS">>, <<"BRA">>, ["caxias", "ser caxias"], []},
     %% --- Paraná / Santa Catarina ---
     {<<"athletico-pr">>, <<"Athletico Paranaense">>, <<"PR">>, <<"BRA">>,
      ["athletico", "athletico paranaense", "atletico paranaense",
       "club athletico paranaense"], ["atletico"]},
     {<<"coritiba">>, <<"Coritiba">>, <<"PR">>, <<"BRA">>,
      ["coritiba", "coritiba foot ball club"], []},
     {<<"parana">>, <<"Paraná"/utf8>>, <<"PR">>, <<"BRA">>, ["parana", "parana clube"], []},
     {<<"londrina">>, <<"Londrina">>, <<"PR">>, <<"BRA">>, ["londrina"], []},
     {<<"operario-pr">>, <<"Operário Ferroviário"/utf8>>, <<"PR">>, <<"BRA">>,
      ["operario ferroviario", "operario ferroviario esporte c"], ["operario"]},
     {<<"chapecoense">>, <<"Chapecoense">>, <<"SC">>, <<"BRA">>,
      ["chapecoense", "associacao chapecoense de futebol"], []},
     {<<"figueirense">>, <<"Figueirense">>, <<"SC">>, <<"BRA">>, ["figueirense"], []},
     {<<"avai">>, <<"Avaí"/utf8>>, <<"SC">>, <<"BRA">>, ["avai"], []},
     {<<"criciuma">>, <<"Criciúma"/utf8>>, <<"SC">>, <<"BRA">>, ["criciuma"], []},
     {<<"joinville">>, <<"Joinville">>, <<"SC">>, <<"BRA">>, ["joinville"], []},
     {<<"brusque">>, <<"Brusque">>, <<"SC">>, <<"BRA">>, ["brusque"], []},
     %% --- Nordeste ---
     {<<"bahia">>, <<"Bahia">>, <<"BA">>, <<"BRA">>, ["bahia", "esporte clube bahia"], []},
     {<<"vitoria">>, <<"Vitória"/utf8>>, <<"BA">>, <<"BRA">>,
      ["vitoria", "esporte clube vitoria"], []},
     {<<"sport-recife">>, <<"Sport Recife">>, <<"PE">>, <<"BRA">>,
      ["sport", "sport recife", "sport club do recife", "sport do recife"], []},
     {<<"nautico">>, <<"Náutico"/utf8>>, <<"PE">>, <<"BRA">>,
      ["nautico", "nautico capibaribe", "clube nautico capibaribe"], []},
     {<<"santa-cruz">>, <<"Santa Cruz">>, <<"PE">>, <<"BRA">>,
      ["santa cruz", "santa cruz futebol clube"], []},
     {<<"ceara">>, <<"Ceará"/utf8>>, <<"CE">>, <<"BRA">>,
      ["ceara", "ceara sporting club"], []},
     {<<"fortaleza">>, <<"Fortaleza">>, <<"CE">>, <<"BRA">>,
      ["fortaleza", "fortaleza esporte clube"], []},
     {<<"csa">>, <<"CSA">>, <<"AL">>, <<"BRA">>,
      ["csa", "centro sportivo alagoano", "cs alagoano"], []},
     {<<"crb">>, <<"CRB">>, <<"AL">>, <<"BRA">>,
      ["crb", "clube de regatas brasil"], []},
     {<<"abc">>, <<"ABC">>, <<"RN">>, <<"BRA">>, ["abc"], []},
     {<<"america-rn">>, <<"América de Natal"/utf8>>, <<"RN">>, <<"BRA">>,
      ["america de natal", "america natal", "america fc natal"], ["america"]},
     {<<"sampaio-correa">>, <<"Sampaio Corrêa"/utf8>>, <<"MA">>, <<"BRA">>,
      ["sampaio correa"], []},
     {<<"confianca">>, <<"Confiança"/utf8>>, <<"SE">>, <<"BRA">>, ["confianca"], []},
     {<<"botafogo-pb">>, <<"Botafogo-PB">>, <<"PB">>, <<"BRA">>, [], ["botafogo"]},
     %% --- Norte / Centro-Oeste ---
     {<<"goias">>, <<"Goiás"/utf8>>, <<"GO">>, <<"BRA">>,
      ["goias", "goias esporte clube"], []},
     {<<"atletico-go">>, <<"Atlético Goianiense"/utf8>>, <<"GO">>, <<"BRA">>,
      ["atletico goianiense", "atletico goiania"], ["atletico"]},
     {<<"vila-nova">>, <<"Vila Nova">>, <<"GO">>, <<"BRA">>, ["vila nova"], []},
     {<<"cuiaba">>, <<"Cuiabá"/utf8>>, <<"MT">>, <<"BRA">>, ["cuiaba"], []},
     {<<"brasiliense">>, <<"Brasiliense">>, <<"DF">>, <<"BRA">>, ["brasiliense"], []},
     {<<"gama">>, <<"Gama">>, <<"DF">>, <<"BRA">>, ["gama", "se gama"], []},
     {<<"paysandu">>, <<"Paysandu">>, <<"PA">>, <<"BRA">>, ["paysandu"], []},
     {<<"remo">>, <<"Remo">>, <<"PA">>, <<"BRA">>, ["remo", "clube do remo"], []},
     {<<"manaus">>, <<"Manaus">>, <<"AM">>, <<"BRA">>, ["manaus"], []},
     %% --- CONMEBOL (Libertadores opponents) ---
     {<<"boca-juniors">>, <<"Boca Juniors">>, undefined, <<"ARG">>,
      ["boca juniors", "boca"], []},
     {<<"river-plate">>, <<"River Plate">>, undefined, <<"ARG">>, ["river plate"], []},
     {<<"racing-club">>, <<"Racing Club">>, undefined, <<"ARG">>, ["racing club"], []},
     {<<"independiente">>, <<"Independiente">>, undefined, <<"ARG">>, ["independiente"], []},
     {<<"san-lorenzo">>, <<"San Lorenzo">>, undefined, <<"ARG">>, ["san lorenzo"], []},
     {<<"velez">>, <<"Vélez Sarsfield"/utf8>>, undefined, <<"ARG">>, ["velez sarsfield"], []},
     {<<"penarol">>, <<"Peñarol"/utf8>>, undefined, <<"URU">>, ["penarol"], []},
     {<<"nacional-uru">>, <<"Nacional (URU)">>, undefined, <<"URU">>, [], ["nacional"]},
     {<<"nacional-par">>, <<"Nacional (PAR)">>, undefined, <<"PAR">>, [], ["nacional"]},
     {<<"olimpia">>, <<"Olimpia">>, undefined, <<"PAR">>, ["olimpia"], []},
     {<<"libertad">>, <<"Libertad">>, undefined, <<"PAR">>, ["libertad"], []},
     {<<"cerro-porteno">>, <<"Cerro Porteño"/utf8>>, undefined, <<"PAR">>, ["cerro porteno"], []},
     {<<"guarani-par">>, <<"Guaraní (PAR)"/utf8>>, undefined, <<"PAR">>, [], ["guarani"]},
     {<<"colo-colo">>, <<"Colo-Colo">>, undefined, <<"CHI">>, ["colo colo"], []},
     {<<"universidad-catolica">>, <<"Universidad Católica"/utf8>>, undefined, <<"CHI">>,
      ["universidad catolica"], []},
     {<<"universidad-de-chile">>, <<"Universidad de Chile">>, undefined, <<"CHI">>,
      ["universidad de chile"], []},
     {<<"atletico-nacional">>, <<"Atlético Nacional"/utf8>>, undefined, <<"COL">>,
      ["atletico nacional"], []},
     {<<"millonarios">>, <<"Millonarios">>, undefined, <<"COL">>, ["millonarios"], []},
     {<<"deportivo-cali">>, <<"Deportivo Cali">>, undefined, <<"COL">>, ["deportivo cali"], []},
     {<<"barcelona-equ">>, <<"Barcelona SC (EQU)">>, undefined, <<"EQU">>, [], ["barcelona"]},
     {<<"emelec">>, <<"Emelec">>, undefined, <<"EQU">>, ["emelec"], []},
     {<<"ldu">>, <<"LDU Quito">>, undefined, <<"EQU">>, ["ldu", "ldu quito"], []},
     {<<"independiente-del-valle">>, <<"Independiente del Valle">>, undefined, <<"EQU">>,
      ["independiente del valle"], []},
     {<<"delfin">>, <<"Delfín"/utf8>>, undefined, <<"EQU">>, ["delfin"], []},
     {<<"bolivar">>, <<"Bolívar"/utf8>>, undefined, <<"BOL">>, ["bolivar"], []},
     {<<"the-strongest">>, <<"The Strongest">>, undefined, <<"BOL">>, ["the strongest"], []},
     {<<"sporting-cristal">>, <<"Sporting Cristal">>, undefined, <<"PER">>,
      ["sporting cristal"], []},
     {<<"universitario-per">>, <<"Universitario (PER)">>, undefined, <<"PER">>, [],
      ["universitario"]},
     {<<"alianza-lima">>, <<"Alianza Lima">>, undefined, <<"PER">>, ["alianza lima"], []},
     {<<"caracas">>, <<"Caracas">>, undefined, <<"VEN">>, ["caracas"], []},
     {<<"zamora">>, <<"Zamora">>, undefined, <<"VEN">>, ["zamora"], []},
     {<<"trujillanos">>, <<"Trujillanos">>, undefined, <<"VEN">>, ["trujillanos"], []}].

%%====================================================================
%% Cached indexes
%%====================================================================

by_id() -> index(by_id).
strong_index() -> index(strong).
weak_index() -> index(weak).

index(Which) ->
    Key = {?MODULE, Which},
    try persistent_term:get(Key)
    catch error:badarg ->
            build_indexes(),
            persistent_term:get(Key)
    end.

build_indexes() ->
    Entries = registry(),
    ById = maps:from_list(
             [{Id, #{id => Id, display => Display, state => St, country => Co,
                     strong => [br_text:normalize(A) || A <- Strong],
                     weak => [br_text:normalize(A) || A <- Weak]}}
              || {Id, Display, St, Co, Strong, Weak} <- Entries]),
    Strong = lists:foldl(
               fun({Id, _, _, _, Aliases, _}, Acc) ->
                       lists:foldl(fun(A, M) -> add_alias(A, Id, M) end, Acc, Aliases)
               end, #{}, Entries),
    Weak = lists:foldl(
             fun({Id, _, St, Co, _, Aliases}, Acc) ->
                     Region = case St of undefined -> Co; _ -> St end,
                     lists:foldl(
                       fun(A, M) ->
                               N = br_text:normalize(A),
                               M1 = M#{{N, Region} => Id},
                               M1#{{strip_affixes(N), Region} => Id}
                       end, Acc, Aliases)
             end, #{}, Entries),
    persistent_term:put({?MODULE, by_id}, ById),
    persistent_term:put({?MODULE, strong}, Strong),
    persistent_term:put({?MODULE, weak}, Weak),
    ok.

%% Index both the alias and its affix-stripped form, without letting a
%% stripped form override an explicit alias.
add_alias(Alias, Id, Map) ->
    N = br_text:normalize(Alias),
    Map1 = Map#{N => Id},
    Stripped = strip_affixes(N),
    case maps:is_key(Stripped, Map1) of
        true -> Map1;
        false -> Map1#{Stripped => Id}
    end.
