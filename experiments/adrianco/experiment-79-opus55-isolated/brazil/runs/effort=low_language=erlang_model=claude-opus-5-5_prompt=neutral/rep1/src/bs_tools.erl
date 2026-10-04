%% MCP tool definitions and their text rendering.
%% call/2 takes the tool name and the JSON arguments (binary keys) and
%% returns {ok, Text} | {error, Text} | {error, unknown_tool}.
-module(bs_tools).
-export([list/0, call/2]).

-define(DEFAULT_LIMIT, 20).

%% --- tool catalogue --------------------------------------------------------

list() ->
    Team = {<<"team">>, str(<<"Team name, any spelling (e.g. \"Flamengo\", \"Palmeiras-SP\", \"Sao Paulo\")">>)},
    Comp = {<<"competition">>, str(<<"Competition: \"Brasileirão\"/\"Serie A\", \"Copa do Brasil\", \"Libertadores\", \"Serie B\" or \"Serie C\""/utf8>>)},
    Season = {<<"season">>, int(<<"Season year, e.g. 2019">>)},
    Limit = {<<"limit">>, int(<<"Maximum number of rows to return (default 20)">>)},
    Venue = {<<"venue">>, #{type => <<"string">>, enum => [<<"home">>, <<"away">>, <<"either">>],
                            description => <<"Restrict to the team's home or away matches">>}},
    [tool(<<"search_matches">>,
          <<"Find matches by team, opponent, competition, season, date range, round or stage. "
            "Returns dated results, newest first, plus a head-to-head summary when two teams are given.">>,
          [Team, {<<"opponent">>, str(<<"Second team, to list only matches between the two">>)},
           Venue, Comp, Season,
           {<<"date_from">>, str(<<"Earliest date, YYYY-MM-DD or DD/MM/YYYY">>)},
           {<<"date_to">>, str(<<"Latest date, YYYY-MM-DD or DD/MM/YYYY">>)},
           {<<"round">>, int(<<"Round number (league or cup round)">>)},
           {<<"stage">>, str(<<"Knockout stage: group stage, round of 16, quarterfinals, semifinals, final">>)},
           Limit], []),
     tool(<<"head_to_head">>,
          <<"Compare two teams: wins, draws, goals and the most recent meetings.">>,
          [{<<"team_a">>, str(<<"First team">>)}, {<<"team_b">>, str(<<"Second team">>)}, Comp, Season, Limit],
          [<<"team_a">>, <<"team_b">>]),
     tool(<<"team_stats">>,
          <<"Win/draw/loss record, goals for/against and win rate of a team, optionally "
            "restricted to a season, competition and home/away matches.">>,
          [Team, Season, Comp, Venue], [<<"team">>]),
     tool(<<"standings">>,
          <<"League table for a season calculated from match results (champion, relegation zone).">>,
          [Season, Comp], [<<"season">>]),
     tool(<<"season_summary">>,
          <<"Aggregate statistics: matches, goals per match, home/draw/away rates. "
            "Optional competition and season filters.">>,
          [Comp, Season], []),
     tool(<<"compare_seasons">>,
          <<"Compare two seasons of a competition (goals per match, home win rate, champion).">>,
          [{<<"season_a">>, int(<<"First season">>)}, {<<"season_b">>, int(<<"Second season">>)}, Comp],
          [<<"season_a">>, <<"season_b">>]),
     tool(<<"biggest_wins">>,
          <<"Largest winning margins, optionally for a team, competition or season.">>,
          [Team, Comp, Season, Limit], []),
     tool(<<"team_rankings">>,
          <<"Rank teams by a metric: best home/away/overall record (win rate), most goals scored, "
            "best defence, most wins.">>,
          [{<<"metric">>, #{type => <<"string">>,
                            enum => [<<"best_home_record">>, <<"best_away_record">>, <<"best_overall_record">>,
                                     <<"most_goals">>, <<"best_defense">>, <<"most_wins">>],
                            description => <<"Ranking metric">>}},
           Comp, Season,
           {<<"min_matches">>, int(<<"Minimum matches played to be ranked (default 10)">>)}, Limit],
          [<<"metric">>]),
     tool(<<"team_competitions">>,
          <<"Competitions and seasons a team appears in, with its record in each.">>,
          [Team], [<<"team">>]),
     tool(<<"derbies">>,
          <<"Matches between traditional Brazilian rivals (Fla-Flu, Grenal, Derby Paulista...).">>,
          [Season, Comp, Team, Limit], []),
     tool(<<"search_players">>,
          <<"Search the FIFA player database by name, nationality, club, position "
            "(code such as ST, or forward/midfielder/defender/goalkeeper) and minimum rating. "
            "Sorted by overall rating.">>,
          [{<<"name">>, str(<<"Player name or part of it">>)},
           {<<"nationality">>, str(<<"Country, e.g. Brazil">>)},
           {<<"club">>, str(<<"Club name or part of it">>)},
           {<<"position">>, str(<<"Position code or group">>)},
           {<<"min_overall">>, int(<<"Minimum overall rating">>)},
           {<<"max_age">>, int(<<"Maximum age">>)}, Limit], []),
     tool(<<"player_details">>,
          <<"Full profile of one player: ratings, physical attributes and skills.">>,
          [{<<"name">>, str(<<"Player name">>)}], [<<"name">>]),
     tool(<<"club_player_summary">>,
          <<"Players of a nationality (default Brazil) grouped by club with count and average rating.">>,
          [{<<"nationality">>, str(<<"Country (default Brazil)">>)},
           {<<"brazilian_clubs_only">>, #{type => <<"boolean">>,
                                          description => <<"Only clubs from Brazil (default true)">>}},
           Limit], []),
     tool(<<"team_profile">>,
          <<"Cross-dataset profile of a club: match record per competition plus its FIFA squad.">>,
          [Team], [<<"team">>]),
     tool(<<"data_summary">>,
          <<"Describe the loaded datasets: files, match counts, competitions and season coverage.">>,
          [], [])].

