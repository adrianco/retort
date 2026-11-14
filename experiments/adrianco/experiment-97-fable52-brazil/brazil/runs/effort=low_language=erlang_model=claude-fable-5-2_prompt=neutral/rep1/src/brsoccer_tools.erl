%%% MCP tool catalogue: JSON schemas plus the implementation of every tool.
%%% call/2 takes the tool name and the decoded JSON arguments (binary keys)
%%% and returns {ok, Text} | {error, Text} where Text is a UTF-8 binary.
-module(brsoccer_tools).
-export([list/0, call/2]).

-define(DEFAULT_LIMIT, 20).

%% ---------------------------------------------------------------- schemas
list() ->
    Str = fun(D) -> #{type => <<"string">>, description => D} end,
    Int = fun(D) -> #{type => <<"integer">>, description => D} end,
    Comp = Str(<<"Competition: 'Brasileirão'/'Serie A', 'Serie B', 'Serie C', 'Copa do Brasil' or 'Libertadores'"/utf8>>),
    Season = Int(<<"Season year, e.g. 2019">>),
    Limit = Int(<<"Maximum number of rows to list (default 20)">>),
    Venue = #{type => <<"string">>, enum => [<<"home">>, <<"away">>, <<"either">>],
              description => <<"Restrict to home or away matches of the team (default either)">>},
    MatchFilters = #{competition => Comp, season => Season,
                     date_from => Str(<<"Earliest date (YYYY-MM-DD or DD/MM/YYYY)">>),
                     date_to => Str(<<"Latest date (YYYY-MM-DD or DD/MM/YYYY)">>)},
    T = fun(Name, Desc, Props, Req) ->
                #{name => Name, description => Desc,
                  inputSchema => #{type => <<"object">>, properties => Props, required => Req}}
        end,
    [T(<<"search_matches">>,
       <<"Find matches by team, opponent, competition, season, date range, round or stage "
         "(e.g. stage 'final'). Team names are normalised, so 'Palmeiras', 'Palmeiras-SP' and "
         "'palmeiras' are the same club. Results are newest first.">>,
       MatchFilters#{team => Str(<<"Team name">>), opponent => Str(<<"Opponent team name">>),
                     venue => Venue, round => Int(<<"Round number">>),
                     stage => Str(<<"Stage: 'group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final'">>),
                     source => Str(<<"Restrict to one source file: novo_campeonato, brasileirao, copa_do_brasil, libertadores, br_football">>),
                     limit => Limit}, []),
     T(<<"head_to_head">>,
       <<"Head-to-head record and match list between two teams.">>,
       MatchFilters#{team_a => Str(<<"First team">>), team_b => Str(<<"Second team">>), limit => Limit},
       [<<"team_a">>, <<"team_b">>]),
     T(<<"team_stats">>,
       <<"Win/draw/loss record, goals for/against and win rate of a team, overall, home, away "
         "and per competition. Optional season / competition / venue filters.">>,
       MatchFilters#{team => Str(<<"Team name">>), venue => Venue}, [<<"team">>]),
     T(<<"standings">>,
       <<"League table for a season calculated from match results (champion, relegation zone). "
         "For knock-out competitions use competition_bracket.">>,
       #{competition => Comp, season => Season, limit => Limit}, [<<"season">>]),
     T(<<"competition_bracket">>,
       <<"Matches of a cup season (Copa do Brasil / Libertadores) grouped by stage, with the winner of the final.">>,
       #{competition => Comp, season => Season,
         stage => Str(<<"Only show this stage (e.g. 'final')">>)}, [<<"competition">>, <<"season">>]),
     T(<<"competition_stats">>,
       <<"Aggregate statistics: matches, goals per match, home/away win rates. Filter by competition, season, team or dates.">>,
       MatchFilters#{team => Str(<<"Team name">>)}, []),
     T(<<"compare_seasons">>,
       <<"Compare two seasons of a competition: goals per match, home win rate, champion and top scoring team.">>,
       #{competition => Comp, season_a => Season, season_b => Season}, [<<"season_a">>, <<"season_b">>]),
     T(<<"biggest_wins">>,
       <<"Largest margins of victory, optionally filtered by team, competition, season or dates.">>,
       MatchFilters#{team => Str(<<"Team name">>), limit => Limit}, []),
     T(<<"team_rankings">>,
       <<"Rank teams by a metric: win_rate, points, points_per_match, goals_for, goals_against, "
         "goal_difference or wins. Use venue=home/away for best home/away records.">>,
       MatchFilters#{venue => Venue,
                     metric => #{type => <<"string">>,
                                 enum => [<<"win_rate">>, <<"points">>, <<"points_per_match">>, <<"goals_for">>,
                                          <<"goals_against">>, <<"goal_difference">>, <<"wins">>],
                                 description => <<"Ranking metric (default win_rate)">>},
                     min_matches => Int(<<"Ignore teams with fewer matches (default 10 when no season is given, else 1)">>),
                     limit => Limit}, []),
     T(<<"team_competitions">>,
       <<"List the competitions and seasons a team appears in, with its record in each.">>,
       #{team => Str(<<"Team name">>)}, [<<"team">>]),
     T(<<"derbies">>,
       <<"Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista ...), optionally for one team, season or competition.">>,
       MatchFilters#{team => Str(<<"Team name">>), limit => Limit}, []),
     T(<<"search_players">>,
       <<"Search the FIFA player database by name, nationality, club, position (code such as ST, or "
         "group: forward, midfielder, defender, goalkeeper), minimum overall rating and age. Sorted by overall rating.">>,
       #{name => Str(<<"Player name or part of it">>), nationality => Str(<<"Nationality, e.g. Brazil">>),
         club => Str(<<"Club name or part of it">>), position => Str(<<"Position code or group">>),
         min_overall => Int(<<"Minimum overall rating">>), max_age => Int(<<"Maximum age">>),
         min_age => Int(<<"Minimum age">>),
         sort => #{type => <<"string">>, enum => [<<"overall">>, <<"potential">>, <<"age">>, <<"name">>]},
         limit => Limit}, []),
     T(<<"player_details">>,
       <<"Full profile of a player (ratings, physical data, skill attributes) plus, when the club "
         "is in the match data, the club's most recent results.">>,
       #{name => Str(<<"Player name">>), club => Str(<<"Club, to disambiguate namesakes">>)}, [<<"name">>]),
     T(<<"brazilian_clubs_players">>,
       <<"Summary of FIFA players at Brazilian league clubs: squad size and average rating per club.">>,
       #{}, []),
     T(<<"dataset_summary">>,
       <<"Describe the loaded datasets: record counts per source file, competitions and season ranges.">>,
       #{}, [])].

%% --------------------------------------------------------------- dispatch
-spec call(binary(), map()) -> {ok, binary()} | {error, binary()}.
call(Name, Args) when is_map(Args) ->
    try
        ok = case brsoccer_data:ensure_loaded() of
                 ok -> ok;
                 {error, E} -> throw({bad, fmt("could not load data: ~p", [E])})
             end,
        {ok, bin(tool(Name, Args))}
    catch
        throw:{bad, Msg} -> {error, bin(Msg)}
    end;
call(_, _) -> {error, <<"arguments must be an object">>}.

tool(<<"search_matches">>, A) ->
    F = filters(A),
    Ms = brsoccer_query:find_matches(F),
    [fmt("Found ~b matches~ts:~n", [length(Ms), describe(F)]), match_lines(Ms, limit(A))];

tool(<<"head_to_head">>, A) ->
    TA = req(<<"team_a">>, A), TB = req(<<"team_b">>, A),
    F = maps:without([team, opponent, venue], filters(A)),
    case brsoccer_query:head_to_head(TA, TB, F) of
        {error, E} -> unknown(E);
        {ok, #{a := KA, b := KB, matches := Ms, record := R}} ->
            NA = names(KA), NB = names(KB),
            Derby = case {KA, KB} of
                        {[X], [Y]} -> case brsoccer_query:rivalry_name(X, Y) of
                                          undefined -> ""; N -> fmt(" (~ts)", [N])
                                      end;
                        _ -> ""
                    end,
            [fmt("~ts vs ~ts~ts~ts:~n", [NA, NB, Derby, describe(F)]),
             match_lines(Ms, limit(A)),
             fmt("~nHead-to-head in dataset (~b played): ~ts ~b wins, ~ts ~b wins, ~b draws~n"
                 "Goals: ~ts ~b, ~ts ~b~n",
                 [maps:get(matches, R), NA, maps:get(wins, R), NB, maps:get(losses, R),
                  maps:get(draws, R), NA, maps:get(gf, R), NB, maps:get(ga, R)])]
    end;

tool(<<"team_stats">>, A) ->
    Team = req(<<"team">>, A),
    F = maps:without([team], filters(A)),
    case brsoccer_query:team_stats(Team, F) of
        {error, E} -> unknown(E);
        {ok, #{team := Keys, overall := O, home := H, away := Aw, by_competition := ByC,
               extended := Ext}} ->
            Venue = maps:get(venue, F, either),
            Title = case Venue of home -> "home record"; away -> "away record"; _ -> "record" end,
            [fmt("~ts ~ts~ts:~n", [names(Keys), Title, describe(maps:without([venue], F))]),
             record_block(O),
             case Venue of
                 either -> [fmt("~nHome: ~ts~nAway: ~ts~n", [record_line(H), record_line(Aw)])];
                 _ -> []
             end,
             case ByC of
                 [_, _ | _] ->
                     ["\nBy competition:\n",
                      [fmt("- ~ts: ~ts~n", [brsoccer_norm:competition_name(C), record_line(R)])
                       || {C, R} <- ByC]];
                 _ -> []
             end,
             case Ext of
                 #{matches := N, avg_corners := AC, avg_shots := AS} when N > 0 ->
                     fmt("~nExtended stats (~b matches with data): ~.1f corners, ~.1f shots per match~n",
                         [N, AC, AS]);
                 _ -> []
             end]
    end;

tool(<<"standings">>, A) ->
    Comp = comp_default(A, serie_a),
    Season = req_int(<<"season">>, A),
    case lists:member(Comp, [copa_do_brasil, libertadores]) of
        true -> tool(<<"competition_bracket">>, A#{<<"competition">> => brsoccer_norm:competition_name(Comp)});
        false ->
            case brsoccer_query:standings(Comp, Season) of
                [] -> no_data(Comp, Season);
                Rows ->
                    N = length(Rows),
                    %% Labels only make sense for a complete double round-robin.
                    Complete = lists:all(fun(#{matches := Pl}) -> Pl =:= 2 * (N - 1) end, Rows),
                    Releg = if Comp =/= serie_a; not Complete -> 0; Season =:= 2003 -> 2; true -> 4 end,
                    Lim = case maps:is_key(<<"limit">>, A) of true -> limit(A); false -> N end,
                    [fmt("~b ~ts ~ts (calculated from matches):~n",
                         [Season, brsoccer_norm:competition_name(Comp),
                          case Complete of true -> "Final Standings"; false -> "Standings" end]),
                     [fmt("~b. ~ts - ~b pts (~bW, ~bD, ~bL) GF ~b GA ~b GD ~ts~ts~n",
                          [P, name(T), Pts, W, D, L, GF, GA, signed(GD),
                           if P =:= 1, Complete, Comp =:= serie_a -> " - Champion";
                              P =:= 1, Complete -> " - Winner";
                              P =:= 1 -> " - Leader (season incomplete in data)";
                              P > N - Releg -> " - Relegated";
                              true -> "" end])
                      || #{position := P, team := T, points := Pts, wins := W, draws := D,
                           losses := L, gf := GF, ga := GA, gd := GD} <- lists:sublist(Rows, Lim)],
                     more(N, Lim, "teams"),
                     "\nNote: computed purely from results (3 pts/win); sporting-court point "
                     "deductions are not in the data.\n"]
            end
    end;

tool(<<"competition_bracket">>, A) ->
    Comp = comp_req(A),
    Season = req_int(<<"season">>, A),
    Stage = case opt(<<"stage">>, A) of undefined -> undefined; S -> brsoccer_norm:fold(S) end,
    Groups0 = brsoccer_query:bracket(Comp, Season),
    Groups = [G || {L, _} = G <- Groups0,
                   Stage =:= undefined orelse binary:match(L, binary:part(Stage, 0, min(5, byte_size(Stage)))) =/= nomatch],
    case Groups of
        [] -> no_data(Comp, Season);
        _ ->
            [fmt("~b ~ts:~n", [Season, brsoccer_norm:competition_name(Comp)]),
             [[fmt("~n~ts (~b matches):~n", [title(L), length(Ms)]),
               [match_line(M) || M <- Ms],
               case L of <<"final">> -> final_summary(Ms); _ -> [] end]
              || {L, Ms} <- Groups]]
    end;

tool(<<"competition_stats">>, A) ->
    F = filters(A),
    #{matches := N} = S = brsoccer_query:competition_stats(F),
    case N of
        0 -> throw({bad, "No played matches match these filters."});
        _ -> [fmt("Statistics~ts:~n", [describe(F)]), stats_block(S)]
    end;

tool(<<"compare_seasons">>, A) ->
    Comp = comp_default(A, serie_a),
    SA = req_int(<<"season_a">>, A), SB = req_int(<<"season_b">>, A),
    [fmt("~ts: ~b vs ~b~n", [brsoccer_norm:competition_name(Comp), SA, SB]),
     [begin
          F = #{competition => Comp, season => S},
          St = brsoccer_query:competition_stats(F),
          case maps:get(matches, St) of
              0 -> fmt("~n~b: no data~n", [S]);
              _ ->
                  Top = case brsoccer_query:team_rankings(F#{metric => goals_for}) of
                            [#{team := T, gf := GF} | _] -> fmt("- Top scoring team: ~ts (~b goals)~n", [name(T), GF]);
                            _ -> []
                        end,
                  Champ = case lists:member(Comp, [serie_a, serie_b, serie_c]) of
                              true ->
                                  [#{team := C, points := P} | _] = brsoccer_query:standings(Comp, S),
                                  fmt("- Table leader: ~ts (~b pts)~n", [name(C), P]);
                              false -> []
                          end,
                  [fmt("~n~b:~n", [S]), stats_block(St), Champ, Top]
          end
      end || S <- [SA, SB]]];

tool(<<"biggest_wins">>, A) ->
    F = filters(A),
    Ms = brsoccer_query:biggest_wins(F, limit(A)),
    S = brsoccer_query:competition_stats(F),
    [fmt("Biggest victories~ts:~n", [describe(F)]),
     numbered([match_line_body(M) || M <- Ms]),
     fmt("~nAverage goals per match: ~.2f~nHome win rate: ~.1f%~n",
         [maps:get(goals_per_match, S), maps:get(home_win_rate, S)])];

tool(<<"team_rankings">>, A) ->
    F0 = maps:without([team], filters(A)),
    Metric = case opt(<<"metric">>, A) of
                 undefined -> win_rate;
                 M -> case lists:member(M, [<<"win_rate">>, <<"points">>, <<"points_per_match">>,
                                            <<"goals_for">>, <<"goals_against">>, <<"goal_difference">>,
                                            <<"wins">>]) of
                          true -> binary_to_atom(M);
                          false -> throw({bad, fmt("Unknown metric '~ts'", [M])})
                      end
             end,
    Min = case opt_int(<<"min_matches">>, A) of
              undefined -> case maps:is_key(season, F0) of true -> 1; false -> 10 end;
              N -> N
          end,
    Rows = brsoccer_query:team_rankings(F0#{metric => Metric, min_matches => Min}),
    Venue = maps:get(venue, F0, either),
    Lim = limit(A),
    [fmt("Team ranking by ~ts (~ts matches)~ts, min ~b matches:~n",
         [Metric, Venue, describe(maps:without([venue], F0)), Min]),
     numbered([fmt("~ts - ~ts", [name(T), record_line(R)]) || #{team := T} = R <- lists:sublist(Rows, Lim)]),
     more(length(Rows), Lim, "teams")];

tool(<<"team_competitions">>, A) ->
    Team = req(<<"team">>, A),
    case brsoccer_query:team_competitions(Team) of
        {error, E} -> unknown(E);
        {ok, Rows} ->
            [fmt("Competitions played by ~ts in the dataset:~n", [names(brsoccer_query:resolve_team(Team))]),
             [fmt("- ~ts (~ts): ~ts~n",
                  [brsoccer_norm:competition_name(C), season_range(Ss), record_line(R)])
              || #{competition := C, seasons := Ss, record := R} <- Rows]]
    end;

tool(<<"derbies">>, A) ->
    F = filters(A),
    Ds = brsoccer_query:derbies(F),
    Lim = limit(A),
    [fmt("Found ~b derby matches~ts:~n", [length(Ds), describe(F)]),
     [fmt("- ~ts [~ts]~n", [match_line_body(M), N]) || {N, M} <- lists:sublist(Ds, Lim)],
     more(length(Ds), Lim, "matches")];

tool(<<"search_players">>, A) ->
    F = player_filters(A),
    Ps = brsoccer_query:search_players(F),
    Lim = limit(A),
    case Ps of
        [] -> "No players found for these criteria.\n";
        _ ->
            [fmt("Found ~b players (sorted by ~ts):~n", [length(Ps), maps:get(sort, F, overall)]),
             numbered([player_line(P) || P <- lists:sublist(Ps, Lim)]),
             more(length(Ps), Lim, "players")]
    end;

tool(<<"player_details">>, A) ->
    Name = req(<<"name">>, A),
    F = maps:with([name, club], player_filters(A)),
    case brsoccer_query:search_players(F) of
        [] -> fmt("No player named '~ts' found.~n", [Name]);
        [P | Others] ->
            [player_profile(P),
             case Others of
                 [] -> [];
                 _ -> ["\nOther matches for this name:\n",
                       [["- ", player_line(O), "\n"] || O <- lists:sublist(Others, 10)]]
             end]
    end;

tool(<<"brazilian_clubs_players">>, _A) ->
    Rows = brsoccer_query:brazilian_club_summary(),
    Top = lists:sublist(brsoccer_query:search_players(#{nationality => <<"Brazil">>}), 10),
    ["Top-rated Brazilian players in dataset:\n",
     numbered([player_line(P) || P <- Top]),
     "\nPlayers at Brazilian clubs (FIFA data):\n",
     [fmt("- ~ts: ~b players, ~b Brazilian (avg rating: ~.1f)~n", [C, N, B, Avg])
      || #{club := C, players := N, brazilians := B, avg_overall := Avg} <- Rows]];

tool(<<"dataset_summary">>, _A) ->
    #{matches_by_source := BySrc, unique_matches := U, total_match_records := T,
      teams := Teams, players := Ps} = brsoccer_data:summary(),
    Files = maps:from_list(brsoccer_data:sources()),
    ["Brazilian soccer datasets loaded:\n",
     [fmt("- ~ts (~ts): ~b match records~n", [maps:get(S, Files), S, N])
      || {S, N} <- lists:sort(maps:to_list(BySrc))],
     fmt("- ~ts (fifa): ~b players~n", [maps:get(fifa, Files), Ps]),
     fmt("~nMatch records: ~b (~b unique after removing cross-file duplicates)~nTeams: ~b~n",
         [T, U, Teams]),
     "\nCompetitions:\n",
     [fmt("- ~ts: seasons ~ts~n", [brsoccer_norm:competition_name(C),
                                   season_range(brsoccer_query:seasons(C))])
      || C <- [serie_a, serie_b, serie_c, copa_do_brasil, libertadores]]];

tool(Name, _) ->
    throw({bad, fmt("Unknown tool '~ts'", [Name])}).

%% ---------------------------------------------------------------- helpers
fmt(F, A) -> io_lib:format(F, A).
bin(IoData) -> unicode:characters_to_binary(IoData).

opt(K, A) ->
    case maps:get(K, A, undefined) of
        null -> undefined;
        <<>> -> undefined;
        V when is_binary(V) -> case string:trim(V) of <<>> -> undefined; T -> T end;
        V -> V
    end.

req(K, A) ->
    case opt(K, A) of
        V when is_binary(V) -> V;
        undefined -> throw({bad, fmt("Missing required argument '~ts'", [K])});
        _ -> throw({bad, fmt("Argument '~ts' must be a string", [K])})
    end.

opt_int(K, A) ->
    case opt(K, A) of
        undefined -> undefined;
        V ->
            case brsoccer_norm:to_int(V) of
                undefined -> throw({bad, fmt("Argument '~ts' must be an integer", [K])});
                I -> I
            end
    end.

req_int(K, A) ->
    case opt_int(K, A) of
        undefined -> throw({bad, fmt("Missing required argument '~ts'", [K])});
        I -> I
    end.

limit(A) ->
    case opt_int(<<"limit">>, A) of
        undefined -> ?DEFAULT_LIMIT;
        N when N < 1 -> 1;
        N -> min(N, 500)
    end.

comp(A) ->
    case opt(<<"competition">>, A) of
        undefined -> undefined;
        V when is_binary(V) ->
            case brsoccer_norm:competition(V) of
                unknown -> throw({bad, fmt("Unknown competition '~ts'. Use Brasileirão, Serie B, "
                                           "Serie C, Copa do Brasil or Libertadores.", [V])});
                C -> C
            end;
        _ -> throw({bad, "Argument 'competition' must be a string"})
    end.

comp_default(A, Def) -> case comp(A) of undefined -> Def; C -> C end.
comp_req(A) ->
    case comp(A) of
        undefined -> throw({bad, "Missing required argument 'competition'"});
        C -> C
    end.

date(K, A) ->
    case opt(K, A) of
        undefined -> undefined;
        V when is_binary(V) ->
            case brsoccer_norm:parse_date(V) of
                {D, _} -> D;
                undefined ->
                    case {brsoccer_norm:to_int(V), K} of
                        {Y, <<"date_from">>} when is_integer(Y), Y > 1800 -> {Y, 1, 1};
                        {Y, <<"date_to">>} when is_integer(Y), Y > 1800 -> {Y, 12, 31};
                        _ -> throw({bad, fmt("Invalid date '~ts' for '~ts' (use YYYY-MM-DD or DD/MM/YYYY)", [V, K])})
                    end
            end;
        _ -> throw({bad, fmt("Argument '~ts' must be a string", [K])})
    end.

team_arg(K, A) ->
    case opt(K, A) of
        undefined -> undefined;
        V when is_binary(V) ->
            case brsoccer_query:resolve_team(V) of
                [] -> unknown({unknown_team, V});
                Keys -> Keys
            end;
        _ -> throw({bad, fmt("Argument '~ts' must be a string", [K])})
    end.

filters(A) ->
    Venue = case opt(<<"venue">>, A) of
                undefined -> undefined;
                <<"home">> -> home;
                <<"away">> -> away;
                <<"either">> -> undefined;
                <<"both">> -> undefined;
                V -> throw({bad, fmt("Invalid venue '~ts' (home, away or either)", [V])})
            end,
    Source = case opt(<<"source">>, A) of
                 undefined -> undefined;
                 S ->
                     case [K || {K, _} <- brsoccer_data:sources(), K =/= fifa, atom_to_binary(K) =:= S] of
                         [K] -> K;
                         [] -> throw({bad, fmt("Unknown source '~ts'", [S])})
                     end
             end,
    maps:filter(fun(_, V) -> V =/= undefined end,
                #{team => team_arg(<<"team">>, A), opponent => team_arg(<<"opponent">>, A),
                  venue => Venue, competition => comp(A), season => opt_int(<<"season">>, A),
                  date_from => date(<<"date_from">>, A), date_to => date(<<"date_to">>, A),
                  round => opt_int(<<"round">>, A), stage => opt(<<"stage">>, A),
                  source => Source}).

player_filters(A) ->
    Sort = case opt(<<"sort">>, A) of
               undefined -> undefined;
               S -> case lists:member(S, [<<"overall">>, <<"potential">>, <<"age">>, <<"name">>]) of
                        true -> binary_to_atom(S);
                        false -> throw({bad, fmt("Invalid sort '~ts'", [S])})
                    end
           end,
    Str = fun(K) -> case opt(K, A) of
                        V when is_binary(V); V =:= undefined -> V;
                        _ -> throw({bad, fmt("Argument '~ts' must be a string", [K])})
                    end
          end,
    maps:filter(fun(_, V) -> V =/= undefined end,
                #{name => Str(<<"name">>), nationality => Str(<<"nationality">>),
                  club => Str(<<"club">>), position => Str(<<"position">>),
                  min_overall => opt_int(<<"min_overall">>, A), max_age => opt_int(<<"max_age">>, A),
                  min_age => opt_int(<<"min_age">>, A), sort => Sort}).

-spec unknown(term()) -> no_return().
unknown({unknown_team, T}) ->
    throw({bad, fmt("No team matching '~ts' found in the match data.", [T])}).

no_data(Comp, Season) ->
    Ss = brsoccer_query:seasons(Comp),
    throw({bad, fmt("No ~ts data for season ~b (available: ~ts).",
                    [brsoccer_norm:competition_name(Comp), Season, season_range(Ss)])}).

name(Key) -> brsoccer_data:display(Key).
names(Keys) when length(Keys) > 3 ->
    [names(lists:sublist(Keys, 3)), fmt(" (+~b more)", [length(Keys) - 3])];
names(Keys) -> lists:join(" / ", [name(K) || K <- Keys]).

describe(F) ->
    Parts = [case K of
                 team -> fmt("team ~ts", [names(V)]);
                 opponent -> fmt("against ~ts", [names(V)]);
                 venue -> fmt("~ts only", [V]);
                 competition -> brsoccer_norm:competition_name(V);
                 season -> fmt("season ~b", [V]);
                 date_from -> fmt("from ~ts", [brsoccer_norm:format_date(V)]);
                 date_to -> fmt("until ~ts", [brsoccer_norm:format_date(V)]);
                 round -> fmt("round ~b", [V]);
                 stage -> fmt("stage ~ts", [V]);
                 source -> fmt("source ~ts", [V])
             end || K <- [team, opponent, venue, competition, season, date_from, date_to, round,
                          stage, source],
                    V <- [maps:get(K, F, undefined)], V =/= undefined],
    case Parts of
        [] -> " (all data)";
        _ -> [" (", lists:join(", ", Parts), ")"]
    end.

match_lines(Ms, Lim) ->
    [[match_line(M) || M <- lists:sublist(Ms, Lim)], more(length(Ms), Lim, "matches")].

more(N, Lim, What) when N > Lim -> fmt("... (~b more ~ts in dataset)~n", [N - Lim, What]);
more(_, _, _) -> [].

match_line(M) -> ["- ", match_line_body(M), "\n"].

match_line_body(#{date := D, home := H, away := A, hg := HG, ag := AG, comp := C, season := S,
                  round := R, stage := St, arena := Arena}) ->
    Score = case is_integer(HG) andalso is_integer(AG) of
                true -> fmt("~b-~b", [HG, AG]);
                false -> "vs"
            end,
    Extra = [case S of undefined -> []; _ -> fmt(" ~b", [S]) end,
             case {St, R} of
                 {undefined, undefined} -> [];
                 {undefined, _} -> fmt(" Round ~b", [R]);
                 _ -> fmt(" ~ts", [St])
             end,
             case Arena of undefined -> []; _ -> fmt(", ~ts", [Arena]) end],
    fmt("~ts: ~ts ~ts ~ts (~ts~ts)",
        [brsoccer_norm:format_date(D), name(H), Score, name(A), brsoccer_norm:competition_name(C), Extra]).

numbered(Lines) ->
    {Out, _} = lists:mapfoldl(fun(L, I) -> {fmt("~b. ~ts~n", [I, L]), I + 1} end, 1, Lines),
    Out.

record_block(#{matches := N, wins := W, draws := D, losses := L, gf := GF, ga := GA,
               win_rate := WR, points := P}) ->
    fmt("- Matches: ~b~n- Wins: ~b, Draws: ~b, Losses: ~b~n- Goals For: ~b, Goals Against: ~b "
        "(difference ~ts)~n- Points: ~b~n- Win rate: ~.1f%~n", [N, W, D, L, GF, GA, signed(GF - GA), P, WR]).

record_line(#{matches := N, wins := W, draws := D, losses := L, gf := GF, ga := GA, win_rate := WR}) ->
    fmt("~b matches, ~bW ~bD ~bL, goals ~b:~b, win rate ~.1f%", [N, W, D, L, GF, GA, WR]).

stats_block(#{matches := N, goals := G, goals_per_match := GPM, home_wins := HW, away_wins := AW,
              draws := D, home_win_rate := HR, away_win_rate := AR, draw_rate := DR,
              home_goals := HG, away_goals := AG}) ->
    fmt("- Matches: ~b~n- Goals: ~b (home ~b, away ~b)~n- Average goals per match: ~.2f~n"
        "- Home wins: ~b (~.1f%)~n- Draws: ~b (~.1f%)~n- Away wins: ~b (~.1f%)~n",
        [N, G, HG, AG, GPM, HW, HR, D, DR, AW, AR]).

signed(N) when N > 0 -> fmt("+~b", [N]);
signed(N) -> fmt("~b", [N]).

season_range([]) -> "none";
season_range([S]) -> fmt("~b", [S]);
season_range(Ss) -> fmt("~b-~b", [hd(Ss), lists:last(Ss)]).

title(<<C, Rest/binary>>) when C >= $a, C =< $z -> <<(C - 32), Rest/binary>>;
title(B) -> B.

%% Aggregate score of the final leg(s) and the winner when decidable.
final_summary(Ms) ->
    Played = [M || #{hg := HG, ag := AG} = M <- Ms, is_integer(HG), is_integer(AG)],
    case Played of
        [] -> "Result of the final is not available in the data.\n";
        [#{home := T1, away := T2} | _] ->
            {G1, G2} = lists:foldl(fun(#{home := H, hg := HG, ag := AG}, {X, Y}) ->
                                           case H of T1 -> {X + HG, Y + AG}; _ -> {X + AG, Y + HG} end
                                   end, {0, 0}, Played),
            if G1 > G2 -> fmt("Champion: ~ts (~b-~b on aggregate)~n", [name(T1), G1, G2]);
               G2 > G1 -> fmt("Champion: ~ts (~b-~b on aggregate)~n", [name(T2), G2, G1]);
               true -> fmt("Aggregate ~b-~b: decided by a tie-breaker (penalties/away goals) "
                           "not recorded in the data.~n", [G1, G2])
            end
    end.

player_line(#{name := N, overall := O, position := Pos, club := Club, nationality := Nat, age := Age}) ->
    fmt("~ts - Overall: ~ts, Position: ~ts, Club: ~ts, Nationality: ~ts, Age: ~ts",
        [N, show(O), show(Pos), show(Club), Nat, show(Age)]).

show(undefined) -> "n/a";
show(<<>>) -> "n/a";
show(I) when is_integer(I) -> integer_to_list(I);
show(B) -> B.

player_profile(#{name := N, skills := Skills, club := Club, club_key := CK} = P) ->
    Top = lists:sublist(lists:sort(fun({_, A}, {_, B}) -> A >= B end, maps:to_list(Skills)), 8),
    Recent = case Club =/= <<>> andalso maps:is_key(CK, brsoccer_data:teams()) of
                 true -> lists:sublist(brsoccer_query:find_matches(#{team => [CK], played_only => true}), 5);
                 false -> []
             end,
    [fmt("~ts~n- Age: ~ts~n- Nationality: ~ts~n- Club: ~ts~n- Position: ~ts (jersey ~ts)~n"
         "- Overall: ~ts, Potential: ~ts~n- Height: ~ts, Weight: ~ts, Preferred foot: ~ts~n"
         "- Value: ~ts, Wage: ~ts~n",
         [N | [show(maps:get(K, P)) || K <- [age, nationality, club, position, jersey, overall,
                                             potential, height, weight, foot, value, wage]]]),
     case Top of
         [] -> [];
         _ -> ["- Best attributes: ", lists:join(", ", [fmt("~ts ~b", [S, V]) || {S, V} <- Top]), "\n"]
     end,
     case Recent of
         [] -> [];
         _ -> [fmt("~nMost recent matches of ~ts in the match data:~n", [name(CK)]),
               [match_line(M) || M <- Recent]]
     end].
