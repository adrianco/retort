-module(soccer_tests).
-include_lib("eunit/include/eunit.hrl").

scenarios_test_() ->
    {setup,fun()->soccer_data:load("data/kaggle") end,fun(_)->ok end,
     fun(DB) ->
        Q=fun(T,P)->soccer_query:run(atom_to_binary(T),
            maps:from_list([{atom_to_binary(K),V}||{K,V}<-maps:to_list(P)]),DB) end,
        League=#{competition=><<"Brasileirão"/utf8>>,season=>2019},
        Derby=#{team=><<"Flamengo-RJ">>,opponent=><<"Fluminense">>},
        [{"Each match CSV can be queried independently",fun()->
            lists:foreach(fun({F,N})->
                ?assertMatch(#{total:=N,items:=[#{date:=_,home_goal:=_,away_goal:=_,competition:=_}]},
                    Q(matches,#{source=>F,limit=>1}))
            end,[{<<"Brasileirao_Matches.csv">>,4180},{<<"Brazilian_Cup_Matches.csv">>,1337},
                 {<<"Libertadores_Matches.csv">>,1255},{<<"BR-Football-Dataset.csv">>,10296},
                 {<<"novo_campeonato_brasileiro.csv">>,6886}])
         end},
         {"Who won the 2019 Brasileirao and which clubs followed?",fun()->
            ?assertMatch(#{total:=20,items:=[#{team:= <<"flamengo">>,played:=38,points:=90},
                #{team:= <<"santos">>,points:=74},#{team:= <<"palmeiras">>,points:=74}]},
                Q(records,League#{limit=>3}))
         end},
         {"Which clubs finished in the bottom four?",fun()->
            ?assertMatch(#{items:=[_,_,_,#{team:= <<"avai">>}]},Q(records,League#{offset=>16}))
         end},
         {"How many games and goals were there per match?",fun()->
            ?assertMatch(#{played:=380,fixtures:=380,goals:=876,goals_per_match:=G} when G==876/380,
                Q(summary,League))
         end},
         {"When did Flamengo last play Fluminense?",fun()->
            #{total:=N,items:=[#{date:=D}|_]}=Q(matches,Derby),?assert(N>20),
            #{items:=[#{date:=Previous}]}=Q(matches,Derby#{offset=>1,limit=>1}),?assert(D>=Previous)
         end},
         {"What is their head-to-head record?",fun()->
            #{items:=[#{wins:=W,losses:=L,draws:=D}]}=Q(records,Derby),
            ?assertMatch(#{items:=[#{wins:=L,losses:=W,draws:=D}]},
                Q(records,#{team=><<"Fluminense">>,opponent=><<"Flamengo">>}))
         end},
         {"What was Corinthians' home record?",fun()->
            ?assertMatch(#{items:=[#{played:=19,team:= <<"corinthians">>}]},
              Q(records,League#{team=><<"Sport Club Corinthians Paulista">>,venue=><<"home">>}))
         end},
         {"Who scored the most and who had the best away record?",fun()->
            ?assertMatch(#{items:=[#{team:= <<"flamengo">>,goals_for:=86}]},Q(records,League#{rank_by=><<"goals">>,limit=>1})),
            #{items:=[#{played:=19,win_rate:=R}|_]}=Q(records,League#{venue=><<"away">>,rank_by=><<"win_rate">>}),?assert(R>50)
         end},
         {"Which matches took place on opening day in 2003?",fun()->
            #{items:=Ms}=Q(matches,#{from=><<"29/03/2003">>,to=><<"2003-03-29">>}),
            ?assert(length(Ms)>0),?assert(lists:all(fun(#{date:=D})->D== <<"2003-03-29">> end,Ms))
         end},
         {"Which cup fixtures were finals and who played in the Libertadores quarterfinals?",fun()->
            ?assertMatch(#{total:=2},Q(matches,#{season=>2019,competition=><<"Copa do Brasil">>,stage=><<"final">>})),
            ?assertMatch(#{total:=8},Q(matches,#{season=>2018,competition=><<"Libertadores">>,stage=><<"quarterfinals">>}))
         end},
         {"Which derbies were played in 2023?",fun()->
            #{total:=N}=Q(matches,#{season=>2023,derby=>true}),?assert(N>0)
         end},
         {"What competitions has Palmeiras played in, and how did seasons compare?",fun()->
            ?assertMatch(#{<<"libertadores">>:=_,<<"copa do brasil">>:=_,<<"serie a">>:=_},
                Q(summary,#{team=><<"Palmeiras">>,group_by=><<"competition">>})),
            ?assertMatch(#{<<"2018">>:=#{played:=380},<<"2019">>:=#{played:=380}},
                Q(summary,#{competition=><<"Serie A">>,group_by=><<"season">>}))
         end},
         {"What was the biggest victory?",fun()->
            #{items:=[#{home_goal:=H,away_goal:=A}]}=Q(matches,#{order=><<"margin">>,limit=>1}),?assert(abs(H-A)>=8)
         end},
         {"Which scheduled matches lack a score?",fun()->
            P=#{source=><<"Brasileirao_Matches.csv">>,season=>2022},
            #{played:=N,fixtures:=380}=Q(summary,P),?assert(N<380)
         end},
         {"Who are the top Brazilians and what are Neymar's attributes?",fun()->
            ?assertMatch(#{total:=18207},Q(players,#{limit=>1})),
            ?assertMatch(#{items:=[#{<<"Name">>:= <<"Neymar Jr">>,<<"Overall">>:= <<"92">>}]},
              Q(players,#{nationality=><<"Brazil">>,limit=>1})),
            ?assertMatch(#{items:=[#{<<"Dribbling">>:= <<"96">>}]},Q(players,#{name=><<"NEYMAR">>}))
         end},
         {"Which Santos players are forwards, and how did their club perform?",fun()->
            #{items:=[#{<<"Club">>:= <<"Santos">>}|_]}=Q(players,#{club=><<"Santos FC">>,position=><<"forward">>}),
            ?assertMatch(#{players:=#{items:=[_|_]},records:=#{items:=[#{points:=74}]}},
                Q(club_profile,League#{team=><<"Santos">>}))
         end},
         {"How many league fixtures did Palmeiras have in 2023?",fun()->
            #{total:=N}=Q(matches,#{team=><<"Palmeiras">>,competition=><<"Serie A">>,season=>2023}),
            ?assert(N>0),?assert(N=<38)
         end},
         {"Where did Guarani host Vasco in 2003?",fun()->
            ?assertMatch(#{items:=[#{arena:= <<"Brinco de Ouro">>,home_goal:=4,away_goal:=2}]},
               Q(matches,#{team=><<"Guarani">>,opponent=><<"Vasco">>,season=>2003,venue=><<"home">>}))
         end},
         {"How many corners were recorded in the 2023 Sao Paulo cup fixture?",fun()->
            ?assertMatch(#{items:=[#{statistics:=#{<<"total_corners">>:= <<"6.0">>}}]},
                Q(matches,#{team=><<"São Paulo FC"/utf8>>,opponent=><<"Flamengo">>,
                            from=><<"2023-09-24">>,to=><<"2023-09-24">>}))
         end},
         {"Warm lookups and aggregates meet the response targets",fun()->
            {Lookup,_}=timer:tc(Q,[players,#{name=><<"Neymar">>}]),
            {Aggregate,_}=timer:tc(Q,[records,#{}]),
            ?assert(Lookup<2000000),?assert(Aggregate<5000000)
         end},
         {"The MCP client can discover tools, call them, and recover from invalid input",fun()->
            Req=#{<<"jsonrpc">>=><<"2.0">>,<<"id">>=>1},
            Call=fun(M,P)->soccer_mcp:handle(Req#{<<"method">>=>M,<<"params">>=>P},DB) end,
            ?assertMatch(#{result:=#{capabilities:=#{tools:=_}}},Call(<<"initialize">>,#{})),
            ?assertMatch(#{result:=#{tools:=[_,_,_,_,_]}},Call(<<"tools/list">>,#{})),
            ?assertMatch(#{error:=#{code:= -32602}},Call(<<"tools/call">>,#{<<"name">>=><<"matches">>,<<"arguments">>=>#{<<"limit">>=>0}})),
            #{result:=#{content:=[#{text:=Text}]}}=Call(<<"tools/call">>,#{<<"name">>=><<"summary">>}),
            ?assertMatch(#{<<"played">>:=_},json:decode(Text)),
            ?assertEqual(silent,soccer_mcp:handle(#{<<"jsonrpc">>=><<"2.0">>,<<"method">>=><<"notifications/initialized">>},DB))
         end}]
     end}.

stdio_utf8_test_() ->
    {timeout,15,fun() ->
        Port=open_port({spawn_executable,os:find_executable("erl")},
            [binary,{line,100000},{args,["+S","2","-noshell","-s","soccer_mcp","main","-s","init","stop"]}]),
        Request=#{jsonrpc=><<"2.0">>,id=>7,method=><<"tools/call">>,
            params=>#{name=><<"matches">>,arguments=>#{team=><<"São Paulo"/utf8>>,
                from=><<"2023-09-24">>,to=><<"2023-09-24">>}}},
        try
            port_command(Port,[json:encode(Request),$\n]),
            receive
                {Port,{data,{eol,Line}}} ->
                    #{<<"result">>:=#{<<"content">>:=[#{<<"text">>:=Text}]}}=json:decode(Line),
                    ?assertMatch(#{<<"total">>:=1},json:decode(Text))
            after 10000 -> error(stdio_timeout)
            end
        after port_close(Port) end
    end}.
