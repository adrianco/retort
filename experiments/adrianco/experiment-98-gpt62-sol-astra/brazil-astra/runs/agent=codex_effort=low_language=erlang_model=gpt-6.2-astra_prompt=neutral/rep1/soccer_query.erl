-module(soccer_query).
-export([run/3, tools/0]).

definitions() ->
    Common = [team,opponent,venue,season,competition,from,to,source,stage,round,derby],
    [{matches,"Fixtures and scores, newest first. Filter both teams for head-to-head or use stage for a bracket. Biggest wins sort by margin.",Common++[order,limit,offset]},
     {records,"Team records and league standings calculated from completed fixtures. Sort by points, goals or win_rate. Venue selects home or away records.",Common++[rank_by,limit,offset]},
     {summary,"Completed match totals, goals per match and home win rate. Group by season for trends or by competition for participation.",Common++[group_by]},
     {players,"FIFA player snapshot, highest overall first. Search by partial name, nationality, club or position. Individual match scorers are unavailable.",[name,nationality,club,position,limit,offset]},
     {club_profile,"Join a club's match record to its FIFA roster. Season filters only matches.",[team,competition,season,limit,offset]}].
tools() ->
    [#{name=>N,description=>list_to_binary(D),inputSchema=>#{type=>object,
       properties=>maps:from_list([{K,property(K)} || K <- Ks]),additionalProperties=>false,
       required=>case N of club_profile -> [team]; _ -> [] end}} || {N,D,Ks} <- definitions()].
property(K) when K == season; K == offset -> #{type=>integer,minimum=>0};
property(limit) -> #{type=>integer,minimum=>1,maximum=>100};
property(derby) -> #{type=>boolean};
property(venue) -> enum([home,away,either]);
property(rank_by) -> enum([points,goals,win_rate]);
property(order) -> enum([latest,margin]);
property(group_by) -> enum([season,competition]);
property(position) -> #{type=>string,description=><<"FIFA position code or forward">>};
property(source) -> #{type=>string,enum=>[<<"Brasileirao_Matches.csv">>,<<"Brazilian_Cup_Matches.csv">>,
    <<"Libertadores_Matches.csv">>,<<"BR-Football-Dataset.csv">>,<<"novo_campeonato_brasileiro.csv">>]};
property(_) -> #{type=>string}.
enum(V) -> #{type=>string,enum=>V}.

run(Name,Args,DB) when is_binary(Name), is_map(Args) ->
    [{N,_,Keys}] = [D || D={K,_,_} <- definitions(),atom_to_binary(K)==Name],
    P = maps:from_list([begin
        [Key] = [K || K <- Keys,atom_to_binary(K)==B],
        {Key,prepare(Key,V,property(Key))}
    end || {B,V} <- maps:to_list(Args)]),
    query(N,P,DB).
