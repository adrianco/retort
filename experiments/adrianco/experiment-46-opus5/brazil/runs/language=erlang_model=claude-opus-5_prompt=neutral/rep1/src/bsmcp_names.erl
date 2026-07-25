%%%-------------------------------------------------------------------
%%% @doc Team name canonicalisation.
%%%
%%% Context: the same club is written five different ways across the six
%%% datasets - "Atletico-MG", "Atlético - MG", "Atlético Mineiro",
%%% "Atletico Mineiro" (no state), "Clube Atlético Mineiro".  Worse, a
%%% *bare* name can denote different clubs depending on the state:
%%% Botafogo-RJ / Botafogo-SP / Botafogo-PB, América-MG / América-RN,
%%% Internacional-RS / Internacional-SC, Flamengo-RJ / Flamengo-PI.
%%%
%%% Strategy (three steps, all pure functions here; the registry that
%%% needs corpus-wide counts lives in {@link bsmcp_data}):
%%%
%%%   1. `split_state/1' peels a trailing federal-unit or country marker
%%%      ("Palmeiras-SP", "América - MG", "Botafogo RJ", "Nacional (URU)",
%%%      "América FC (Minas Gerais)") and returns {Core, State}.
%%%   2. `strip_club_words/1' + `bsmcp_text:normalize/1' remove legal
%%%      suffixes and abbreviations ("EC", "FC", "Futebol Clube", "Ltda").
%%%   3. `club_alias/2' maps a hand-curated table of well known clubs
%%%      onto one key.  Aliases are *state aware*: "Internacional" with
%%%      no state, or with RS, is the Porto Alegre club; "EC
%%%      Internacional SC" (Lages) is deliberately left alone.
%%%
%%% The result is `{Key, State}'.  Teams whose key appears with more
%%% than one state in the corpus stay separate (Botafogo|RJ vs
%%% Botafogo|SP); the rest merge.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_names).

-export([split_state/1, key/1, resolve/1, club_alias/2, clubs/0,
         is_state/1, state_of_full_name/1, display_core/1]).

%% Brazilian federal units.
-define(STATES, [<<"AC">>, <<"AL">>, <<"AP">>, <<"AM">>, <<"BA">>, <<"CE">>,
                 <<"DF">>, <<"ES">>, <<"GO">>, <<"MA">>, <<"MT">>, <<"MS">>,
                 <<"MG">>, <<"PA">>, <<"PB">>, <<"PR">>, <<"PE">>, <<"PI">>,
                 <<"RJ">>, <<"RN">>, <<"RS">>, <<"RO">>, <<"RR">>, <<"SC">>,
                 <<"SP">>, <<"SE">>, <<"TO">>]).

%% Country markers used by the Libertadores file.
-define(COUNTRIES, [<<"URU">>, <<"PAR">>, <<"ARG">>, <<"EQU">>, <<"PER">>,
                    <<"VEN">>, <<"COL">>, <<"CHI">>, <<"BOL">>, <<"MEX">>,
                    <<"BRA">>, <<"ECU">>, <<"UY">>]).

%% Words that carry no identity ("Esporte Clube Bahia" == "Bahia").
-define(CLUB_WORDS, [<<"fc">>, <<"ec">>, <<"sc">>, <<"ac">>, <<"ad">>,
                     <<"aa">>, <<"se">>, <<"ge">>, <<"ca">>, <<"cs">>,
                     <<"cr">>, <<"ae">>, <<"ce">>, <<"clube">>, <<"club">>,
                     <<"futebol">>, <<"ltda">>, <<"esporte">>, <<"esportes">>,
                     <<"associacao">>, <<"sociedade">>, <<"regatas">>]).

%%====================================================================
%% API
%%====================================================================

