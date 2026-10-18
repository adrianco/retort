%% @doc Team name normalisation. Raw names come in many shapes:
%%   "Palmeiras-SP", "Boavista Sport Club (antigo ...) - RJ", "Nacional (URU)",
%%   "Sport Club Corinthians Paulista", "Grêmio", "Athletico-PR".
%% A team is #{name, base, state}: `name' is the display name, `base' is the
%% folded key used for matching, and `state' is the state/country code or <<>>.
-module(bsm_team).
-export([parse/1, parse/2, same/2, key/1]).

-define(STOP_WORDS, [<<"ec">>, <<"fc">>, <<"sc">>, <<"ac">>, <<"ca">>, <<"cr">>, <<"se">>,
                     <<"ad">>, <<"club">>, <<"clube">>, <<"esporte">>, <<"esportiva">>,
                     <<"sociedade">>, <<"futebol">>, <<"de">>, <<"do">>, <<"da">>]).

-define(UFS, [<<"AC">>, <<"AL">>, <<"AP">>, <<"AM">>, <<"BA">>, <<"CE">>, <<"DF">>, <<"ES">>,
              <<"GO">>, <<"MA">>, <<"MT">>, <<"MS">>, <<"MG">>, <<"PA">>, <<"PB">>, <<"PR">>,
              <<"PE">>, <<"PI">>, <<"RJ">>, <<"RN">>, <<"RS">>, <<"RO">>, <<"RR">>, <<"SC">>,
              <<"SP">>, <<"SE">>, <<"TO">>]).

-type team() :: #{name := binary(), base := binary(), state := binary()}.
-export_type([team/0]).

-spec parse(binary()) -> team().
parse(Raw) -> parse(Raw, <<>>).

%% @doc `StateHint' is used when the name carries no suffix (separate state column).
-spec parse(binary(), binary()) -> team().
parse(Raw, StateHint) ->
    NoParens = re:replace(Raw, <<"\\s*\\([^)]*\\)">>, <<>>, [global, {return, binary}]),
    {Name, Suffix} = split_suffix(bsm_text:trim(NoParens)),
    {Base, AliasState} = team_alias(canonical(bsm_text:fold(Name))),
    State = case valid_state(upper(Suffix)) of
                <<>> -> case valid_state(upper(StateHint)) of
                            <<>> -> AliasState;
                            Hint -> Hint
                        end;
                S -> S
            end,
    #{name => Name, base => Base, state => State}.

%% @doc Two teams are the same when their bases match and their states do not
%% conflict. An unknown state (<<>>) is compatible with anything, so the query
%% "Flamengo" matches "Flamengo-RJ" but "Atletico-MG" never matches "Atletico-PR".
-spec same(team(), team()) -> boolean().
same(#{base := B, state := S1}, #{base := B, state := S2}) ->
    S1 =:= <<>> orelse S2 =:= <<>> orelse S1 =:= S2;
same(_, _) ->
    false.

-spec key(team()) -> {binary(), binary()}.
key(#{base := B, state := S}) -> {B, S}.

%% "Palmeiras-SP", "Copa: Sport - PE" and "Botafogo RJ" all carry a state.
%% The space form is only trusted for upper-case two-letter codes that are
%% not club-name abbreviations such as "FC".
split_suffix(Clean) ->
    case re:run(Clean, <<"^(.*?)\\s*-\\s*([A-Za-z]{2,3})$">>, [{capture, all_but_first, binary}]) of
        {match, [Name, Suffix]} -> {bsm_text:trim(Name), Suffix};
        nomatch -> split_space_suffix(Clean)
    end.

split_space_suffix(Clean) ->
    case re:run(Clean, <<"^(.*\\S)\\s+([A-Z]{2})$">>, [{capture, all_but_first, binary}]) of
        {match, [Name, Suffix]} ->
            case lists:member(Suffix, [<<"FC">>, <<"EC">>, <<"SC">>, <<"AC">>, <<"CA">>, <<"CR">>, <<"SE">>, <<"AD">>]) of
                true -> {Clean, <<>>};
                false -> {Name, Suffix}
            end;
        nomatch -> {Clean, <<>>}
    end.

%% Club abbreviations that appear at the start or end of names in some feeds
%% ("EC Bahia", "Fortaleza FC") and do not identify the club.
canonical(Fold) ->
    Words = binary:split(Fold, <<" ">>, [global, trim_all]),
    Trimmed = lists:reverse(drop_stop(lists:reverse(drop_stop(Words)))),
    iolist_to_binary(lists:join(<<" ">>, Trimmed)).

drop_stop([W | Rest]) ->
    case lists:member(W, ?STOP_WORDS) of
        true -> drop_stop(Rest);
        false -> [W | Rest]
    end;
drop_stop([]) -> [].

%% Known full-name variants that should resolve to the short name used elsewhere.
team_alias(<<"sport club corinthians paulista">>) -> {<<"corinthians">>, <<>>};
team_alias(<<"sociedade esportiva palmeiras">>) -> {<<"palmeiras">>, <<>>};
team_alias(<<"clube de regatas do flamengo">>) -> {<<"flamengo">>, <<>>};
team_alias(<<"athletico paranaense">>) -> {<<"atletico">>, <<"PR">>};
team_alias(<<"atletico paranaense">>) -> {<<"atletico">>, <<"PR">>};
team_alias(<<"athletico">>) -> {<<"atletico">>, <<"PR">>};
team_alias(<<"atletico mineiro">>) -> {<<"atletico">>, <<"MG">>};
team_alias(<<"atletico goianiense">>) -> {<<"atletico">>, <<"GO">>};
team_alias(<<"sport recife">>) -> {<<"sport">>, <<"PE">>};
team_alias(<<"vasco da gama">>) -> {<<"vasco">>, <<"RJ">>};
team_alias(<<"gremio foot ball porto alegrense">>) -> {<<"gremio">>, <<"RS">>};
team_alias(<<"sport club internacional">>) -> {<<"internacional">>, <<"RS">>};
team_alias(Fold) -> {Fold, <<>>}.

%% Two-letter codes must be real Brazilian UFs (the novo_campeonato file has
%% "BH" for Bahia). Three-letter codes are country codes from Libertadores.
valid_state(<<>>) -> <<>>;
valid_state(S) when byte_size(S) =:= 3 -> S;
valid_state(S) when byte_size(S) =:= 2 ->
    case lists:member(S, ?UFS) of
        true -> S;
        false -> <<>>
    end;
valid_state(_) -> <<>>.

upper(<<>>) -> <<>>;
upper(B) -> list_to_binary(string:uppercase(binary_to_list(B))).
