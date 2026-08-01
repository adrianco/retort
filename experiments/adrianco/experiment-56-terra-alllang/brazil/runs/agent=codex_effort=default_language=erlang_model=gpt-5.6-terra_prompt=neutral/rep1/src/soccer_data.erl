%% coding: utf-8
-module(soccer_data).
-export([load/0, load/1, clear/0, matches/0, players/0, normalize_team/1]).

-define(MATCHES, soccer_matches).
-define(PLAYERS, soccer_players).

load() -> load("data/kaggle").
load(Dir) ->
    clear(), ets:new(?MATCHES, [named_table, public, set]), ets:new(?PLAYERS, [named_table, public, set]),
    MatchFiles = [{"Brasileirao_Matches.csv", <<"Brasileirao">>},
                  {"Brazilian_Cup_Matches.csv", <<"Copa do Brasil">>},
                  {"Libertadores_Matches.csv", <<"Libertadores">>},
                  {"BR-Football-Dataset.csv", <<"Extended">>},
                  {"novo_campeonato_brasileiro.csv", <<"Brasileirao">>}],
    lists:foreach(fun({F, C}) -> load_matches(filename:join(Dir, F), C) end, MatchFiles),
    load_players(filename:join(Dir, "fifa_data.csv")), ok.

clear() ->
    lists:foreach(fun(T) -> case ets:info(T) of undefined -> ok; _ -> ets:delete(T) end end,
                  [?MATCHES, ?PLAYERS]), ok.
matches() -> [M || {_, M} <- ets:tab2list(?MATCHES)].
players() -> [P || {_, P} <- ets:tab2list(?PLAYERS)].

load_matches(File, Competition) ->
    case soccer_csv:read(File) of
        {ok, H, Rows} -> lists:foreach(fun(R) ->
            V = row(H, R), M = match(V, Competition),
            case maps:get(home, M, <<>>) of <<>> -> ok; _ -> ets:insert(?MATCHES, {erlang:unique_integer([positive]), M}) end
        end, Rows);
        _ -> ok
    end.
match(V, DefaultCompetition) ->
    Home = field(V, [<<"home_team">>, <<"home">>, <<"Equipe_mandante">>]),
    Away = field(V, [<<"away_team">>, <<"away">>, <<"Equipe_visitante">>]),
    Date = field(V, [<<"datetime">>, <<"date">>, <<"Data">>]),
    Season0 = field(V, [<<"season">>, <<"Ano">>]),
    #{home => Home, away => Away, home_key => normalize_team(Home), away_key => normalize_team(Away),
      home_goals => integer(field(V, [<<"home_goal">>, <<"Gols_mandante">>])),
      away_goals => integer(field(V, [<<"away_goal">>, <<"Gols_visitante">>])), date => normalize_date(Date),
      season => season(Season0, Date), competition => case field(V, [<<"tournament">>]) of <<>> -> DefaultCompetition; X -> X end,
      round => field(V, [<<"round">>, <<"Rodada">>, <<"stage">>]), stadium => field(V, [<<"Arena">>])}.
load_players(File) ->
    case soccer_csv:read(File) of
        {ok, H, Rows} -> lists:foreach(fun(R) -> V = row(H, R), Name = field(V, [<<"Name">>]),
            case Name of <<>> -> ok; _ -> ets:insert(?PLAYERS, {erlang:unique_integer([positive]),
              #{name => Name, name_key => lower(Name), nationality => field(V,[<<"Nationality">>]), club => field(V,[<<"Club">>]),
                position => field(V,[<<"Position">>]), overall => integer(field(V,[<<"Overall">>])), potential => integer(field(V,[<<"Potential">>])), age => integer(field(V,[<<"Age">>]))}}) end
        end, Rows);
        _ -> ok
    end.
row(H, R) -> maps:from_list(lists:zip([strip_bom(X) || X <- H], R)).
strip_bom(<<239,187,191, Rest/binary>>) -> Rest; strip_bom(X) -> X.
field(M, Keys) -> lists:foldl(fun(K, Acc) -> case Acc of <<>> -> maps:get(K, M, <<>>); _ -> Acc end end, <<>>, Keys).
integer(<<>>) -> 0; integer(B) -> try binary_to_integer(B) catch _:_ -> 0 end.
season(<<>>, Date) -> case Date of <<Y:4/binary, _/binary>> -> integer(Y); _ -> 0 end; season(B, _) -> integer(B).
normalize_date(<<D:2/binary, $/, M:2/binary, $/, Y:4/binary, _/binary>>) -> <<Y/binary, $-, M/binary, $-, D/binary>>;
normalize_date(<<Y:4/binary, $-, M:2/binary, $-, D:2/binary, _/binary>>) -> <<Y/binary, $-, M/binary, $-, D/binary>>;
normalize_date(X) -> X.
normalize_team(Value) ->
    Lower = ascii(lower(Value)), NoState = re:replace(Lower, <<"-[a-z]{2}$">>, <<>>, [{return,binary}]),
    Key = re:replace(NoState, <<"[^a-z0-9]">>, <<>>, [global, {return,binary}]),
    aliases(Key).
aliases(<<"sportclubcorinthianspaulista">>) -> <<"corinthians">>;
aliases(<<"clubederegatasdoflamengo">>) -> <<"flamengo">>;
aliases(<<"saopaulofutebolclube">>) -> <<"saopaulo">>;
aliases(<<"sociedadeesportivapalmeiras">>) -> <<"palmeiras">>;
aliases(<<"fluminensefootballclub">>) -> <<"fluminense">>;
aliases(Key) -> Key.
ascii(B) -> lists:foldl(fun({From,To}, Acc) -> binary:replace(Acc, From, To, [global]) end, B,
    [{<<195,161>>,<<"a">>},{<<195,160>>,<<"a">>},{<<195,163>>,<<"a">>},{<<195,162>>,<<"a">>},{<<195,169>>,<<"e">>},{<<195,170>>,<<"e">>},{<<195,173>>,<<"i">>},{<<195,179>>,<<"o">>},{<<195,180>>,<<"o">>},{<<195,181>>,<<"o">>},{<<195,186>>,<<"u">>},{<<195,167>>,<<"c">>}]).
lower(B) when is_binary(B) ->
    Chars = case unicode:characters_to_list(B, utf8) of
        L when is_list(L) -> L;
        {error, _, _} -> unicode:characters_to_list(B, latin1)
    end,
    unicode:characters_to_binary(string:lowercase(Chars)).