%% @doc Full resolution of a raw dataset name to `{Key, State, Core}'.
%% `Core' keeps the original (accented) spelling minus the state marker
%% so it can be used to build a pretty display name.
-spec resolve(binary()) -> {binary(), binary() | undefined, binary()}.
resolve(Raw) ->
    {Core, State} = split_state(Raw),
    BaseKey = key(Core),
    case club_alias(BaseKey, State) of
        {ok, #{key := K, state := S, name := Name}} -> {K, S, Name};
        error -> {BaseKey, State, Core}
    end.

%% @doc Normalised key of a name with the state marker already removed.
-spec key(binary()) -> binary().
key(Core) ->
    Norm = bsmcp_text:normalize(Core),
    case strip_club_words(binary:split(Norm, <<" ">>, [global, trim_all])) of
        [] -> Norm;
        Toks -> bsmcp_text:join(Toks, <<" ">>)
    end.

%% @doc Peel a trailing state / country marker off a raw team name.
-spec split_state(binary()) -> {binary(), binary() | undefined}.
split_state(Raw0) ->
    Raw = string:trim(Raw0),
    case parenthesised(Raw) of
        {ok, Core, State} -> {Core, State};
        error -> dashed_or_spaced(Raw)
    end.

%% @doc Display name candidate: raw core with whitespace collapsed.
-spec display_core(binary()) -> binary().
display_core(Core) ->
    bsmcp_text:join([T || T <- binary:split(string:trim(Core), [<<" ">>, <<"\t">>],
                                            [global, trim_all])], <<" ">>).

-spec is_state(binary()) -> boolean().
is_state(B) -> lists:member(B, ?STATES).

is_country(B) -> lists:member(B, ?COUNTRIES).

%%--------------------------------------------------------------------
%% Curated club table
%%--------------------------------------------------------------------

%% @doc Look up the curated table. A curated entry only applies when the
%% observed state is missing or equal to the club's own state, so that
%% e.g. "Flamengo - PI" never collapses into Flamengo (RJ).
%%
%% One alias may be claimed by several clubs ("Atlético" is MG, PR, GO
%% and AC).  With a state we pick the matching club; without a state we
%% only accept an unambiguous alias.
-spec club_alias(binary(), binary() | undefined) -> {ok, map()} | error.
club_alias(Key, State) ->
    case maps:get(Key, alias_map(), []) of
        [] ->
            error;
        [Club] when State =:= undefined ->
            {ok, Club};
        Clubs when State =:= undefined ->
            %% ambiguous bare alias - fall back to the generic key
            case [C || C = #{key := K} <- Clubs, K =:= Key] of
                [Club] -> {ok, Club};
                _ -> error
            end;
        Clubs ->
            case [C || C = #{state := S} <- Clubs, S =:= State] of
                [Club | _] -> {ok, Club};
                [] -> error
            end
    end.

alias_map() ->
    case persistent_term:get({?MODULE, alias_map}, undefined) of
        undefined ->
            Map = build_alias_map(),
            persistent_term:put({?MODULE, alias_map}, Map),
            Map;
        Map ->
            Map
    end.

build_alias_map() ->
    lists:foldl(
      fun(Club = #{key := K, aliases := Aliases}, Acc) ->
              lists:foldl(fun(A, Acc1) -> add_alias(key(A), Club, Acc1) end,
                          add_alias(K, Club, Acc), Aliases)
      end, #{}, clubs()).

add_alias(Alias, Club = #{key := K}, Map) ->
    Existing = maps:get(Alias, Map, []),
    case lists:any(fun(#{key := K2}) -> K2 =:= K end, Existing) of
        true -> Map;   % several spellings of one club collapse to the same key
        false -> Map#{Alias => Existing ++ [Club]}
    end.

%% @doc Hand-curated identities for the clubs that appear under many
%% spellings.  `aliases' are raw-ish strings; they are normalised with
%% the same pipeline as dataset names before being indexed.
-spec clubs() -> [map()].
clubs() ->
    [c(<<"flamengo">>, <<"Flamengo">>, <<"RJ">>,
       [<<"cr flamengo">>, <<"clube de regatas do flamengo">>]),
     c(<<"fluminense">>, <<"Fluminense">>, <<"RJ">>, [<<"fluminense fc">>]),
     c(<<"botafogo">>, <<"Botafogo">>, <<"RJ">>,
       [<<"botafogo fr">>, <<"botafogo de futebol e regatas">>]),
     c(<<"vasco da gama">>, <<"Vasco da Gama">>, <<"RJ">>,
       [<<"vasco">>, <<"cr vasco da gama">>]),
     c(<<"palmeiras">>, <<"Palmeiras">>, <<"SP">>,
       [<<"se palmeiras">>, <<"sociedade esportiva palmeiras">>]),
     c(<<"corinthians">>, <<"Corinthians">>, <<"SP">>,
       [<<"sc corinthians paulista">>, <<"sport club corinthians paulista">>,
        <<"corinthians paulista">>]),
     c(<<"sao paulo">>, <<"São Paulo"/utf8>>, <<"SP">>,
       [<<"sao paulo fc">>, <<"sao paulo futebol clube">>]),
     c(<<"santos">>, <<"Santos">>, <<"SP">>, [<<"santos fc">>]),
     c(<<"gremio">>, <<"Grêmio"/utf8>>, <<"RS">>,
       [<<"gremio fbpa">>, <<"gremio foot ball porto alegrense">>]),
     c(<<"internacional">>, <<"Internacional">>, <<"RS">>,
       [<<"sc internacional">>, <<"inter">>]),
     c(<<"cruzeiro">>, <<"Cruzeiro">>, <<"MG">>, [<<"cruzeiro ec">>]),
     c(<<"atletico mineiro">>, <<"Atlético Mineiro"/utf8>>, <<"MG">>,
       [<<"atletico">>, <<"clube atletico mineiro">>, <<"atletico mg">>]),
     c(<<"america mineiro">>, <<"América Mineiro"/utf8>>, <<"MG">>,
       [<<"america">>, <<"america fc minas gerais">>, <<"america minas gerais">>]),
     c(<<"athletico paranaense">>, <<"Athletico Paranaense">>, <<"PR">>,
       [<<"athletico">>, <<"atletico">>, <<"atletico paranaense">>,
        <<"club athletico paranaense">>]),
     c(<<"atletico goianiense">>, <<"Atlético Goianiense"/utf8>>, <<"GO">>,
       [<<"atletico">>, <<"atletico go">>]),
     c(<<"atletico acreano">>, <<"Atlético Acreano"/utf8>>, <<"AC">>, [<<"atletico">>]),
     c(<<"coritiba">>, <<"Coritiba">>, <<"PR">>, [<<"coritiba fbc">>]),
     c(<<"parana">>, <<"Paraná"/utf8>>, <<"PR">>, [<<"parana clube">>, <<"ca parana">>]),
     c(<<"bahia">>, <<"Bahia">>, <<"BA">>, [<<"ec bahia">>, <<"esporte clube bahia">>]),
     c(<<"vitoria">>, <<"Vitória"/utf8>>, <<"BA">>, [<<"ec vitoria">>, <<"vitoria ec">>]),
     c(<<"sport">>, <<"Sport Recife">>, <<"PE">>,
       [<<"sport recife">>, <<"sport club do recife">>, <<"sport do recife">>]),
     c(<<"nautico">>, <<"Náutico"/utf8>>, <<"PE">>,
       [<<"nautico capibaribe">>, <<"clube nautico capibaribe">>]),
     c(<<"santa cruz">>, <<"Santa Cruz">>, <<"PE">>, [<<"santa cruz fc">>]),
     c(<<"ceara">>, <<"Ceará"/utf8>>, <<"CE">>,
       [<<"ceara sc">>, <<"ceara sporting club">>, <<"ceara sporting">>]),
     c(<<"fortaleza">>, <<"Fortaleza">>, <<"CE">>,
       [<<"fortaleza ec">>, <<"fortaleza esporte clube">>, <<"fortaleza fc">>]),
     c(<<"goias">>, <<"Goiás"/utf8>>, <<"GO">>, [<<"goias ec">>]),
     c(<<"vila nova">>, <<"Vila Nova">>, <<"GO">>, [<<"vila nova fc">>]),
     c(<<"chapecoense">>, <<"Chapecoense">>, <<"SC">>,
       [<<"associacao chapecoense de futebol">>]),
     c(<<"figueirense">>, <<"Figueirense">>, <<"SC">>, []),
     c(<<"avai">>, <<"Avaí"/utf8>>, <<"SC">>, []),
     c(<<"criciuma">>, <<"Criciúma"/utf8>>, <<"SC">>, []),
     c(<<"joinville">>, <<"Joinville">>, <<"SC">>, [<<"joinville ec">>]),
     c(<<"juventude">>, <<"Juventude">>, <<"RS">>, [<<"ec juventude">>]),
     c(<<"csa">>, <<"CSA">>, <<"AL">>,
       [<<"cs alagoano">>, <<"centro sportivo alagoano">>]),
     c(<<"crb">>, <<"CRB">>, <<"AL">>, [<<"clube de regatas brasil">>]),
     c(<<"cuiaba">>, <<"Cuiabá"/utf8>>, <<"MT">>, [<<"cuiaba ec">>]),
     c(<<"red bull bragantino">>, <<"Red Bull Bragantino">>, <<"SP">>,
       [<<"bragantino">>, <<"rb bragantino">>]),
     c(<<"ponte preta">>, <<"Ponte Preta">>, <<"SP">>, [<<"aa ponte preta">>]),
     c(<<"portuguesa">>, <<"Portuguesa">>, <<"SP">>,
       [<<"portuguesa desportos">>, <<"associacao portuguesa de desportos">>]),
     c(<<"guarani">>, <<"Guarani">>, <<"SP">>, [<<"guarani fc">>]),
     c(<<"sao caetano">>, <<"São Caetano"/utf8>>, <<"SP">>, [<<"ad sao caetano">>]),
     c(<<"santo andre">>, <<"Santo André"/utf8>>, <<"SP">>, [<<"ec santo andre">>]),
     c(<<"oeste">>, <<"Oeste">>, <<"SP">>, []),
     c(<<"ituano">>, <<"Ituano">>, <<"SP">>, []),
     c(<<"mirassol">>, <<"Mirassol">>, <<"SP">>, []),
     c(<<"novorizontino">>, <<"Novorizontino">>, <<"SP">>,
       [<<"gremio novorizontino">>]),
     c(<<"paysandu">>, <<"Paysandu">>, <<"PA">>, [<<"paysandu sc">>]),
     c(<<"remo">>, <<"Remo">>, <<"PA">>, [<<"clube do remo">>]),
     c(<<"abc">>, <<"ABC">>, <<"RN">>, [<<"abc fc">>]),
     c(<<"america rn">>, <<"América de Natal"/utf8>>, <<"RN">>,
       [<<"america de natal">>, <<"america fc natal">>, <<"america natal">>]),
     c(<<"sampaio correa">>, <<"Sampaio Corrêa"/utf8>>, <<"MA">>, []),
     c(<<"brasiliense">>, <<"Brasiliense">>, <<"DF">>, [<<"brasiliense fc">>]),
     c(<<"gama">>, <<"Gama">>, <<"DF">>, [<<"se gama">>]),
     c(<<"londrina">>, <<"Londrina">>, <<"PR">>, [<<"londrina ec">>]),
     c(<<"operario">>, <<"Operário Ferroviário"/utf8>>, <<"PR">>,
       [<<"operario ferroviario esporte c">>, <<"operario ferroviario">>]),
     c(<<"tombense">>, <<"Tombense">>, <<"MG">>, []),
     c(<<"tupi">>, <<"Tupi">>, <<"MG">>, []),
     c(<<"caldense">>, <<"Caldense">>, <<"MG">>, []),
     c(<<"urt">>, <<"URT">>, <<"MG">>, []),
     c(<<"uberlandia">>, <<"Uberlândia"/utf8>>, <<"MG">>, []),
     c(<<"villa nova">>, <<"Villa Nova">>, <<"MG">>, []),
     c(<<"confianca">>, <<"Confiança"/utf8>>, <<"SE">>, [<<"ad confianca">>]),
     c(<<"sergipe">>, <<"Sergipe">>, <<"SE">>, [<<"cs sergipe">>]),
     c(<<"treze">>, <<"Treze">>, <<"PB">>, []),
     c(<<"campinense">>, <<"Campinense">>, <<"PB">>, [<<"campinense clube">>]),
     c(<<"manaus">>, <<"Manaus">>, <<"AM">>, [<<"manaus fc">>]),
     c(<<"nacional am">>, <<"Nacional">>, <<"AM">>, []),
     c(<<"volta redonda">>, <<"Volta Redonda">>, <<"RJ">>, []),
     c(<<"madureira">>, <<"Madureira">>, <<"RJ">>, [<<"madureira ec">>]),
     c(<<"boavista">>, <<"Boavista">>, <<"RJ">>,
       [<<"boavista sc saquarema">>,
        <<"boavista sport club antigo esporte clube barreira">>]),
     c(<<"resende">>, <<"Resende">>, <<"RJ">>, []),
     c(<<"caxias">>, <<"Caxias">>, <<"RS">>, [<<"ser caxias">>]),
     c(<<"ypiranga rs">>, <<"Ypiranga">>, <<"RS">>, []),
     c(<<"brasil de pelotas">>, <<"Brasil de Pelotas">>, <<"RS">>,
       [<<"brasil pelotas">>]),
     c(<<"luverdense">>, <<"Luverdense">>, <<"MT">>, []),
     c(<<"altos">>, <<"Altos">>, <<"PI">>, [<<"ae altos">>]),
     c(<<"parnahyba">>, <<"Parnahyba">>, <<"PI">>, [<<"parnahyba sc">>]),
     c(<<"salgueiro">>, <<"Salgueiro">>, <<"PE">>, []),
     c(<<"asa">>, <<"ASA">>, <<"AL">>, [<<"asa arapiraca">>]),
     c(<<"juazeirense">>, <<"Juazeirense">>, <<"BA">>, []),
     c(<<"jacuipense">>, <<"Jacuipense">>, <<"BA">>, []),
     c(<<"ferroviario">>, <<"Ferroviário"/utf8>>, <<"CE">>, []),
     c(<<"floresta">>, <<"Floresta">>, <<"CE">>, [<<"floresta ec">>]),
     c(<<"icasa">>, <<"Icasa">>, <<"CE">>, []),
     c(<<"brusque">>, <<"Brusque">>, <<"SC">>, []),
     c(<<"marcilio dias">>, <<"Marcílio Dias"/utf8>>, <<"SC">>, [])].

c(Key, Name, State, Aliases) ->
    #{key => Key, name => Name, state => State, aliases => Aliases}.

%%====================================================================
%% Internals
%%====================================================================

%% "Nacional (URU)" | "América FC (Minas Gerais)" | "River (PI)"
parenthesised(Raw) ->
    Size = byte_size(Raw),
    case Size > 3 andalso binary:at(Raw, Size - 1) =:= $) of
        false ->
            error;
        true ->
            case binary:matches(Raw, <<"(">>) of
                [] -> error;
                Matches ->
                    {Open, 1} = lists:last(Matches),
                    Inner = binary:part(Raw, Open + 1, Size - Open - 2),
                    Core = string:trim(binary:part(Raw, 0, Open)),
                    case marker(Inner, spelled_out) of
                        {ok, State} -> {ok, Core, State};
                        error -> error
                    end
            end
    end.

%% "Palmeiras-SP" | "América - MG" | "Botafogo RJ" | "Barcelona-EQU"
dashed_or_spaced(Raw) ->
    case split_last(Raw, [<<" - ">>, <<"-">>, <<" ">>]) of
        {Core, Tail} ->
            case marker(Tail, abbreviation) of
                {ok, State} ->
                    Core1 = string:trim(Core, trailing, " -"),
                    case Core1 of
                        <<>> -> {Raw, undefined};
                        _ -> {Core1, State}
                    end;
                error ->
                    {Raw, undefined}
            end;
        error ->
            {Raw, undefined}
    end.

split_last(Bin, Seps) ->
    Candidates = [{Pos, Len} || Sep <- Seps,
                                {Pos, Len} <- last_match(Bin, Sep)],
    case Candidates of
        [] -> error;
        _ ->
            {Pos, Len} = lists:last(lists:sort(Candidates)),
            {binary:part(Bin, 0, Pos),
             binary:part(Bin, Pos + Len, byte_size(Bin) - Pos - Len)}
    end.

last_match(Bin, Sep) ->
    case binary:matches(Bin, Sep) of
        [] -> [];
        L -> [lists:last(L)]
    end.

%% Is this trailing token a federal unit / country marker?  Spelled out
%% state names ("Minas Gerais") are only accepted inside parentheses -
%% a trailing bare word must not be eaten, or "EC Bahia" would become
%% the club "EC" in state BA.
marker(Tail0, Mode) ->
    Tail = string:trim(Tail0),
    Upper = string:uppercase(bsmcp_text:fold_accents(Tail)),
    Clean = << <<C>> || <<C>> <= Upper, C >= $A, C =< $Z >>,
    case Clean of
        <<>> ->
            error;
        _ ->
            case is_state(Clean) andalso byte_size(Tail) =< 3 of
                true ->
                    {ok, Clean};
                false ->
                    case is_country(Clean) andalso byte_size(Tail) =< 4 of
                        true -> {ok, Clean};
                        false when Mode =:= spelled_out -> state_of_full_name(Tail);
                        false -> error
                    end
            end
    end.

%% "Minas Gerais" -> {ok, <<"MG">>}
-spec state_of_full_name(binary()) -> {ok, binary()} | error.
state_of_full_name(Name) ->
    case maps:find(bsmcp_text:normalize(Name), full_state_names()) of
        {ok, UF} -> {ok, UF};
        error -> error
    end.

full_state_names() ->
    #{<<"acre">> => <<"AC">>, <<"alagoas">> => <<"AL">>,
      <<"amapa">> => <<"AP">>, <<"amazonas">> => <<"AM">>,
      <<"bahia">> => <<"BA">>, <<"ceara">> => <<"CE">>,
      <<"distrito federal">> => <<"DF">>, <<"espirito santo">> => <<"ES">>,
      <<"goias">> => <<"GO">>, <<"maranhao">> => <<"MA">>,
      <<"mato grosso">> => <<"MT">>, <<"mato grosso sul">> => <<"MS">>,
      <<"minas gerais">> => <<"MG">>, <<"para">> => <<"PA">>,
      <<"paraiba">> => <<"PB">>, <<"parana">> => <<"PR">>,
      <<"pernambuco">> => <<"PE">>, <<"piaui">> => <<"PI">>,
      <<"rio janeiro">> => <<"RJ">>, <<"rio grande norte">> => <<"RN">>,
      <<"rio grande sul">> => <<"RS">>, <<"rondonia">> => <<"RO">>,
      <<"roraima">> => <<"RR">>, <<"santa catarina">> => <<"SC">>,
      <<"sao paulo">> => <<"SP">>, <<"sergipe">> => <<"SE">>,
      <<"tocantins">> => <<"TO">>}.

%% Drop legal-form words, but never everything (a name like "Sport" or
%% "CSA" must survive intact).
strip_club_words(Toks) ->
    Kept = [T || T <- Toks, not lists:member(T, ?CLUB_WORDS)],
    case Kept of
        [] -> Toks;
        _ -> Kept
    end.
