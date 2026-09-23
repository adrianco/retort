%% MCP tool definitions and text formatting on top of brsoccer_query.
-module(brsoccer_tools).
-export([list/0, call/2, fmt_match/1]).

-define(KEYS, [team, opponent, home_team, away_team, competition, season, date_from, date_to,
               stage, venue, name, nationality, club, position, min_overall, limit, team_a,
               team_b, min_matches, question, brazilian_clubs_only]).

str(D) -> #{type => <<"string">>, description => D}.
int(D) -> #{type => <<"integer">>, description => D}.

schema(Props, Req) -> #{type => <<"object">>, properties => Props, required => Req}.

match_filters() ->
    #{team => str(<<"Team name (any variant, e.g. 'Flamengo', 'Palmeiras-SP', 'São Paulo')"/utf8>>),
      opponent => str(<<"Opponent team name">>),
      home_team => str(<<"Home team">>), away_team => str(<<"Away team">>),
      competition => str(<<"Brasileirão | Copa do Brasil | Libertadores | Serie B | Serie C"/utf8>>),
      season => int(<<"Season year">>),
      date_from => str(<<"Start date (YYYY-MM-DD or DD/MM/YYYY)">>),
      date_to => str(<<"End date">>),
      stage => str(<<"Stage/round, e.g. 'final', 'semifinals', 'Round 5'">>),
      limit => int(<<"Max results (default 20)">>)}.