prepare(K,V,#{enum:=Allowed}) -> true=lists:member(V,[enum_value(X)||X<-Allowed]), normalize(K,V);
prepare(_,V,#{type:=integer,minimum:=Min}=Spec) when is_integer(V),V>=Min ->
    true= V =< maps:get(maximum,Spec,V), V;
prepare(_,V,#{type:=boolean}) when is_boolean(V) -> V;
prepare(K,V,#{type:=string}) when is_binary(V) -> normalize(K,V).
enum_value(X) when is_atom(X) -> atom_to_binary(X);
enum_value(X) -> X.
normalize(K,V) when K==team; K==opponent; K==club -> soccer_data:team(V);
normalize(competition,V) -> soccer_data:competition(V);
normalize(source,V) -> V;
normalize(K,V) when K==from; K==to ->
    D=soccer_data:date(V), [Y,M,Day]=[binary_to_integer(X)||X<-binary:split(D,<<"-">>,[global])],
    true=calendar:valid_date(Y,M,Day), D;
normalize(_,V) -> soccer_data:fold(V).

query(players,P,#{players:=Rows}) ->
    Found = [R || {Name,Nation,Club,R} <- Rows,contains(Name,maps:get(name,P,<<>>)),
                  equals(nationality,Nation,P),equals(club,Club,P),
                  position(maps:get(position,P,any),maps:get(<<"Position">>,R))],
    Sorted = lists:reverse(lists:keysort(1,[{binary_to_integer(maps:get(<<"Overall">>,R)),R} || R<-Found])),
    page([R || {_,R}<-Sorted],P);
query(club_profile,P=#{team:=T},DB) ->
    #{records=>query(records,P,DB),players=>query(players,P#{club=>T},DB)};
query(N,P,#{matches:=All,raw:=Raw}) ->
    Rows = case maps:find(source,P) of error -> All; {ok,F} -> maps:get(F,Raw) end,
    Matches = [M || M<-Rows,selected(M,P)],
    compute(N,Matches,P).

contains(_,<<>>) -> true;
contains(S,Q) -> binary:match(S,Q) /= nomatch.
position(any,_) -> true;
position(<<"forward">>,Pos) -> lists:member(Pos,[<<"ST">>,<<"CF">>,<<"LW">>,<<"RW">>,<<"LF">>,<<"RF">>,<<"LS">>,<<"RS">>]);
position(Q,Pos) -> string:uppercase(Q)==Pos.
equals(K,V,P) -> maps:get(K,P,V)==V.
selected(M=#{home:=H,away:=A,date:=D},P) ->
    lists:all(fun(K)-> equals(K,maps:get(K,M,<<>>),P) end,[competition,season,stage,round])
    andalso (not maps:is_key(from,P) orelse D >= maps:get(from,P))
    andalso (not maps:is_key(to,P) orelse (D /= null andalso D =< maps:get(to,P)))
    andalso (not maps:get(derby,P,false) orelse derby(H,A))
    andalso ((maps:get(venue,P,either) /= <<"away">> andalso equals(team,H,P) andalso equals(opponent,A,P))
      orelse (maps:get(venue,P,either) /= <<"home">> andalso equals(team,A,P) andalso equals(opponent,H,P))).
derby(H,A) ->
    lists:any(fun(G)-> lists:member(H,G) andalso lists:member(A,G) end,
        [[<<"flamengo">>,<<"fluminense">>,<<"vasco">>,<<"botafogo rj">>],
         [<<"corinthians">>,<<"palmeiras">>,<<"santos">>,<<"sao paulo">>],
         [<<"gremio">>,<<"internacional">>],[<<"cruzeiro">>,<<"atletico mg">>],
         [<<"bahia">>,<<"vitoria">>],[<<"atletico pr">>,<<"coritiba">>],
         [<<"ceara">>,<<"fortaleza">>]]).
page(R,P) ->
    Total=length(R), Tail=lists:nthtail(min(Total,maps:get(offset,P,0)),R),
    #{total=>Total,items=>lists:sublist(Tail,maps:get(limit,P,20))}.
played(#{home_goal:=H,away_goal:=A}) -> is_integer(H) andalso is_integer(A).
compute(matches,Ms,P) ->
    Sorted = case maps:get(order,P,latest) of
        <<"margin">> -> lists:reverse(lists:sort([{abs(H-A),maps:get(date,M),M} ||
            M=#{home_goal:=H,away_goal:=A}<-Ms,played(M)]));
        _ -> lists:reverse(lists:sort([{maps:get(date,M),M}||M<-Ms]))
    end,
    page([element(tuple_size(T),T)||T<-Sorted],P);
compute(summary,Ms,#{group_by:=Group}) ->
    Key=binary_to_existing_atom(Group),
    maps:from_list([{group_label(K),summary(V)} || {K,V}<-maps:to_list(maps:groups_from_list(fun(M)->maps:get(Key,M) end,Ms))]);
compute(summary,Ms,_) -> summary(Ms);
compute(records,Ms,P) ->
    Table=lists:foldl(fun(#{home:=H,away:=A,home_goal:=HG,away_goal:=AG},Acc)->
        T=record(home,H,HG,AG,P,Acc), record(away,A,AG,HG,P,T)
    end,#{},[M || M<-Ms,played(M)]),
    Rows=[stats(T,V)||{T,V}<-maps:to_list(Table)],
    Metric=case maps:get(rank_by,P,points) of <<"goals">>->goals_for; <<"win_rate">>->win_rate; _->points end,
    page(lists:sort(fun(X,Y)->rank(X,Metric)=<rank(Y,Metric) end,Rows),P).
group_label(Y) when is_integer(Y) -> integer_to_binary(Y);
group_label(K) -> K.
summary(Ms) ->
    Scores=[{H,A}||M=#{home_goal:=H,away_goal:=A}<-Ms,played(M)],
    N=length(Scores), Goals=lists:sum([H+A||{H,A}<-Scores]),
    #{fixtures=>length(Ms),played=>N,goals=>Goals,goals_per_match=>ratio(Goals,N),
      home_win_rate=>ratio(100*length([ok||{H,A}<-Scores,H>A]),N)}.
ratio(_,0) -> null;
ratio(X,Y) -> X/Y.
record(Side,T,F,A,P,Acc) ->
    case equals(team,T,P) andalso lists:member(maps:get(venue,P,<<"either">>),[<<"either">>,atom_to_binary(Side)]) of
        false -> Acc;
        true ->
            {W,D,L,GF,GA}=maps:get(T,Acc,{0,0,0,0,0}),
            Acc#{T=>{W+flag(F>A),D+flag(F==A),L+flag(F<A),GF+F,GA+A}}
    end.
flag(true)->1;
flag(false)->0.
stats(T,{W,D,L,F,A}) ->
    #{team=>T,played=>W+D+L,wins=>W,draws=>D,losses=>L,points=>3*W+D,goals_for=>F,
      goals_against=>A,goal_difference=>F-A,win_rate=>ratio(100*W,W+D+L)}.
rank(R,K) -> { -maps:get(K,R), -maps:get(points,R), -maps:get(wins,R),
               -maps:get(goal_difference,R), -maps:get(goals_for,R),maps:get(team,R)}.
