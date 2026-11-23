-module(soccer_data).
-export([load/1, team/1, fold/1, date/1, competition/1]).

files() -> [{league,"Brasileirao_Matches.csv"}, {history,"novo_campeonato_brasileiro.csv"},
            {cup,"Brazilian_Cup_Matches.csv"}, {lib,"Libertadores_Matches.csv"},
            {extended,"BR-Football-Dataset.csv"}].

load(Dir) ->
    Raw = maps:from_list([{list_to_binary(F), rows(Dir,F,fun(R) ->
        (match(K,R))#{source => list_to_binary(F)} end)} || {K,F} <- files()]),
    Groups = [maps:get(list_to_binary(F),Raw) || {_,F} <- files()],
    Merged = lists:foldl(fun merge/2, #{}, lists:append(Groups)),
    Players = rows(Dir,"fifa_data.csv",fun(R) ->
        {fold(maps:get(<<"Name">>,R)),fold(maps:get(<<"Nationality">>,R)),
         team(maps:get(<<"Club">>,R)),R} end),
    #{raw => Raw, matches => maps:values(Merged), players => Players}.

rows(Dir,F,Fun) ->
    {ok,B} = file:read_file(filename:join(Dir,F)),
    [Header|Lines] = binary:split(B,<<"\n">>,[global,trim_all]),
    Keys = fields(string:trim(Header,leading,[16#FEFF])),
    [Fun(maps:from_list(lists:zip(Keys,fields(L)))) || L <- Lines].
fields(L) -> csv(string:trim(L,trailing,"\r"),false,[],[]).
csv(<<>>,false,V,A) -> lists:reverse([list_to_binary(lists:reverse(V))|A]);
csv(<<$", $",R/binary>>,true,V,A) -> csv(R,true,[$"|V],A);
csv(<<$",R/binary>>,Q,V,A) -> csv(R,not Q,V,A);
csv(<<$,,R/binary>>,false,V,A) -> csv(R,false,[],[list_to_binary(lists:reverse(V))|A]);
csv(<<C,R/binary>>,Q,V,A) -> csv(R,Q,[C|V],A).

fold(B) ->
    N = unicode:characters_to_nfd_binary(string:casefold(string:trim(B))),
    re:replace(N,"\\p{M}","",[global,unicode,{return,binary}]).
team(B) ->
    S = re:replace(fold(B),"\\s*-\\s*"," ",[global,{return,binary}]),
    club_alias(S).
club_alias(<<"sociedade esportiva palmeiras">>) -> <<"palmeiras">>;
club_alias(<<"fluminense football club">>) -> <<"fluminense">>;
club_alias(<<"sport club corinthians paulista">>) -> <<"corinthians">>;
club_alias(<<"clube de regatas do flamengo">>) -> <<"flamengo">>;
club_alias(<<"sao paulo fc">>) -> <<"sao paulo">>;
club_alias(<<"santos fc">>) -> <<"santos">>;
club_alias(<<"atletico mineiro">>) -> <<"atletico mg">>;
club_alias(<<"atletico goianiense">>) -> <<"atletico go">>;
club_alias(B) when B == <<"athletico pr">>; B == <<"athletico paranaense">>; B == <<"atletico paranaense">>; B == <<"athletico">> -> <<"atletico pr">>;
club_alias(B) when B == <<"vasco da gama">>; B == <<"vasco da gama rj">> -> <<"vasco">>;
club_alias(<<"bragantino">>) -> <<"red bull bragantino">>;
club_alias(<<"sport recife">>) -> <<"sport">>;
club_alias(<<"ec bahia">>) -> <<"bahia">>;
club_alias(<<"ec juventude">>) -> <<"juventude">>;
club_alias(<<"fortaleza fc">>) -> <<"fortaleza">>;
club_alias(<<"fortaleza ec">>) -> <<"fortaleza">>;
club_alias(<<"santa cruz fc">>) -> <<"santa cruz">>;
club_alias(<<"botafogo">>) -> <<"botafogo rj">>;
club_alias(B) ->
    case binary:split(B,<<" ">>,[global]) of
        [Prefix,_] when Prefix == <<"atletico">>; Prefix == <<"america">>; Prefix == <<"botafogo">> -> B;
        _ -> case re:replace(B," (sp|rj|rs|sc|mg|pr|pe|ba|ce|go|mt|al)$","",[{return,binary}]) of
                 B -> B;
                 Short -> club_alias(Short)
             end
    end.
date(<<D:2/binary,"/",M:2/binary,"/",Y:4/binary>>) -> <<Y/binary,"-",M/binary,"-",D/binary>>;
date(<<D:10/binary,_/binary>>) -> D;
date(_) -> null.
num(B) -> try binary_to_integer(hd(binary:split(B,<<".">>))) catch error:badarg -> null end.
competition(B) ->
    case fold(B) of
        C when C == <<"brasileirao">>; C == <<"brasileirao serie a">> -> <<"serie a">>;
        <<"copa libertadores">> -> <<"libertadores">>;
        C -> C
    end.
base(C,D,S,H,A,HG,AG) ->
    #{competition=>C,date=>date(D),season=>num(S),home=>team(H),away=>team(A),
      home_goal=>num(HG),away_goal=>num(AG)}.
match(history,#{<<"Data">>:=D,<<"Ano">>:=S,<<"Equipe_mandante">>:=H,<<"Equipe_visitante">>:=A,
                <<"Gols_mandante">>:=HG,<<"Gols_visitante">>:=AG,<<"Arena">>:=Arena,<<"Rodada">>:=R}) ->
    (base(<<"serie a">>,D,S,H,A,HG,AG))#{arena=>Arena,round=>R};
match(extended,R=#{<<"date">>:=D,<<"tournament">>:=C,<<"home">>:=H,<<"away">>:=A,
                   <<"home_goal">>:=HG,<<"away_goal">>:=AG}) ->
    (base(competition(C),D,binary:part(D,0,4),H,A,HG,AG))#{statistics=>R};
match(K,R=#{<<"datetime">>:=D,<<"season">>:=S,<<"home_team">>:=H,<<"away_team">>:=A,
            <<"home_goal">>:=HG,<<"away_goal">>:=AG}) ->
    Round = maps:get(<<"round">>,R,<<>>),
    {C,Stage} = case K of
        league -> {<<"serie a">>,<<>>};
        lib -> {<<"libertadores">>,maps:get(<<"stage">>,R)};
        cup -> {<<"copa do brasil">>,cup_stage(num(S),Round)}
    end,
    (base(C,D,S,H,A,HG,AG))#{round=>Round,stage=>Stage}.
cup_stage(S,R) ->
    Final = case S of 2012 -> 6; 2016 -> 7; 2021 -> 7; _ -> 8 end,
    case Final-num(R) of 0 -> <<"final">>; 1 -> <<"semifinals">>; 2 -> <<"quarterfinals">>; _ -> R end.

merge(M=#{competition:=C,date:=D,season:=S,home:=H,away:=A},Acc) ->
    Extended = maps:is_key(statistics,M),
    Year = case {Extended,C,D} of
        {true,<<"serie a">>,Date} when Date >= <<"2021-01-01">>, Date =< <<"2021-02-26">> -> 2020;
        _ -> S
    end,
    Key = {C,case C of <<"serie a">> -> Year; _ -> D end,H,A},
    case maps:find(Key,Acc) of
        {ok,Old} ->
            Combined = maps:merge(M,Old),
            Updated = case maps:get(home_goal,Old) == null andalso maps:get(home_goal,M) /= null of
                true -> maps:merge(Combined,maps:with([home_goal,away_goal],M));
                false -> Combined
            end,
            Acc#{Key=>Updated};
        error when Extended, C == <<"serie a">>, Year =< 2022 -> Acc;
        error -> Acc#{Key=>M}
    end.