list() ->
    MF = match_filters(),
    [tool(<<"search_matches">>, <<"Find matches by team, opponent, competition, season, date range or stage across all match datasets.">>,
          schema(MF, [])),
     tool(<<"head_to_head">>, <<"Head-to-head record and match list between two teams.">>,
          schema(maps:merge(maps:with([competition, season, limit], MF),
                            #{team_a => str(<<"First team">>), team_b => str(<<"Second team">>)}),
                 [<<"team_a">>, <<"team_b">>])),
     tool(<<"team_stats">>, <<"Win/draw/loss record and goals for a team, optionally by season, competition and venue (home/away/all).">>,
          schema(maps:merge(maps:with([team, competition, season, date_from, date_to], MF),
                            #{venue => str(<<"home | away | all">>)}), [<<"team">>])),
     tool(<<"standings">>, <<"League table calculated from match results for a Brasileirão season (champion and relegated teams)."/utf8>>,
          schema(#{season => int(<<"Season year">>), competition => str(<<"Default Brasileirão"/utf8>>),
                   limit => int(<<"Rows to show">>)}, [<<"season">>])),
     tool(<<"league_stats">>, <<"Aggregate statistics: average goals per match and home/away/draw rates.">>,
          schema(maps:with([competition, season, team, date_from, date_to], MF), [])),
     tool(<<"biggest_wins">>, <<"Largest victory margins, optionally filtered.">>,
          schema(maps:with([competition, season, team, limit], MF), [])),
     tool(<<"best_records">>, <<"Rank teams by win rate at home, away or overall.">>,
          schema(maps:merge(maps:with([competition, season, limit], MF),
                            #{venue => str(<<"home | away | all">>),
                              min_matches => int(<<"Minimum matches (default 10)">>)}), [])),
     tool(<<"top_scoring_teams">>, <<"Teams ranked by goals scored, e.g. for a season.">>,
          schema(maps:with([competition, season, limit], MF), [])),
     tool(<<"derbies">>, <<"Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...).">>,
          schema(maps:with([season, competition, team, limit], MF), [])),
     tool(<<"team_competitions">>, <<"Which competitions (and seasons) a team appears in.">>,
          schema(maps:with([team], MF), [<<"team">>])),
     tool(<<"search_players">>, <<"Search FIFA player database by name, nationality, club, position, minimum rating.">>,
          schema(#{name => str(<<"Player name substring">>), nationality => str(<<"e.g. Brazil">>),
                   club => str(<<"Club name">>), position => str(<<"Position code (ST, GK...) or forward/midfielder/defender/goalkeeper">>),
                   min_overall => int(<<"Minimum overall rating">>),
                   brazilian_clubs_only => #{type => <<"boolean">>, description => <<"Only players at Brazilian clubs">>},
                   limit => int(<<"Max results (default 20)">>)}, [])),
     tool(<<"brazilian_clubs_players">>, <<"Count and average rating of FIFA players per Brazilian club.">>,
          schema(#{}, [])),
     tool(<<"dataset_info">>, <<"Row counts for all loaded datasets.">>, schema(#{}, []))].

tool(N, D, S) -> #{name => N, description => D, inputSchema => S}.

%% Args: map with binary keys (from JSON). Returns {ok, Text} | {error, Text}.
call(Name, Args) ->
    O = maps:from_list([{K, V} || K <- ?KEYS, V <- [maps:get(atom_to_binary(K), Args, null)], V =/= null]),
    try
        {ok, unicode:characters_to_binary(run(Name, O))}
    catch
        throw:{bad_args, Msg} -> {error, Msg};
        C:E:St -> {error, iolist_to_binary(io_lib:format("~p:~p ~p", [C, E, hd(St)]))}
    end.

limit(O, D) ->
    case maps:get(limit, O, undefined) of
        undefined -> D;
        L -> max(1, brsoccer_norm:int(L))
    end.

need(K, O) ->
    case maps:get(K, O, undefined) of
        undefined -> throw({bad_args, <<"missing required argument: ", (atom_to_binary(K))/binary>>});
        V -> V
    end.

run(<<"search_matches">>, O) ->
    Ms = brsoccer_query:matches(O),
    L = limit(O, 20),
    [io_lib:format("Found ~b matches~n", [length(Ms)]),
     [[<<"- ">>, fmt_match(M), $\n] || M <- lists:sublist(Ms, L)],
     more(Ms, L)];
run(<<"head_to_head">>, O) ->
    A = need(team_a, O), B = need(team_b, O),
    H = brsoccer_query:head_to_head(A, B, maps:without([team_a, team_b], O)),
    Ms = maps:get(matches, H),
    L = limit(O, 20),
    [io_lib:format("~ts vs ~ts: ~b matches in dataset~n", [A, B, length(Ms)]),
     [[<<"- ">>, fmt_match(M), $\n] || M <- lists:sublist(Ms, L)], more(Ms, L),
     io_lib:format("~nHead-to-head in dataset: ~ts ~b wins, ~ts ~b wins, ~b draws (goals ~b-~b)~n",
                   [A, maps:get(a_wins, H), B, maps:get(b_wins, H), maps:get(draws, H),
                    maps:get(a_goals, H), maps:get(b_goals, H)])];
run(<<"team_stats">>, O) ->
    T = need(team, O),
    R = brsoccer_query:team_record(T, O),
    Venue = maps:get(venue, O, <<"all">>),
    Ctx = [case maps:get(season, O, undefined) of undefined -> ""; S -> io_lib:format(" ~p", [S]) end,
           case maps:get(competition, O, undefined) of undefined -> ""; C -> [" ", C] end],
    io_lib:format("~ts ~ts record (~ts):~n- Matches: ~b~n- Wins: ~b, Draws: ~b, Losses: ~b~n"
                  "- Goals For: ~b, Goals Against: ~b~n- Win rate: ~p%~n",
                  [T, Venue, string:trim(iolist_to_binary(Ctx)) , maps:get(matches, R), maps:get(wins, R),
                   maps:get(draws, R), maps:get(losses, R), maps:get(goals_for, R),
                   maps:get(goals_against, R), maps:get(win_rate, R)]);
run(<<"standings">>, O) ->
    S = need(season, O),
    Rows = brsoccer_query:standings(S, maps:get(competition, O, <<"Brasileirão"/utf8>>)),
    N = length(Rows),
    [io_lib:format("~p Brasileirão Final Standings (calculated from matches):~n", [S]),
     [io_lib:format("~b. ~ts - ~b pts (~bW, ~bD, ~bL, GD ~b)~ts~n",
                    [P, T, Pts, W, D, L, GD,
                     if P =:= 1 -> " - Champion"; N >= 16, P > N - 4 -> " - Relegated"; true -> "" end])
      || #{position := P, team := T, points := Pts, wins := W, draws := D, losses := L,
           goal_diff := GD} <- lists:sublist(Rows, limit(O, 40))],
     case Rows of [] -> "No data for that season.\n"; _ -> "" end];
run(<<"league_stats">>, O) ->
    R = brsoccer_query:league_summary(O),
    io_lib:format("Matches: ~b~nTotal goals: ~b~nAverage goals per match: ~p~nHome win rate: ~p%~n"
                  "Away win rate: ~p%~nDraw rate: ~p%~n",
                  [maps:get(matches, R), maps:get(goals, R), maps:get(avg_goals, R),
                   maps:get(home_win_rate, R), maps:get(away_win_rate, R), maps:get(draw_rate, R)]);
run(<<"biggest_wins">>, O) ->
    Ms = brsoccer_query:biggest_wins(O, limit(O, 10)),
    ["Biggest victories:\n",
     lists:zipwith(fun(I, M) -> [integer_to_list(I), ". ", fmt_match(M), $\n] end,
                   lists:seq(1, length(Ms)), Ms)];
run(<<"best_records">>, O) ->
    V = maps:get(venue, O, <<"home">>),
    Min = case maps:get(min_matches, O, undefined) of undefined -> 10; M -> brsoccer_norm:int(M) end,
    Rows = lists:sublist(brsoccer_query:best_records(V, O, Min), limit(O, 10)),
    [io_lib:format("Best ~ts records (min ~b matches):~n", [V, Min]) | record_rows(Rows)];
run(<<"top_scoring_teams">>, O) ->
    Rows = lists:sublist(brsoccer_query:goals_ranking(O), limit(O, 10)),
    ["Teams by goals scored:\n" | record_rows(Rows)];
run(<<"derbies">>, O) ->
    Ds = brsoccer_query:derbies(O),
    L = limit(O, 30),
    [io_lib:format("Found ~b derby matches~n", [length(Ds)]),
     [[<<"- [">>, N, <<"] ">>, fmt_match(M), $\n] || {N, M} <- lists:sublist(Ds, L)], more(Ds, L)];
run(<<"team_competitions">>, O) ->
    T = need(team, O),
    [io_lib:format("Competitions for ~ts:~n", [T]),
     [io_lib:format("- ~ts: ~b matches, seasons ~w-~w~n", [C, N, hd(Ss), lists:last(Ss)])
      || {C, N, Ss} <- brsoccer_query:team_competitions(T)]];
run(<<"search_players">>, O) ->
    {Note, Ps} = case brsoccer_query:players(O) of
                     [] when is_map_key(name, O) ->
                         {"No exact name match; closest partial matches shown.\n",
                          brsoccer_query:players(O#{name_any => true})};
                     Exact -> {"", Exact}
                 end,
    L = limit(O, 20),
    [Note, io_lib:format("Found ~b players~n", [length(Ps)]),
     lists:zipwith(fun(I, P) -> [integer_to_list(I), ". ", fmt_player(P), $\n] end,
                   lists:seq(1, min(L, length(Ps))), lists:sublist(Ps, L)),
     more(Ps, L)];
run(<<"brazilian_clubs_players">>, _O) ->
    ["Players at Brazilian clubs (FIFA data):\n",
     [io_lib:format("- ~ts: ~b players (avg rating: ~b)~n", [C, N, A])
      || {C, N, A} <- brsoccer_query:brazilian_club_players()]];
run(<<"dataset_info">>, _O) ->
    [io_lib:format("- ~p: ~b rows~n", [S, N]) || {S, N} <- brsoccer_data:source_counts()];
run(Other, _) ->
    throw({bad_args, <<"unknown tool: ", Other/binary>>}).

record_rows(Rows) ->
    lists:zipwith(
      fun(I, #{team := T, matches := N, wins := W, draws := D, losses := L, goals_for := GF,
               goals_against := GA, win_rate := WR}) ->
              io_lib:format("~b. ~ts - ~b matches, ~bW ~bD ~bL, goals ~b-~b, win rate ~p%~n",
                            [I, T, N, W, D, L, GF, GA, WR])
      end, lists:seq(1, length(Rows)), Rows).

more(L, N) when length(L) > N -> io_lib:format("... (~b more results in dataset)~n", [length(L) - N]);
more(_, _) -> "".

fmt_match(#{date := D, home := H, away := A, hg := HG, ag := AG, competition := C, stage := S}) ->
    Ctx = case S of <<>> -> C; _ -> <<C/binary, " ", S/binary>> end,
    io_lib:format("~ts: ~ts ~b-~b ~ts (~ts)", [D, H, HG, AG, A, Ctx]).

fmt_player(#{name := N, overall := O, potential := P, position := Pos, club := C, age := Age,
             nationality := Nat}) ->
    io_lib:format("~ts - Overall: ~w, Potential: ~w, Position: ~ts, Club: ~ts, Age: ~w, Nationality: ~ts",
                  [N, O, P, Pos, case C of <<>> -> <<"(none)">>; _ -> C end, Age, Nat]).