tool(Name, Desc, Props, Required) ->
    #{name => Name, description => Desc,
      inputSchema => #{type => <<"object">>, properties => maps:from_list(Props), required => Required}}.

str(D) -> #{type => <<"string">>, description => D}.
int(D) -> #{type => <<"integer">>, description => D}.

%% --- dispatch --------------------------------------------------------------

call(Name, Args) when is_map(Args) ->
    case lists:any(fun(#{name := N}) -> N =:= Name end, list()) of
        false -> {error, unknown_tool};
        true ->
            try {ok, unicode_bin(run(Name, Args))}
            catch throw:{tool_error, Msg} -> {error, unicode_bin(Msg)}
            end
    end;
call(_, _) -> {error, <<"arguments must be an object">>}.

unicode_bin(IoData) -> iolist_to_binary(IoData).

run(<<"search_matches">>, A) ->
    O = match_opts(A),
    case {maps:get(team, O, undefined), maps:get(opponent, O, undefined)} of
        {undefined, Opp} when Opp =/= undefined -> run_search(maps:remove(opponent, O#{team => Opp}), A);
        _ -> run_search(O, A)
    end;
run(<<"head_to_head">>, A) ->
    TA = team(A, <<"team_a">>, required), TB = team(A, <<"team_b">>, required),
    O = maps:without([team, opponent, venue], match_opts(A)),
    #{matches := Ms} = H = bs_query:head_to_head(TA, TB, O),
    [io_lib:format("~s vs ~s~s:~n", [d(TA), d(TB), rivalry(TA, TB)]),
     match_lines(Ms, limit(A)), "\n", h2h_line(TA, TB, H)];
run(<<"team_stats">>, A) ->
    T = team(A, <<"team">>, required),
    O = match_opts(A),
    Venue = maps:get(venue, O, either),
    Ms = bs_query:matches(O),
    R = bs_query:record(T, Ms, Venue),
    [io_lib:format("~s ~s record~s:~n", [d(T), venue_label(Venue), scope(O)]), record_block(R),
     case is_map_key(competition, O) of
         true -> [];
         false ->
             ["By competition:\n",
              [io_lib:format("- ~s: ~s~n", [bs_data:comp_label(C), record_line(CR)])
               || C <- comps(Ms),
                  #{matches := N} = CR <- [bs_query:record(T, [M || #{comp := C0} = M <- Ms, C0 =:= C], Venue)],
                  N > 0]]
     end];
run(<<"standings">>, A) ->
    Season = int_arg(A, <<"season">>, required),
    Comp = comp(A, serie_a),
    standings_text(Comp, Season);
run(<<"season_summary">>, A) ->
    O = maps:with([competition, season], match_opts(A)),
    Ms = bs_query:matches(O),
    S = bs_query:league_stats(Ms),
    [io_lib:format("Statistics~s:~n", [scope(O)]), stats_block(S),
     case is_map_key(season, O) of
         true -> [];
         false ->
             Seasons = lists:usort([Y || #{season := Y} <- bs_query:played(Ms), Y =/= undefined]),
             ["Goals per match by season:\n",
              [begin
                   #{matches := N, avg_goals := Avg} =
                       bs_query:league_stats([M || #{season := Y0} = M <- Ms, Y0 =:= Y]),
                   io_lib:format("- ~p: ~.2f (~p matches)~n", [Y, Avg, N])
               end || Y <- Seasons]]
     end];
run(<<"compare_seasons">>, A) ->
    SA = int_arg(A, <<"season_a">>, required), SB = int_arg(A, <<"season_b">>, required),
    Comp = comp(A, serie_a),
    [[begin
          Ms = bs_query:matches(#{competition => Comp, season => S}),
          Top = case bs_query:standings(Ms) of
                    [{T, #{points := P}} | _] when Comp =/= copa_do_brasil, Comp =/= libertadores ->
                        io_lib:format("- Top of table: ~s (~p pts)~n", [d(T), P]);
                    _ -> []
                end,
          Scorer = case bs_query:rankings(Ms, either, goals_for, 1) of
                       [{T2, #{gf := G}} | _] -> io_lib:format("- Most goals: ~s (~p)~n", [d(T2), G]);
                       [] -> []
                   end,
          [io_lib:format("~s ~p:~n", [bs_data:comp_label(Comp), S]),
           stats_block(bs_query:league_stats(Ms)), Top, Scorer, "\n"]
      end || S <- [SA, SB]]];
run(<<"biggest_wins">>, A) ->
    O = match_opts(A),
    Ms = bs_query:biggest_wins(bs_query:matches(O), limit(A)),
    [io_lib:format("Biggest victories~s:~n", [scope(O)]),
     numbered([match_text(M) || M <- Ms])];
run(<<"team_rankings">>, A) ->
    O = maps:with([competition, season], match_opts(A)),
    {Venue, Metric, Title} =
        case str_arg(A, <<"metric">>, required) of
            <<"best_home_record">> -> {home, win_rate, "Best home records"};
            <<"best_away_record">> -> {away, win_rate, "Best away records"};
            <<"best_overall_record">> -> {either, win_rate, "Best overall records"};
            <<"most_goals">> -> {either, goals_for, "Most goals scored"};
            <<"best_defense">> -> {either, goals_against, "Best defences (goals conceded per match)"};
            <<"most_wins">> -> {either, wins, "Most wins"};
            Other -> err(["Unknown metric: ", Other])
        end,
    Min = case int_arg(A, <<"min_matches">>, undefined) of undefined -> 10; N -> N end,
    Rows = lists:sublist(bs_query:rankings(bs_query:matches(O), Venue, Metric, Min), limit(A)),
    [io_lib:format("~s~s (min ~p matches):~n", [Title, scope(O), Min]),
     numbered([io_lib:format("~s - ~s", [d(T), record_line(R)]) || {T, R} <- Rows])];
run(<<"team_competitions">>, A) ->
    T = team(A, <<"team">>, required),
    [io_lib:format("Competitions played by ~s in the dataset:~n", [d(T)]),
     [io_lib:format("- ~s (~s): ~s~n", [bs_data:comp_label(C), seasons_text(Ss), record_line(R)])
      || {C, Ss, R} <- bs_query:team_competitions(T)]];
run(<<"derbies">>, A) ->
    O = maps:with([competition, season, team], match_opts(A)),
    Ds = bs_query:derbies(O),
    [io_lib:format("Derbies~s: ~p matches~n", [scope(O), length(Ds)]),
     [io_lib:format("- ~s [~s]~n", [match_text(M), N]) || {N, M} <- lists:sublist(Ds, limit(A))],
     more(length(Ds), limit(A))];
run(<<"search_players">>, A) ->
    O = player_opts(A),
    Ps = bs_query:players(O),
    Shown = lists:sublist(Ps, limit(A)),
    [io_lib:format("Players found: ~p~n", [length(Ps)]),
     numbered([player_line(P) || P <- Shown]), more(length(Ps), limit(A)),
     case {Ps, maps:get(club, O, undefined)} of
         {[], Club} when Club =/= undefined ->
             <<"Note: the FIFA dataset only covers some Brazilian clubs; clubs such as "
               "Flamengo, Palmeiras, Corinthians and São Paulo have no players in it.\n"/utf8>>;
         _ -> []
     end];
run(<<"player_details">>, A) ->
    Name = str_arg(A, <<"name">>, required),
    case bs_query:players(#{name => Name}) of
        [] -> err(["No player found matching \"", Name, "\""]);
        [P | Rest] ->
            [player_block(P),
             case Rest of
                 [] -> [];
                 _ -> ["\nOther matches:\n", [["- ", player_line(R), "\n"] || R <- lists:sublist(Rest, 5)]]
             end]
    end;
run(<<"club_player_summary">>, A) ->
    Nat = case str_arg(A, <<"nationality">>, undefined) of undefined -> <<"Brazil">>; N -> N end,
    Only = maps:get(<<"brazilian_clubs_only">>, A, true) =/= false,
    Ps = [P || #{club := C, club_key := K} = P <- bs_query:players(#{nationality => Nat}),
               C =/= <<>>, (not Only) orelse K =/= undefined],
    Groups = lists:foldl(fun(#{club := C, overall := Ov}, M) ->
                                 maps:update_with(C, fun(L) -> [Ov | L] end, [Ov], M)
                         end, #{}, Ps),
    Rows = lists:sort(fun({CA, LA}, {CB, LB}) -> {length(LA), CB} >= {length(LB), CA} end,
                      maps:to_list(Groups)),
    [io_lib:format("~s players~s: ~p players at ~p clubs~n",
                   [Nat, case Only of true -> " at Brazilian clubs"; false -> " by club" end,
                    length(Ps), length(Rows)]),
     [io_lib:format("- ~s: ~p players (avg rating: ~.1f)~n", [C, length(L), lists:sum(L) / length(L)])
      || {C, L} <- lists:sublist(Rows, limit(A))],
     more(length(Rows), limit(A))];
run(<<"team_profile">>, A) ->
    T = team(A, <<"team">>, required),
    Ms = bs_query:matches(#{team => T}),
    Squad = [P || #{club_key := K} = P <- bs_query:players(#{}), K =:= T],
    [io_lib:format("~s - profile~n~nAll matches in dataset:~n", [d(T)]),
     record_block(bs_query:record(T, Ms)),
     "By competition:\n",
     [io_lib:format("- ~s (~s): ~s~n", [bs_data:comp_label(C), seasons_text(Ss), record_line(R)])
      || {C, Ss, R} <- bs_query:team_competitions(T)],
     "\nFIFA squad:\n",
     case Squad of
         [] -> "- no players for this club in the FIFA dataset\n";
         _ ->
             Ovs = [O || #{overall := O} <- Squad],
             [io_lib:format("- ~p players, average rating ~.1f~n", [length(Squad), lists:sum(Ovs) / length(Ovs)]),
              numbered([player_line(P) || P <- lists:sublist(Squad, 10)])]
     end];
run(<<"data_summary">>, _) ->
    All = bs_data:all_matches(), Dedup = bs_data:matches(),
    ["Loaded datasets:\n",
     [io_lib:format("- ~s: ~p rows~n", [source_file(S), N]) || {S, N} <- bs_data:sources()],
     io_lib:format("~nMatches: ~p rows, ~p unique after merging overlapping files~n",
                   [length(All), length(Dedup)]),
     [begin
          CMs = [M || #{comp := C0} = M <- Dedup, C0 =:= C],
          Ss = lists:usort([S || #{season := S} <- CMs, S =/= undefined]),
          io_lib:format("- ~s: ~p matches (~s)~n", [bs_data:comp_label(C), length(CMs), seasons_text(Ss)])
      end || C <- comps(Dedup)],
     io_lib:format("Teams: ~p~n", [length(lists:usort(lists:append([[H, Aw] || #{home := H, away := Aw} <- Dedup])))])].

run_search(O, A) ->
    Ms = bs_query:matches(O),
    T = maps:get(team, O, undefined), Opp = maps:get(opponent, O, undefined),
    Title = case {T, Opp} of
                {undefined, _} -> "Matches";
                {_, undefined} -> io_lib:format("~s matches", [d(T)]);
                _ -> io_lib:format("~s vs ~s~s", [d(T), d(Opp), rivalry(T, Opp)])
            end,
    [io_lib:format("~s~s: ~p found~n", [Title, scope(O), length(Ms)]),
     match_lines(Ms, limit(A)),
     case {T, Opp, Ms} of
         {undefined, _, _} -> [];
         {_, _, []} -> [];
         {_, undefined, _} -> ["\n", d(T), ": ", record_line(bs_query:record(T, Ms, maps:get(venue, O, either))), "\n"];
         _ -> ["\n", h2h_line(T, Opp, #{matches => Ms, a => bs_query:record(T, Ms), b => bs_query:record(Opp, Ms)})]
     end].

standings_text(Comp, Season) ->
    Ms = bs_query:matches(#{competition => Comp, season => Season}),
    Rows = bs_query:standings(Ms),
    Rows =:= [] andalso err(io_lib:format("No ~s matches found for season ~p", [bs_data:comp_label(Comp), Season])),
    League = lists:member(Comp, [serie_a, serie_b, serie_c]),
    Played = [N || {_, #{matches := N}} <- Rows],
    Complete = League andalso lists:min(Played) =:= lists:max(Played),
    Count = length(Rows),
    Note = fun(1) when Complete -> " - Champion";
              (I) when Complete, Comp =:= serie_a, Count >= 20, I > Count - 4 -> " - Relegated";
              (_) -> ""
           end,
    [io_lib:format("~p ~s ~s (calculated from matches):~n",
                   [Season, bs_data:comp_label(Comp),
                    case Complete of true -> "Final Standings"; false -> "Table" end]),
     [io_lib:format("~p. ~s - ~p pts (~pW, ~pD, ~pL) GF ~p GA ~p GD ~s~s~n",
                    [I, d(T), P, W, D, L, F, Ag, signed(F - Ag), Note(I)])
      || {I, {T, #{points := P, wins := W, draws := D, losses := L, gf := F, ga := Ag}}}
             <- lists:enumerate(Rows)],
     case League of
         true when not Complete -> "Note: teams have played different numbers of matches; the data for this season is incomplete.\n";
         true -> [];
         false -> "Note: this is a knockout competition; the table only aggregates results.\n"
     end].

%% --- argument handling -----------------------------------------------------

match_opts(A) ->
    put_opts([{team, team(A, <<"team">>, undefined)},
              {opponent, team(A, <<"opponent">>, undefined)},
              {venue, venue(A)},
              {competition, comp(A, undefined)},
              {season, int_arg(A, <<"season">>, undefined)},
              {round, int_arg(A, <<"round">>, undefined)},
              {stage, case str_arg(A, <<"stage">>, undefined) of
                          undefined -> undefined;
                          S -> bs_query:parse_stage(S)
                      end},
              {date_from, date_arg(A, <<"date_from">>)},
              {date_to, date_arg(A, <<"date_to">>)}]).

player_opts(A) ->
    put_opts([{name, str_arg(A, <<"name">>, undefined)},
              {nationality, str_arg(A, <<"nationality">>, undefined)},
              {club, str_arg(A, <<"club">>, undefined)},
              {position, str_arg(A, <<"position">>, undefined)},
              {min_overall, int_arg(A, <<"min_overall">>, undefined)},
              {max_age, int_arg(A, <<"max_age">>, undefined)}]).

put_opts(L) -> maps:from_list([KV || {_, V} = KV <- L, V =/= undefined]).

str_arg(A, K, Default) ->
    case maps:get(K, A, null) of
        V when is_binary(V) ->
            case string:trim(V) of
                <<>> -> missing(K, Default);
                T -> T
            end;
        null -> missing(K, Default);
        V when is_integer(V) -> integer_to_binary(V);
        _ -> err(["Argument \"", K, "\" must be a string"])
    end.

int_arg(A, K, Default) ->
    case maps:get(K, A, null) of
        V when is_integer(V) -> V;
        V when is_float(V) -> trunc(V);
        V when is_binary(V) ->
            try binary_to_integer(string:trim(V))
            catch _:_ -> err(["Argument \"", K, "\" must be an integer"])
            end;
        null -> missing(K, Default);
        _ -> err(["Argument \"", K, "\" must be an integer"])
    end.

missing(K, required) -> err(["Missing required argument \"", K, "\""]);
missing(_, Default) -> Default.

date_arg(A, K) ->
    case str_arg(A, K, undefined) of
        undefined -> undefined;
        S ->
            case bs_data:parse_date(S) of
                undefined -> err(["Argument \"", K, "\" is not a valid date (use YYYY-MM-DD or DD/MM/YYYY)"]);
                D -> D
            end
    end.

team(A, K, Default) ->
    case str_arg(A, K, Default) of
        undefined -> undefined;
        Name ->
            case bs_team:resolve(Name) of
                {ok, Key} -> Key;
                not_found -> err(["No team matching \"", Name, "\" found in the match data"])
            end
    end.

comp(A, Default) ->
    case str_arg(A, <<"competition">>, undefined) of
        undefined -> Default;
        S ->
            case bs_query:parse_competition(S) of
                undefined -> err(["Unknown competition \"", S, "\". Use Serie A, Copa do Brasil, "
                                  "Libertadores, Serie B or Serie C"]);
                C -> C
            end
    end.

venue(A) ->
    case str_arg(A, <<"venue">>, undefined) of
        undefined -> undefined;
        <<"home">> -> home;
        <<"away">> -> away;
        <<"either">> -> undefined;
        <<"both">> -> undefined;
        V -> err(["Unknown venue \"", V, "\" (use home, away or either)"])
    end.

limit(A) ->
    case int_arg(A, <<"limit">>, undefined) of
        N when is_integer(N), N > 0 -> min(N, 500);
        _ -> ?DEFAULT_LIMIT
    end.

-spec err(iodata()) -> no_return().
err(Msg) -> throw({tool_error, Msg}).

%% --- rendering -------------------------------------------------------------

d(Key) -> bs_team:display(Key).

match_lines(Ms, Limit) ->
    [[["- ", match_text(M), "\n"] || M <- lists:sublist(Ms, Limit)], more(length(Ms), Limit)].

more(N, Limit) when N > Limit -> io_lib:format("... (~p more in dataset)~n", [N - Limit]);
more(_, _) -> [].

match_text(#{date := Date, home := H, away := A, hg := Hg, ag := Ag} = M) ->
    Score = case is_integer(Hg) andalso is_integer(Ag) of
                true -> io_lib:format("~p-~p", [Hg, Ag]);
                false -> "vs"
            end,
    io_lib:format("~s: ~s ~s ~s (~s)", [date_text(Date), d(H), Score, d(A), context(M)]).

context(#{comp := C, season := S, round := R, stage := St, extra := X}) ->
    [bs_data:comp_label(C),
     case S of undefined -> []; _ -> [" ", integer_to_binary(S)] end,
     case {St, R} of
         {undefined, undefined} -> [];
         {undefined, _} -> [" Round ", integer_to_binary(R)];
         _ -> [", ", St]
     end,
     case X of
         #{arena := Arena} when Arena =/= <<>> -> [", ", Arena];
         _ -> []
     end].

date_text(undefined) -> "date unknown";
date_text({Y, M, D}) -> io_lib:format("~4..0w-~2..0w-~2..0w", [Y, M, D]).

record_block(#{matches := N, wins := W, draws := D, losses := L, gf := F, ga := A} = R) ->
    io_lib:format("- Matches: ~p~n- Wins: ~p, Draws: ~p, Losses: ~p~n"
                  "- Goals For: ~p, Goals Against: ~p~n- Win rate: ~s%~n",
                  [N, W, D, L, F, A, win_rate(R)]).

record_line(#{matches := N, wins := W, draws := D, losses := L, gf := F, ga := A} = R) ->
    io_lib:format("~p matches, ~pW ~pD ~pL, goals ~p-~p, win rate ~s%", [N, W, D, L, F, A, win_rate(R)]).

win_rate(#{matches := 0}) -> "0.0";
win_rate(#{matches := N, wins := W}) -> io_lib:format("~.1f", [100 * W / N]).

stats_block(#{matches := N, goals := G, avg_goals := Avg, home_win_rate := HW, draw_rate := Dr,
              away_win_rate := AW}) ->
    io_lib:format("- Matches played: ~p~n- Total goals: ~p~n- Average goals per match: ~.2f~n"
                  "- Home win rate: ~.1f%~n- Draw rate: ~.1f%~n- Away win rate: ~.1f%~n",
                  [N, G, Avg, HW, Dr, AW]).

h2h_line(TA, TB, #{matches := Ms, a := #{wins := WA, draws := D, gf := GA}, b := #{wins := WB, gf := GB}}) ->
    io_lib:format("Head-to-head in dataset (~p matches): ~s ~p wins, ~s ~p wins, ~p draws; goals ~p-~p~n",
                  [length(bs_query:played(Ms)), d(TA), WA, d(TB), WB, D, GA, GB]).

rivalry(A, B) ->
    case [N || {N, X, Y} <- bs_team:rivalries(), {X, Y} =:= {min(A, B), max(A, B)}] of
        [N | _] -> [" (", N, ")"];
        [] -> []
    end.

scope(O) ->
    Parts = [case K of
                 competition -> bs_data:comp_label(V);
                 season -> integer_to_binary(V);
                 stage -> V;
                 round -> ["round ", integer_to_binary(V)];
                 date_from -> ["from ", date_text(V)];
                 date_to -> ["until ", date_text(V)]
             end || K <- [season, competition, stage, round, date_from, date_to],
                    V <- [maps:get(K, O, undefined)], V =/= undefined],
    case Parts of
        [] -> " (all data)";
        _ -> [" (", lists:join(", ", Parts), ")"]
    end.

venue_label(home) -> "home";
venue_label(away) -> "away";
venue_label(_) -> "overall".

comps(Ms) ->
    Present = lists:usort([C || #{comp := C} <- Ms]),
    [C || C <- [serie_a, copa_do_brasil, libertadores, serie_b, serie_c], lists:member(C, Present)].

seasons_text([]) -> "no seasons";
seasons_text([S]) -> integer_to_list(S);
seasons_text(Ss) -> io_lib:format("~p-~p", [hd(Ss), lists:last(Ss)]).

signed(N) when N > 0 -> ["+", integer_to_list(N)];
signed(N) -> integer_to_list(N).

numbered(Lines) ->
    [[integer_to_list(I), ". ", L, "\n"] || {I, L} <- lists:enumerate(Lines)].

player_line(#{name := N, overall := Ov, position := Pos, club := Club, nationality := Nat, age := Age}) ->
    io_lib:format("~s - Overall: ~s, Position: ~s, Club: ~s, Nationality: ~s, Age: ~s",
                  [N, val(Ov), val(Pos), val(Club), val(Nat), val(Age)]).

player_block(#{name := N, skills := Skills} = P) ->
    [io_lib:format("~s~n", [N]),
     [io_lib:format("- ~s: ~s~n", [Label, val(maps:get(K, P))])
      || {Label, K} <- [{"Nationality", nationality}, {"Club", club}, {"Position", position},
                        {"Age", age}, {"Overall", overall}, {"Potential", potential},
                        {"Jersey Number", jersey}, {"Height", height}, {"Weight", weight},
                        {"Preferred Foot", foot}, {"Value", value}, {"Wage", wage}]],
     "- Skills: ", lists:join(", ", [[S, " ", integer_to_binary(V)] || {S, V} <- Skills]), "\n"].

val(undefined) -> "n/a";
val(<<>>) -> "n/a";
val(V) when is_integer(V) -> integer_to_list(V);
val(V) -> V.

source_file(brasileirao) -> "Brasileirao_Matches.csv";
source_file(novo_brasileirao) -> "novo_campeonato_brasileiro.csv";
source_file(copa_do_brasil) -> "Brazilian_Cup_Matches.csv";
source_file(libertadores) -> "Libertadores_Matches.csv";
source_file(br_football) -> "BR-Football-Dataset.csv";
source_file(fifa_players) -> "fifa_data.csv".
