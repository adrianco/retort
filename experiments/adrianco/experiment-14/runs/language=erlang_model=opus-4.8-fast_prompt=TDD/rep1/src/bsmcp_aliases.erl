%% @doc Canonical team aliases.
%%
%% Maps the surface spellings that plain suffix-stripping gets wrong onto a
%% single canonical key. Keys are already lowercased, accent-free and
%% hyphen-tightened by {@link bsmcp_normalize}. Two problems are solved:
%%
%%   1. Ambiguous state suffixes — Atlético-MG/-GO/-PR and América-MG/-RN
%%      would all collapse to "atletico"/"america" if the suffix were
%%      stripped, so their canonical key keeps the state code.
%%   2. Full-name spellings from BR-Football ("Atletico Mineiro",
%%      "EC Bahia", "Vasco Da Gama RJ") are folded onto the suffixed key.
-module(bsmcp_aliases).

-export([lookup/1]).

%% @doc Return `{ok, Canonical}' if Name is a known alias, else `error'.
-spec lookup(binary()) -> {ok, binary()} | error.
lookup(Name) ->
    maps:find(Name, table()).

table() ->
    expand(
      [{<<"atletico-mg">>, [<<"atletico-mg">>, <<"atletico mineiro">>]},
       {<<"atletico-go">>, [<<"atletico-go">>, <<"atletico goianiense">>]},
       {<<"athletico-pr">>, [<<"athletico-pr">>, <<"atletico-pr">>,
                             <<"atletico paranaense">>, <<"athletico paranaense">>]},
       {<<"america-mg">>, [<<"america-mg">>, <<"america mg">>]},
       {<<"america-rn">>, [<<"america-rn">>, <<"america rn">>]},
       {<<"vasco">>, [<<"vasco da gama">>, <<"vasco da gama rj">>]},
       {<<"bahia">>, [<<"ec bahia">>]},
       {<<"fortaleza">>, [<<"fortaleza fc">>]},
       {<<"sport">>, [<<"sport recife">>]},
       {<<"juventude">>, [<<"ec juventude">>]},
       {<<"santa cruz">>, [<<"santa cruz fc">>]},
       {<<"botafogo">>, [<<"botafogo rj">>]},
       {<<"bragantino">>, [<<"red bull bragantino">>, <<"rb bragantino">>]}]).

%% Flatten {Canon, Variants} pairs into a variant -> Canon map.
expand(Pairs) ->
    lists:foldl(
      fun({Canon, Variants}, Acc) ->
              lists:foldl(fun(V, A) -> A#{V => Canon} end, Acc, Variants)
      end, #{}, Pairs).
