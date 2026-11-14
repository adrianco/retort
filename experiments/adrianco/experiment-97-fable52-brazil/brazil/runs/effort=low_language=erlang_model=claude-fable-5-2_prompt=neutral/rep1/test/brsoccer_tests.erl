%%% BDD-style (Given / When / Then) EUnit scenarios for the Brazilian Soccer
%%% MCP server.  They run against the real Kaggle files in data/kaggle.
-module(brsoccer_tests).
-include_lib("eunit/include/eunit.hrl").

u(S) -> unicode:characters_to_binary(S).

%% --- helpers -------------------------------------------------------------
call(Tool, Args) ->
    {ok, Text} = brsoccer_tools:call(Tool, Args),
    Text.

has(Text, Sub) -> binary:match(Text, u(Sub)) =/= nomatch.

-define(assertHas(Text, Sub), ?assert(has(Text, Sub))).
-define(_assertHas(Text, Sub), ?_assert(has(Text, Sub))).

rpc(Map) ->
    {reply, Json} = brsoccer_mcp:handle_line(iolist_to_binary(json:encode(Map))),
    json:decode(Json).

tool_rpc(Id, Name, Args) ->
    rpc(#{jsonrpc => <<"2.0">>, id => Id, method => <<"tools/call">>,
          params => #{name => Name, arguments => Args}}).

%% =========================================================================
%% Feature: CSV parsing (no data needed)
%% =========================================================================
csv_test_() ->
    [{"Given quoted fields with commas and doubled quotes, Then they are unescaped",
      ?_assertEqual([[<<"a">>, <<"b,c">>, <<"say \"hi\"">>], [<<"1">>, <<>>, <<"3">>]],
                    brsoccer_csv:parse(<<"a,\"b,c\",\"say \"\"hi\"\"\"\r\n1,,3\n">>))},
     {"Given a BOM and a blank trailing line, Then both are ignored",
      ?_assertEqual([[<<"x">>, <<"y">>]], brsoccer_csv:parse(<<16#EF, 16#BB, 16#BF, "x,y\n\n">>))},
     {"Given a quoted field spanning two lines, Then it is one field",
      ?_assertEqual([[<<"a\nb">>, <<"c">>]], brsoccer_csv:parse(<<"\"a\nb\",c\n">>))},
     {"Given a header, Then rows become maps",
      ?_assertEqual([#{<<"h1">> => <<"1">>, <<"h2">> => <<"2">>}],
                    brsoccer_csv:to_maps([[<<"h1">>, <<"h2">>], [<<"1">>, <<"2">>]]))}].

%% =========================================================================
%% Feature: name / date normalisation (no data needed)
%% =========================================================================
team_name_variations_test_() ->
    Same = fun(Names) -> lists:usort([brsoccer_norm:team_key(u(N)) || N <- Names]) end,
    [{"Given state-suffixed and plain spellings, Then they map to one club",
      [?_assertEqual([<<"palmeiras">>], Same(["Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "palmeiras", "Palmeiras SP"])),
       ?_assertEqual([<<"sao paulo">>], Same(["São Paulo", "Sao Paulo-SP", "São Paulo - SP", "Sao Paulo", "São Paulo FC"])),
       ?_assertEqual([<<"gremio">>], Same(["Grêmio", "Gremio-RS", "Gremio RS", "Grêmio - RS"])),
       ?_assertEqual([<<"flamengo">>], Same(["Flamengo-RJ", "Flamengo - RJ", "Flamengo"]))]},
     {"Given full / alternative club names, Then aliases resolve",
      [?_assertEqual([<<"corinthians">>], Same(["Sport Club Corinthians Paulista", "Corinthians-SP"])),
       ?_assertEqual([<<"athletico">>], Same(["Atletico-PR", "Athletico-PR", "Atlético Paranaense", "Athletico Paranaense", "Athletico", "Atlético - PR"])),
       ?_assertEqual([<<"atletico">>], Same(["Atlético-MG", "Atletico Mineiro", "Atlético Mineiro - MG", "Atletico-MG"])),
       ?_assertEqual([<<"vasco">>], Same(["Vasco", "Vasco da Gama-RJ", "Vasco Da Gama RJ"])),
       ?_assertEqual([<<"sport">>], Same(["Sport-PE", "Sport Recife", "Sport Club do Recife", "Sport"])),
       ?_assertEqual([<<"bragantino">>], Same(["Red Bull Bragantino-SP", "Bragantino", "Bragantino - SP"])),
       ?_assertEqual([<<"csa">>], Same(["Csa-AL", "CSA", "C.s.a. - AL", "CS Alagoano"]))]},
     {"Given namesakes from different states, Then they stay distinct",
      [?_assertNotEqual(brsoccer_norm:team_key(<<"Botafogo-RJ">>), brsoccer_norm:team_key(<<"Botafogo - PB">>)),
       ?_assertNotEqual(brsoccer_norm:team_key(<<"Atletico-MG">>), brsoccer_norm:team_key(<<"Atletico-GO">>)),
       ?_assertNotEqual(brsoccer_norm:team_key(<<"Flamengo - RJ">>), brsoccer_norm:team_key(<<"Flamengo - PI">>)),
       ?_assertNotEqual(brsoccer_norm:team_key(<<"Nacional (URU)">>), brsoccer_norm:team_key(<<"Nacional (PAR)">>)),
       ?_assertEqual(brsoccer_norm:team_key(<<"Nacional (URU)">>), brsoccer_norm:team_key(<<"Nacional-URU">>))]},
     {"Given accents, Then folding removes them",
      ?_assertEqual(<<"sao paulo avai gremio">>, brsoccer_norm:fold(u("  São  Paulo Avaí GRÊMIO ")))}].

date_formats_test_() ->
    [?_assertEqual({{2023, 9, 24}, undefined}, brsoccer_norm:parse_date(<<"2023-09-24">>)),
     ?_assertEqual({{2003, 3, 29}, undefined}, brsoccer_norm:parse_date(<<"29/03/2003">>)),
     ?_assertEqual({{2012, 5, 19}, <<"18:30:00">>}, brsoccer_norm:parse_date(<<"2012-05-19 18:30:00">>)),
     ?_assertEqual(undefined, brsoccer_norm:parse_date(<<"NA">>)),
     ?_assertEqual(undefined, brsoccer_norm:parse_date(<<"2023-02-30">>)),
     ?_assertEqual(3, brsoccer_norm:to_int(<<"3.0">>)),
     ?_assertEqual(undefined, brsoccer_norm:to_int(<<"NA">>)),
     ?_assertEqual(serie_a, brsoccer_norm:competition(u("Brasileirão"))),
     ?_assertEqual(copa_do_brasil, brsoccer_norm:competition(<<"copa do brasil">>)),
     ?_assertEqual(libertadores, brsoccer_norm:competition(<<"Copa Libertadores">>)),
     ?_assertEqual(unknown, brsoccer_norm:competition(<<"Premier League">>))].

%% =========================================================================
%% Features needing the data set
%% =========================================================================
data_test_() ->
    {setup,
     fun() -> ok = brsoccer_data:ensure_loaded() end,
     fun(_) -> ok end,
     {timeout, 120,
      [{"Feature: data coverage", coverage()},
       {"Feature: match queries", match_queries()},
       {"Feature: team queries", team_queries()},
       {"Feature: player queries", player_queries()},
       {"Feature: competition queries", competition_queries()},
       {"Feature: statistical analysis", statistics()},
       {"Feature: MCP protocol", protocol()},
       {"Feature: error handling", errors()},
       {"Feature: performance", performance()}]}}.

coverage() ->
    [{"Given the data dir, When loaded, Then all 6 CSV files are fully loaded",
      fun() ->
              #{matches_by_source := S, players := P, unique_matches := U} = brsoccer_data:summary(),
              ?assertEqual(#{brasileirao => 4180, copa_do_brasil => 1337, libertadores => 1255,
                             br_football => 10296, novo_campeonato => 6886}, S),
              ?assertEqual(18207, P),
              ?assert(U < 4180 + 1337 + 1255 + 10296 + 6886)
      end},
     {"Given overlapping files, Then every source is individually queryable",
      [?_assert(length(brsoccer_query:find_matches(#{source => Src, team => <<"Flamengo">>})) > 0)
       || Src <- [brasileirao, copa_do_brasil, libertadores, br_football, novo_campeonato]]},
     {"Given overlapping Serie A files, Then a season has exactly 380 unique matches",
      [?_assertEqual(380, length(brsoccer_query:find_matches(#{competition => serie_a, season => Y})))
       || Y <- [2006, 2012, 2015, 2019, 2020, 2021, 2022]]},
     {"Given UTF-8 names, Then accented display names survive",
      [?_assertEqual(u("São Paulo"), brsoccer_data:display(<<"sao paulo">>)),
       ?_assertEqual(u("Grêmio"), brsoccer_data:display(<<"gremio">>))]},
     {"Then the dataset_summary tool describes everything",
      fun() ->
              T = call(<<"dataset_summary">>, #{}),
              ?assertHas(T, "fifa_data.csv"), ?assertHas(T, "18207 players"),
              ?assertHas(T, "Libertadores: seasons 2013-2022")
      end}].

match_queries() ->
    [{"Scenario: Find matches between two teams",
      fun() ->
              %% When I search for matches between Flamengo and Fluminense
              {ok, #{matches := Ms, record := R}} =
                  brsoccer_query:head_to_head(<<"Flamengo">>, <<"Fluminense">>, #{}),
              %% Then I receive a list of matches, each with date, scores and competition
              ?assert(length(Ms) >= 40),
              lists:foreach(fun(#{date := D, hg := HG, ag := AG, comp := C, home := H, away := A}) ->
                                    ?assertMatch({_, _, _}, D),
                                    ?assert(is_integer(HG) andalso is_integer(AG)),
                                    ?assert(is_atom(C)),
                                    ?assertEqual([<<"flamengo">>, <<"fluminense">>], lists:sort([H, A]))
                            end, Ms),
              #{wins := W, draws := D0, losses := L, matches := N} = R,
              ?assertEqual(N, W + D0 + L)
      end},
     {"Q: Show me all Flamengo vs Fluminense matches",
      fun() ->
              T = call(<<"head_to_head">>, #{<<"team_a">> => <<"Flamengo">>, <<"team_b">> => <<"fluminense-rj">>}),
              ?assertHas(T, "Fla-Flu"), ?assertHas(T, "Head-to-head in dataset"),
              ?assertHas(T, "more matches in dataset")
      end},
     {"Q: What matches did Palmeiras play in 2023?",
      fun() ->
              T = call(<<"search_matches">>, #{<<"team">> => <<"Palmeiras">>, <<"season">> => 2023}),
              ?assertHas(T, "Palmeiras"), ?assertHas(T, "2023-"),
              Ms = brsoccer_query:find_matches(#{team => <<"Palmeiras">>, season => 2023}),
              ?assert(length(Ms) > 30),
              ?assert(lists:all(fun(#{date := {Y, _, _}}) -> Y =:= 2023 end, Ms))
      end},
     {"Q: Find all Copa do Brasil finals",
      fun() ->
              T = call(<<"search_matches">>, #{<<"competition">> => <<"Copa do Brasil">>,
                                               <<"stage">> => <<"final">>, <<"limit">> => 50}),
              ?assertHas(T, "2015-12-02: Palmeiras 2-1 Santos"),
              ?assertHas(T, "2019-09-18: Internacional 1-2 Athletico-PR")
      end},
     {"Q: When did Flamengo last play Corinthians? What was the score?",
      fun() ->
              [#{date := D, hg := HG, ag := AG} | Rest] =
                  brsoccer_query:find_matches(#{team => <<"Flamengo">>, opponent => <<"Corinthians">>,
                                                played_only => true}),
              ?assert(lists:all(fun(#{date := D2}) -> D2 =< D end, Rest)),
              ?assert(is_integer(HG) andalso is_integer(AG)),
              ?assertMatch({2023, _, _}, D)
      end},
     {"Given a date range and venue, Then only matching home games are returned",
      fun() ->
              Ms = brsoccer_query:find_matches(#{team => <<"Santos">>, venue => home,
                                                 date_from => {2015, 1, 1}, date_to => {2015, 12, 31}}),
              ?assert(length(Ms) >= 19),
              ?assert(lists:all(fun(#{home := H, date := {Y, _, _}}) ->
                                        H =:= <<"santos">> andalso Y =:= 2015 end, Ms)),
              T = call(<<"search_matches">>, #{<<"team">> => <<"Santos">>, <<"venue">> => <<"home">>,
                                               <<"date_from">> => <<"01/01/2015">>,
                                               <<"date_to">> => <<"2015-12-31">>}),
              ?assertHas(T, io_lib:format("Found ~b matches", [length(Ms)]))
      end},
     {"Q: Show me all derbies in 2023",
      fun() ->
              Ds = brsoccer_query:derbies(#{season => 2023}),
              ?assert(length(Ds) > 10),
              ?assert(lists:keymember(<<"Fla-Flu">>, 1, Ds)),
              ?assertHas(call(<<"derbies">>, #{<<"season">> => 2023}), "[Fla-Flu]")
      end},
     {"Given the historical file, Then stadium and round are reported",
      fun() ->
              T = call(<<"search_matches">>, #{<<"team">> => <<"Guarani">>, <<"opponent">> => <<"Vasco">>,
                                               <<"season">> => 2003, <<"venue">> => <<"home">>}),
              ?assertHas(T, "2003-03-29: Guarani 4-2 Vasco"),
              ?assertHas(T, "Round 1, Brinco de Ouro")
      end}].

team_queries() ->
    [{"Scenario: Get team statistics",
      fun() ->
              %% When I request statistics for Palmeiras in season 2023
              {ok, #{overall := #{matches := N, wins := W, draws := D, losses := L, gf := GF, ga := GA},
                     home := #{matches := HN}, away := #{matches := AN}}} =
                  brsoccer_query:team_stats(<<"Palmeiras">>, #{season => 2023}),
              %% Then I receive wins, losses, draws and goals
              ?assert(N > 30), ?assertEqual(N, W + D + L), ?assertEqual(N, HN + AN),
              ?assert(GF > GA)
      end},
     {"Q: What is Corinthians' home record in 2022?",
      fun() ->
              T = call(<<"team_stats">>, #{<<"team">> => <<"Corinthians">>, <<"season">> => 2022,
                                           <<"venue">> => <<"home">>, <<"competition">> => u("Brasileirão")}),
              ?assertHas(T, "Corinthians home record"),
              ?assertHas(T, "- Matches: 19"),
              ?assertHas(T, "Wins: 12, Draws: 4, Losses: 3"),
              ?assertHas(T, "Win rate: 63.2%")
      end},
     {"Q: Which team scored the most goals in Serie A 2019?",
      fun() ->
              [#{team := T, gf := GF} | _] =
                  brsoccer_query:team_rankings(#{competition => serie_a, season => 2019, metric => goals_for}),
              ?assertEqual({<<"flamengo">>, 86}, {T, GF})
      end},
     {"Q: Compare Palmeiras and Santos head-to-head",
      fun() ->
              {ok, #{record := AB}} = brsoccer_query:head_to_head(<<"Palmeiras">>, <<"Santos">>, #{}),
              {ok, #{record := BA}} = brsoccer_query:head_to_head(<<"Santos">>, <<"Palmeiras">>, #{}),
              ?assertEqual(maps:get(wins, AB), maps:get(losses, BA)),
              ?assertEqual(maps:get(gf, AB), maps:get(ga, BA)),
              ?assert(maps:get(matches, AB) > 30),
              ?assertHas(call(<<"head_to_head">>, #{<<"team_a">> => <<"Palmeiras">>, <<"team_b">> => <<"Santos">>}),
                         "Palmeiras vs Santos")
      end},
     {"Q: What competitions has Palmeiras played in? (cross-file)",
      fun() ->
              {ok, Rows} = brsoccer_query:team_competitions(<<"Palmeiras">>),
              ?assertEqual([copa_do_brasil, libertadores, serie_a],
                           lists:sort([C || #{competition := C} <- Rows])),
              T = call(<<"team_competitions">>, #{<<"team">> => <<"palmeiras-sp">>}),
              ?assertHas(T, "Libertadores"), ?assertHas(T, "Copa do Brasil"), ?assertHas(T, "Brasileirão")
      end},
     {"Given accent-free or partial input, Then the team is still found",
      [?_assertEqual([<<"sao paulo">>], brsoccer_query:resolve_team(<<"sao paulo">>)),
       ?_assertEqual([<<"gremio">>], brsoccer_query:resolve_team(<<"GREMIO">>)),
       ?_assertEqual([<<"internacional">>], brsoccer_query:resolve_team(<<"Inter">>)),
       ?_assert(lists:member(<<"chapecoense">>, brsoccer_query:resolve_team(<<"Chape">>)))]}].

player_queries() ->
    [{"Q: Find all Brazilian players in the dataset",
      fun() ->
              Ps = brsoccer_query:search_players(#{nationality => <<"Brazil">>}),
              ?assertEqual(827, length(Ps)),
              ?assert(lists:all(fun(#{nationality := N}) -> N =:= <<"Brazil">> end, Ps)),
              [#{name := Top, overall := 92} | _] = Ps,
              ?assertEqual(<<"Neymar Jr">>, Top)
      end},
     {"Q: Who are the top Brazilian players?",
      fun() ->
              T = call(<<"search_players">>, #{<<"nationality">> => <<"brazilian">>, <<"limit">> => 3}),
              ?assertHas(T, "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain")
      end},
     {"Q: Who is Neymar? (search by name, with attributes)",
      fun() ->
              T = call(<<"player_details">>, #{<<"name">> => <<"neymar">>}),
              ?assertHas(T, "Neymar Jr"), ?assertHas(T, "Overall: 92, Potential: 93"),
              ?assertHas(T, "Dribbling 96")
      end},
     {"Q: Who are the highest-rated players at Grêmio? (accent-insensitive club)",
      fun() ->
              A = brsoccer_query:search_players(#{club => u("Grêmio")}),
              B = brsoccer_query:search_players(#{club => <<"gremio">>}),
              ?assertEqual(A, B), ?assertEqual(20, length(A)),
              Os = [O || #{overall := O} <- A],
              ?assertEqual(lists:reverse(lists:sort(Os)), Os)
      end},
     {"Q: Show me all forwards from Santos",
      fun() ->
              Ps = brsoccer_query:search_players(#{club => <<"Santos">>, position => <<"forwards">>}),
              ?assert(length(Ps) > 0),
              ?assert(lists:all(fun(#{club := C, position := P}) ->
                                        C =:= <<"Santos">> andalso brsoccer_query:position_group(P) =:= forward
                                end, Ps))
      end},
     {"Given the club alias 'Sport', Then Sport Recife players are found, not Sporting CP",
      fun() ->
              Ps = brsoccer_query:search_players(#{club => <<"Sport">>}),
              ?assertEqual([<<"Sport Club do Recife">>], lists:usort([C || #{club := C} <- Ps]))
      end},
     {"Given rating / age / position filters, Then all are honoured",
      fun() ->
              Ps = brsoccer_query:search_players(#{nationality => <<"Brazil">>, position => <<"GK">>,
                                                   min_overall => 80, max_age => 30}),
              ?assert(length(Ps) > 0),
              ?assert(lists:all(fun(#{position := P, overall := O, age := A}) ->
                                        P =:= <<"GK">> andalso O >= 80 andalso A =< 30 end, Ps))
      end},
     {"Q: Brazilian players at Brazilian clubs (cross-file: FIFA clubs x league teams)",
      fun() ->
              Rows = brsoccer_query:brazilian_club_summary(),
              Clubs = [C || #{club := C} <- Rows],
              ?assert(lists:member(u("Grêmio"), Clubs)),
              ?assert(lists:member(<<"Santos">>, Clubs)),
              ?assertNot(lists:member(<<"Santos Laguna">>, Clubs)),
              T = call(<<"brazilian_clubs_players">>, #{}),
              ?assertHas(T, "Top-rated Brazilian players"), ?assertHas(T, "avg rating:")
      end},
     {"Cross-file: a player's profile includes his club's recent matches",
      fun() ->
              [#{name := N} | _] = brsoccer_query:search_players(#{club => <<"Cruzeiro">>}),
              T = call(<<"player_details">>, #{<<"name">> => N, <<"club">> => <<"Cruzeiro">>}),
              ?assertHas(T, "Most recent matches of Cruzeiro")
      end}].

competition_queries() ->
    [{"Q: Who won the 2019 Brasileirão?",
      fun() ->
              [First, Second, Third | _] = Rows = brsoccer_query:standings(serie_a, 2019),
              ?assertEqual(20, length(Rows)),
              ?assertMatch(#{team := <<"flamengo">>, points := 90, wins := 28, draws := 6, losses := 4}, First),
              ?assertMatch(#{team := <<"santos">>, points := 74, wins := 22, draws := 8, losses := 8}, Second),
              ?assertMatch(#{team := <<"palmeiras">>, points := 74, wins := 21, draws := 11, losses := 6}, Third),
              T = call(<<"standings">>, #{<<"season">> => 2019, <<"competition">> => <<"Serie A">>}),
              ?assertHas(T, "1. Flamengo - 90 pts (28W, 6D, 4L)"), ?assertHas(T, "- Champion")
      end},
     {"Q: Which teams were relegated in 2020?",
      fun() ->
              T = call(<<"standings">>, #{<<"season">> => 2020}),
              Lines = [L || L <- binary:split(T, <<"\n">>, [global]), has(L, "Relegated")],
              ?assertEqual(4, length(Lines)),
              [?assert(lists:any(fun(L) -> has(L, Team) end, Lines))
               || Team <- ["Vasco", "Goiás", "Coritiba", "Botafogo"]]
      end},
     {"Given an incomplete season, Then no champion/relegation is claimed",
      fun() ->
              T = call(<<"standings">>, #{<<"season">> => 2023}),
              ?assertNot(has(T, "Champion")), ?assertNot(has(T, "Relegated")),
              ?assertHas(T, "season incomplete")
      end},
     {"Q: Show the 2018 Copa Libertadores bracket",
      fun() ->
              T = call(<<"competition_bracket">>, #{<<"competition">> => <<"Copa Libertadores">>,
                                                    <<"season">> => 2018}),
              [?assertHas(T, S) || S <- ["Group stage", "Round of 16", "Quarterfinals", "Semifinals",
                                         "Final (2 matches)", "Champion: River Plate (5-3 on aggregate)"]]
      end},
     {"Q: Who won the 2015 Copa do Brasil? (tie on aggregate is reported honestly)",
      fun() ->
              T = call(<<"competition_bracket">>, #{<<"competition">> => <<"Copa do Brasil">>,
                                                    <<"season">> => 2015, <<"stage">> => <<"final">>}),
              ?assertHas(T, "Palmeiras 2-1 Santos"), ?assertHas(T, "Aggregate 2-2"),
              T2 = call(<<"competition_bracket">>, #{<<"competition">> => <<"Copa do Brasil">>,
                                                     <<"season">> => 2018, <<"stage">> => <<"final">>}),
              ?assertHas(T2, "Champion: Cruzeiro (3-1 on aggregate)")
      end},
     {"Q: Compare the 2018 and 2019 seasons",
      fun() ->
              T = call(<<"compare_seasons">>, #{<<"season_a">> => 2018, <<"season_b">> => 2019}),
              ?assertHas(T, "Table leader: Palmeiras (80 pts)"),
              ?assertHas(T, "Table leader: Flamengo (90 pts)"),
              ?assertHas(T, "Average goals per match: 2.18"), ?assertHas(T, "Average goals per match: 2.31")
      end}].

statistics() ->
    [{"Q: What's the average goals per match in the Brasileirão?",
      fun() ->
              #{matches := N, goals := G, goals_per_match := GPM, home_wins := HW, away_wins := AW,
                draws := D, home_win_rate := HR} = brsoccer_query:competition_stats(#{competition => serie_a}),
              ?assert(N > 7000), ?assertEqual(N, HW + AW + D),
              ?assert(abs(GPM - G / N) < 1.0e-9),
              ?assert(GPM > 2.0 andalso GPM < 3.0),
              ?assert(HR > 40.0 andalso HR < 60.0),
              ?assertHas(call(<<"competition_stats">>, #{<<"competition">> => u("Brasileirão")}),
                         "Average goals per match: 2.")
      end},
     {"Q: Which team has the best away record?",
      fun() ->
              [#{team := Best, win_rate := WR} | Rest] =
                  brsoccer_query:team_rankings(#{competition => serie_a, venue => away, min_matches => 100}),
              ?assert(is_binary(Best)),
              ?assert(lists:all(fun(#{win_rate := W, matches := M}) -> W =< WR andalso M >= 100 end, Rest)),
              %% away table of a single season sums to that season's matches
              Away2019 = brsoccer_query:team_rankings(#{competition => serie_a, season => 2019, venue => away}),
              ?assertEqual(380, lists:sum([M || #{matches := M} <- Away2019])),
              ?assertHas(call(<<"team_rankings">>, #{<<"venue">> => <<"away">>, <<"competition">> => <<"Serie A">>}),
                         "(away matches)")
      end},
     {"Q: Which team has the best home record?",
      fun() ->
              T = call(<<"team_rankings">>, #{<<"venue">> => <<"home">>, <<"season">> => 2019,
                                              <<"competition">> => <<"Serie A">>, <<"limit">> => 1}),
              ?assertHas(T, "1. Flamengo - 19 matches, 17W")
      end},
     {"Q: Show me the biggest wins in the dataset",
      fun() ->
              Ms = brsoccer_query:biggest_wins(#{}, 10),
              Margins = [abs(H - A) || #{hg := H, ag := A} <- Ms],
              ?assertEqual(lists:reverse(lists:sort(Margins)), Margins),
              ?assertEqual(8, hd(Margins)),
              T = call(<<"biggest_wins">>, #{<<"limit">> => 3}),
              ?assertHas(T, u("1. 2021-06-08: São Paulo 9-1 4 de Julho")),
              ?assertHas(T, "Average goals per match:"), ?assertHas(T, "Home win rate:")
      end},
     {"Home vs away performance of one team adds up to the overall record",
      fun() ->
              {ok, #{overall := O, home := H, away := A}} =
                  brsoccer_query:team_stats(<<"Flamengo">>, #{competition => serie_a, season => 2019}),
              ?assertEqual(38, maps:get(matches, O)),
              [?assertEqual(maps:get(K, O), maps:get(K, H) + maps:get(K, A))
               || K <- [matches, wins, draws, losses, gf, ga]]
      end},
     {"Extended statistics (corners, shots) come from the BR-Football file",
      fun() ->
              T = call(<<"team_stats">>, #{<<"team">> => <<"Flamengo">>, <<"season">> => 2022}),
              ?assertHas(T, "Extended stats"), ?assertHas(T, "corners")
      end}].

protocol() ->
    [{"initialize returns server info and the tools capability",
      fun() ->
              #{<<"id">> := 1, <<"result">> := R} =
                  rpc(#{jsonrpc => <<"2.0">>, id => 1, method => <<"initialize">>,
                        params => #{protocolVersion => <<"2025-06-18">>, capabilities => #{},
                                    clientInfo => #{name => <<"t">>, version => <<"0">>}}}),
              ?assertMatch(#{<<"protocolVersion">> := <<"2025-06-18">>,
                             <<"capabilities">> := #{<<"tools">> := _},
                             <<"serverInfo">> := #{<<"name">> := <<"brazilian-soccer-mcp">>}}, R)
      end},
     {"notifications get no reply",
      ?_assertEqual(noreply, brsoccer_mcp:handle_line(
                               <<"{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n">>))},
     {"tools/list returns a schema for every tool, and every tool is callable",
      fun() ->
              #{<<"result">> := #{<<"tools">> := Tools}} =
                  rpc(#{jsonrpc => <<"2.0">>, id => 2, method => <<"tools/list">>}),
              ?assertEqual(15, length(Tools)),
              lists:foreach(fun(#{<<"name">> := N, <<"description">> := D,
                                  <<"inputSchema">> := #{<<"type">> := <<"object">>, <<"properties">> := P,
                                                         <<"required">> := Req}}) ->
                                    ?assert(is_binary(N) andalso byte_size(D) > 10),
                                    ?assert(lists:all(fun(K) -> maps:is_key(K, P) end, Req))
                            end, Tools)
      end},
     {"tools/call returns UTF-8 text content",
      fun() ->
              #{<<"id">> := <<"x">>, <<"result">> := #{<<"isError">> := false,
                                                       <<"content">> := [#{<<"type">> := <<"text">>, <<"text">> := T}]}} =
                  tool_rpc(<<"x">>, <<"standings">>, #{season => 2019, limit => 4}),
              ?assertHas(T, u("4. Grêmio - 65 pts"))
      end},
     {"ping, unknown method, bad JSON and unknown tool follow JSON-RPC",
      fun() ->
              ?assertMatch(#{<<"result">> := #{}}, rpc(#{jsonrpc => <<"2.0">>, id => 3, method => <<"ping">>})),
              ?assertMatch(#{<<"error">> := #{<<"code">> := -32601}},
                           rpc(#{jsonrpc => <<"2.0">>, id => 4, method => <<"bogus">>})),
              {reply, J} = brsoccer_mcp:handle_line(<<"{not json">>),
              ?assertMatch(#{<<"error">> := #{<<"code">> := -32700}, <<"id">> := null}, json:decode(J)),
              ?assertMatch(#{<<"error">> := #{<<"code">> := -32602}}, tool_rpc(5, <<"nope">>, #{})),
              ?assertMatch(#{<<"error">> := #{<<"code">> := -32600}}, rpc(#{foo => 1})),
              ?assertEqual(noreply, brsoccer_mcp:handle_line(<<"\n">>))
      end}].

errors() ->
    Err = fun(Tool, Args) -> {error, T} = brsoccer_tools:call(Tool, Args), T end,
    [{"unknown team", ?_assertHas(Err(<<"team_stats">>, #{<<"team">> => <<"Real Madrid XYZ">>}), "No team matching")},
     {"missing argument", ?_assertHas(Err(<<"head_to_head">>, #{<<"team_a">> => <<"Flamengo">>}), "Missing required argument 'team_b'")},
     {"bad competition", ?_assertHas(Err(<<"standings">>, #{<<"season">> => 2019, <<"competition">> => <<"NBA">>}), "Unknown competition")},
     {"bad date", ?_assertHas(Err(<<"search_matches">>, #{<<"date_from">> => <<"yesterday">>}), "Invalid date")},
     {"bad type", ?_assertHas(Err(<<"standings">>, #{<<"season">> => <<"abc">>}), "must be an integer")},
     {"season without data", ?_assertHas(Err(<<"standings">>, #{<<"season">> => 1950}), "No Brasileirão data for season 1950")},
     {"wrong argument types do not crash",
      [?_assertMatch({error, _}, brsoccer_tools:call(<<"team_stats">>, #{<<"team">> => 42})),
       ?_assertMatch({error, _}, brsoccer_tools:call(<<"search_players">>, #{<<"name">> => [1, 2]})),
       ?_assertMatch({error, _}, brsoccer_tools:call(<<"search_matches">>, <<"nope">>))]},
     {"tool errors are reported with isError over MCP",
      ?_assertMatch(#{<<"result">> := #{<<"isError">> := true}},
                    tool_rpc(9, <<"team_stats">>, #{team => <<"Nonexistent FC 123">>}))},
     {"no player found is a normal answer",
      ?_assertHas(call(<<"search_players">>, #{<<"name">> => <<"zzzzqqq">>}), "No players found")}].

performance() ->
    Timed = fun(Tool, Args) ->
                    {Us, {ok, _}} = timer:tc(fun() -> brsoccer_tools:call(Tool, Args) end),
                    Us / 1.0e6
            end,
    [{"Simple lookups respond in < 2 seconds",
      [?_assert(Timed(<<"head_to_head">>, #{<<"team_a">> => <<"Flamengo">>, <<"team_b">> => <<"Corinthians">>}) < 2.0),
       ?_assert(Timed(<<"player_details">>, #{<<"name">> => <<"Neymar">>}) < 2.0),
       ?_assert(Timed(<<"search_matches">>, #{<<"team">> => <<"Palmeiras">>}) < 2.0)]},
     {"Aggregate queries respond in < 5 seconds",
      [?_assert(Timed(<<"team_rankings">>, #{}) < 5.0),
       ?_assert(Timed(<<"biggest_wins">>, #{}) < 5.0),
       ?_assert(Timed(<<"competition_stats">>, #{}) < 5.0),
       ?_assert(Timed(<<"brazilian_clubs_players">>, #{}) < 5.0)]},
     {"A cold load of all six files takes < 5 seconds",
      fun() ->
              {Us, ok} = timer:tc(fun() -> brsoccer_data:load() end),
              ?assert(Us < 5000000)
      end}].
