%% Team-name and date normalization.
-module(brsoccer_norm).
-export([trim/1, ascii/1, tokens/1, team_key/1, team_matches/2, date/1, int/1, display/1]).

-define(STOP, [<<"fc">>, <<"ec">>, <<"sc">>, <<"club">>, <<"clube">>, <<"esporte">>,
               <<"futebol">>, <<"de">>, <<"do">>, <<"da">>, <<"e">>, <<"ac">>,
               <<"cr">>, <<"ca">>, <<"regatas">>, <<"sporting">>, <<"associacao">>]).

%% Lowercase ASCII fold of a UTF-8 binary.
ascii(Bin) when is_binary(Bin) ->
    Chars = case unicode:characters_to_list(Bin) of
                L when is_list(L) -> L;
                _ -> binary_to_list(Bin)
            end,
    list_to_binary([fold(C) || C <- string:lowercase(Chars)]).

fold(C) when C >= 16#E0, C =< 16#E5 -> $a;
fold(C) when C =:= 16#E7 -> $c;
fold(C) when C >= 16#E8, C =< 16#EB -> $e;
fold(C) when C >= 16#EC, C =< 16#EF -> $i;
fold(C) when C =:= 16#F1 -> $n;
fold(C) when C >= 16#F2, C =< 16#F6 -> $o;
fold(C) when C >= 16#F9, C =< 16#FC -> $u;
fold(C) when C < 128 -> C;
fold(_) -> $\s.

%% Significant tokens of a team name, with aliases applied.
tokens(Name) ->
    A = ascii(Name),
    Clean = << <<(case C of X when (X >= $a andalso X =< $z) orelse (X >= $0 andalso X =< $9) -> X; _ -> $\s end)>> || <<C>> <= A >>,
    Toks = [T || T <- binary:split(Clean, <<" ">>, [global, trim_all]), not lists:member(T, ?STOP)],
    aliases(Toks).

aliases([<<"athletico">> | R]) -> aliases([<<"atletico">> | R]);
aliases([<<"atletico">>, <<"mineiro">> | R]) -> [<<"atletico">>, <<"mg">> | R];
aliases([<<"atletico">>, <<"paranaense">> | R]) -> [<<"atletico">>, <<"pr">> | R];
aliases([<<"atletico">>, <<"goianiense">> | R]) -> [<<"atletico">>, <<"go">> | R];
aliases([<<"sport">>, <<"corinthians">> | R]) -> aliases([<<"corinthians">> | R]);
aliases([<<"corinthians">>, <<"paulista">> | R]) -> [<<"corinthians">> | R];
aliases([<<"sport">>, <<"recife">> | R]) -> [<<"sport">>, <<"pe">> | R];
aliases([<<"america">>, <<"minas">>, <<"gerais">> | R]) -> [<<"america">>, <<"mg">> | R];
aliases([<<"red">>, <<"bull">>, <<"bragantino">> | R]) -> [<<"bragantino">> | R];
aliases([<<"vasco">>, <<"gama">> | R]) -> [<<"vasco">> | R];
aliases([<<"ceara">> | R]) -> [<<"ceara">> | R -- [<<"sporting">>]];
aliases(T) -> T.

%% A compact identity key for a team (used for grouping).
team_key(Name) ->
    iolist_to_binary(lists:join(<<" ">>, strip_state(tokens(Name)))).

%% Drop a trailing state code unless it disambiguates (Atletico-MG vs Atletico-PR).
strip_state(T) when length(T) < 2 -> T;
strip_state(T) ->
    Base = lists:droplast(T),
    case is_state(lists:last(T)) andalso not lists:member(Base, [[<<"atletico">>], [<<"america">>]]) of
        true -> Base;
        false -> T
    end.

is_state(T) ->
    lists:member(T, [<<"ac">>,<<"al">>,<<"ap">>,<<"am">>,<<"ba">>,<<"ce">>,<<"df">>,<<"es">>,
                     <<"go">>,<<"ma">>,<<"mt">>,<<"ms">>,<<"mg">>,<<"pa">>,<<"pb">>,<<"pr">>,
                     <<"pe">>,<<"pi">>,<<"rj">>,<<"rn">>,<<"rs">>,<<"ro">>,<<"rr">>,<<"sc">>,
                     <<"sp">>,<<"se">>,<<"to">>]).

%% Does a user query match a team name? All query tokens must appear in the team tokens.
team_matches(Query, Name) ->
    Q = tokens(Query),
    T = tokens(Name),
    Q =/= [] andalso lists:all(fun(X) -> lists:member(X, T) end, Q).

%% Normalize a date to <<"YYYY-MM-DD">>.
date(<<D:2/binary, "/", M:2/binary, "/", Y:4/binary, _/binary>>) -> <<Y/binary, "-", M/binary, "-", D/binary>>;
date(<<Y:4/binary, "-", M:2/binary, "-", D:2/binary, _/binary>>) -> <<Y/binary, "-", M/binary, "-", D/binary>>;
date(Other) -> Other.

int(B) when is_binary(B) ->
    S = trim(B),
    case string:to_integer(S) of
        {I, _} when is_integer(I) -> I;
        _ -> undefined
    end;
int(I) when is_integer(I) -> I.

%% Human display name: drop "-XX" / " - XX" state suffixes.
display(Name) ->
    N = string:trim(Name),
    case re:run(N, <<"^(.*?)\\s*-\\s*[A-Z]{2}$">>, [{capture, [1], binary}, unicode]) of
        {match, [Base]} ->
            case tokens(Base) of
                [<<"atletico">>] -> N;
                [<<"america">>] -> N;
                _ -> Base
            end;
        nomatch -> N
    end.

%% Strip spaces and double quotes from both ends (cheap; avoids string:trim pattern compilation).
trim(<<C, R/binary>>) when C =:= $\s; C =:= $"; C =:= $\t -> trim(R);
trim(B) -> rtrim(B, byte_size(B)).

rtrim(_, 0) -> <<>>;
rtrim(B, N) ->
    case binary:at(B, N - 1) of
        C when C =:= $\s; C =:= $"; C =:= $\t; C =:= $\r -> rtrim(B, N - 1);
        _ -> binary:part(B, 0, N)
    end.
