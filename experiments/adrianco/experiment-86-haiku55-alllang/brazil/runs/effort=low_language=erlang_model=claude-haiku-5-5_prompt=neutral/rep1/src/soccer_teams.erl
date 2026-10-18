%% Context: resolves the club name variants used across the six files to one
%% canonical display name. Keys keep state suffixes, so Atlético-MG and
%% Athletico-PR stay distinct even though both are "Atletico" once suffixes are
%% stripped. Names not listed here fall back to the suffix-stripped name.
-module(soccer_teams).
-export([resolve/1]).

-define(INDEX_KEY, {?MODULE, index}).

%% {Canonical display name, [variant spellings seen in the data]}
-define(CLUBS, [
    {<<"Atlético-MG"/utf8>>, [<<"Atletico-MG">>, <<"Atletico Mineiro">>]},
    {<<"Athletico-PR"/utf8>>, [<<"Atletico-PR">>, <<"Athletico Paranaense">>,
                               <<"Atletico Paranaense">>]},
    {<<"Grêmio"/utf8>>, [<<"Gremio-RS">>, <<"Gremio">>]},
    {<<"Internacional">>, [<<"Internacional-RS">>]},
    {<<"Flamengo">>, [<<"Flamengo-RJ">>]},
    {<<"Fluminense">>, [<<"Fluminense-RJ">>]},
    {<<"Botafogo">>, [<<"Botafogo-RJ">>, <<"Botafogo RJ">>]},
    {<<"Vasco da Gama">>, [<<"Vasco">>, <<"Vasco da Gama-RJ">>, <<"Vasco Da Gama RJ">>]},
    {<<"Corinthians">>, [<<"Corinthians-SP">>]},
    {<<"Palmeiras">>, [<<"Palmeiras-SP">>]},
    {<<"Santos">>, [<<"Santos-SP">>]},
    {<<"São Paulo"/utf8>>, [<<"Sao Paulo-SP">>]},
    {<<"Cruzeiro">>, [<<"Cruzeiro-MG">>]},
    {<<"Coritiba">>, [<<"Coritiba-PR">>]},
    {<<"Figueirense">>, [<<"Figueirense-SC">>]},
    {<<"Chapecoense">>, [<<"Chapecoense-SC">>]},
    {<<"Goiás"/utf8>>, [<<"Goias-GO">>, <<"Goias">>]},
    {<<"Ponte Preta">>, [<<"Ponte Preta-SP">>]},
    {<<"Vitória"/utf8>>, [<<"Vitoria-BA">>, <<"Vitoria">>]},
    {<<"Sport">>, [<<"Sport-PE">>, <<"Sport Recife">>, <<"Sport Club do Recife">>]},
    {<<"Bahia">>, [<<"Bahia-BA">>, <<"EC Bahia">>]},
    {<<"Avaí"/utf8>>, [<<"Avai-SC">>, <<"Avai">>]},
    {<<"Atlético-GO"/utf8>>, [<<"Atletico-GO">>, <<"Atletico Goianiense">>]},
    {<<"Ceará"/utf8>>, [<<"Ceara-CE">>, <<"Ceara">>]},
    {<<"Náutico"/utf8>>, [<<"Nautico">>]},
    {<<"Fortaleza">>, [<<"Fortaleza-CE">>, <<"Fortaleza FC">>, <<"Fortaleza EC">>]},
    {<<"América-MG"/utf8>>, [<<"America-MG">>, <<"America MG">>]},
    {<<"Criciúma"/utf8>>, [<<"Criciuma-SC">>]},
    {<<"CSA">>, [<<"CSA-AL">>, <<"Csa-AL">>]}
]).

%% Returns {DisplayName, MatchTokens}. MatchTokens is every token from every
%% spelling of the club, so "Atletico Mineiro" and "Atletico-MG" both match.
-spec resolve(binary()) -> {binary(), [binary()]}.
resolve(Raw) ->
    case maps:get(soccer_util:tokens(Raw), index(), undefined) of
        undefined ->
            Display = soccer_util:team_name(Raw),
            {Display, soccer_util:tokens(Display)};
        Entry ->
            Entry
    end.

index() ->
    case persistent_term:get(?INDEX_KEY, undefined) of
        undefined ->
            Index = build_index(),
            persistent_term:put(?INDEX_KEY, Index),
            Index;
        Index ->
            Index
    end.

build_index() ->
    maps:from_list(
      lists:append(
        [begin
             Tokens = lists:usort(lists:append([soccer_util:tokens(V) || V <- [Canonical | Variants]])),
             [{soccer_util:tokens(V), {Canonical, Tokens}} || V <- [Canonical | Variants]]
         end
         || {Canonical, Variants} <- ?CLUBS])).
