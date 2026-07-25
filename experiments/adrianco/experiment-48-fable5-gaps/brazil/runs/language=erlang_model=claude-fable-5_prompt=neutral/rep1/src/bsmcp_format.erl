%% Renders query results as human-readable UTF-8 text, in the answer style
%% shown in the specification.
-module(bsmcp_format).

-export([matches/2, team_stats/1, standings/2, players/2, league_stats/1,
         biggest_wins/2, data_summary/1, match_line/1]).

bin(IoList) -> unicode:characters_to_binary(IoList).

%%% Matches --------------------------------------------------------------------

matches(Result = #{matches := Ms, total := Total}, Limit) ->
    Shown = lists:sublist(Ms, Limit),
    Header =
        case Result of
            #{team1_display := D1, team2_display := D2} ->
                io_lib:format("~ts vs ~ts: ~b match(es) found~n", [D1, D2, Total]);
            #{team1_display := D1} ->
                io_lib:format("~ts: ~b match(es) found~n", [D1, Total]);
            _ ->
                io_lib:format("~b match(es) found~n", [Total])
        end,
    Lines = [["- ", match_line(M), "\n"] || M <- Shown],
    More = case Total - length(Shown) of
               N when N > 0 -> io_lib:format("... (~b more match(es) in dataset; raise 'limit' to see more)~n", [N]);
               _ -> []
           end,
    H2H = case Result of
              #{h2h := S, team1_display := T1, team2_display := T2} ->
                  io_lib:format(
                    "~nHead-to-head: ~ts ~b wins, ~ts ~b wins, ~b draws "
                    "(goals ~b-~b)~n",
                    [T1, maps:get(t1_wins, S), T2, maps:get(t2_wins, S),
                     maps:get(draws, S), maps:get(t1_goals, S),
                     maps:get(t2_goals, S)]);
              _ -> []
          end,
    bin([Header, Lines, More, H2H]).

match_line(M = #{home := H, away := A, hg := HG, ag := AG}) ->
    Score = case {HG, AG} of
                {undefined, _} -> "vs";
                {_, undefined} -> "vs";
                _ -> io_lib:format("~b-~b", [HG, AG])
            end,
    Ctx = context(M),
    Arena = case maps:get(arena, M, undefined) of
                undefined -> [];
                Ar -> io_lib:format(" @ ~ts", [Ar])
            end,
    io_lib:format("~ts: ~ts ~s ~ts (~ts)~ts",
                  [bsmcp_names:format_date(maps:get(date, M)),
                   string:trim(H), Score, string:trim(A), Ctx, Arena]).

context(M) ->
    Comp = maps:get(competition, M),
    Parts =
        case {maps:get(stage, M, undefined), maps:get(round, M, undefined)} of
            {undefined, undefined} -> [Comp];
            {undefined, R} -> [Comp, io_lib:format(", Round ~p", [R])];
            {S, _} -> [Comp, ", ", S]
        end,
    Season = case maps:get(season, M, undefined) of
                 undefined -> [];
                 Y -> io_lib:format(" ~b", [Y])
             end,
    [Parts, Season].

%%% Team statistics ------------------------------------------------------------

team_stats(#{team := Team, overall := O, home := H, away := A,
             competitions := Comps, venue := Venue}) ->
    VenueTxt = case Venue of
                   <<"home">> -> " (home matches only)";
                   <<"away">> -> " (away matches only)";
                   _ -> ""
               end,
    Block = fun(Label, #{played := P, wins := W, draws := D, losses := L,
                         gf := GF, ga := GA}) ->
                    io_lib:format(
                      "~s: ~b matches - ~b W, ~b D, ~b L | goals for ~b, "
                      "against ~b | win rate ~.1f%~n",
                      [Label, P, W, D, L, GF, GA, win_rate(W, P)])
            end,
    Splits = case Venue of
                 <<"all">> ->
                     [Block("  Home", H), Block("  Away", A)];
                 _ -> []
             end,
    CompTxt = case Comps of
                  [] -> "";
                  _ -> io_lib:format("Competitions: ~ts~n",
                                     [lists:join(", ", Comps)])
              end,
    bin([io_lib:format("~ts record~s:~n", [Team, VenueTxt]),
         Block("Overall", O), Splits, CompTxt]).

win_rate(_, 0) -> 0.0;
win_rate(W, P) -> 100.0 * W / P.

%%% Standings ------------------------------------------------------------------

standings(#{competition := Comp, season := Season, rows := Rows,
            matches := N}, Limit) ->
    case Rows of
        [] ->
            bin(io_lib:format("No ~ts matches found for season ~p.~n",
                              [Comp, Season]));
        _ ->
            Shown = lists:sublist(Rows, Limit),
            Header = io_lib:format(
                       "~ts ~p standings (computed from ~b matches):~n",
                       [Comp, Season, N]),
            Lines = [standings_line(I, R) ||
                        {I, R} <- lists:enumerate(Shown)],
            Note = case length(Rows) - length(Shown) of
                       0 -> [];
                       More -> io_lib:format("... (~b more teams)~n", [More])
                   end,
            bin([Header, Lines, Note])
    end.

standings_line(I, R) ->
    Tag = case I of 1 -> " - Champion"; _ -> "" end,
    io_lib:format(
      "~2b. ~ts - ~b pts (~bW ~bD ~bL, GF ~b, GA ~b, GD ~s~b)~s~n",
      [I, maps:get(display, R), maps:get(pts, R), maps:get(wins, R),
       maps:get(draws, R), maps:get(losses, R), maps:get(gf, R),
       maps:get(ga, R),
       case maps:get(gd, R) >= 0 of true -> "+"; false -> "" end,
       maps:get(gd, R), Tag]).

%%% Players --------------------------------------------------------------------

players(Ps, Limit) ->
    Total = length(Ps),
    Shown = lists:sublist(Ps, Limit),
    case Total of
        0 ->
            <<"No players found. Note: the FIFA 19 dataset does not license "
              "Brazilian league clubs, so club searches work best with "
              "European/international clubs; try searching by name or "
              "nationality instead.">>;
        _ ->
            Header = io_lib:format("~b player(s) found:~n", [Total]),
            Lines = [player_line(I, P) || {I, P} <- lists:enumerate(Shown)],
            More = case Total - length(Shown) of
                       0 -> [];
                       N -> io_lib:format("... (~b more; raise 'limit' to see more)~n", [N])
                   end,
            bin([Header, Lines, More])
    end.

player_line(I, P) ->
    io_lib:format(
      "~2b. ~ts - Overall: ~p, Potential: ~p, Position: ~ts, Age: ~p, "
      "Nationality: ~ts, Club: ~ts~n",
      [I, maps:get(name, P), maps:get(overall, P), maps:get(potential, P),
       or_dash(maps:get(position, P)), maps:get(age, P),
       maps:get(nationality, P), or_dash(maps:get(club, P))]).

or_dash(<<>>) -> <<"-">>;
or_dash(B) -> B.

%%% League stats ---------------------------------------------------------------

league_stats(#{matches := N, goals := G, avg_goals := Avg, home_wins := HW,
               draws := D, away_wins := AW, home_win_pct := HP,
               draw_pct := DP, away_win_pct := AP}) ->
    bin(io_lib:format(
          "Matches with results: ~b~n"
          "Total goals: ~b (average ~.2f per match)~n"
          "Home wins: ~b (~.1f%), Draws: ~b (~.1f%), Away wins: ~b (~.1f%)~n",
          [N, G, Avg, HW, HP, D, DP, AW, AP])).

%%% Biggest wins ---------------------------------------------------------------

biggest_wins(Ms, Limit) ->
    Shown = lists:sublist(Ms, Limit),
    Lines = [io_lib:format("~2b. ~ts~n", [I, match_line(M)])
             || {I, M} <- lists:enumerate(Shown)],
    bin([io_lib:format("Biggest victories (~b shown):~n", [length(Shown)]),
         Lines]).

%%% Data summary ---------------------------------------------------------------

data_summary(S = #{competitions := Comps}) ->
    CompLines =
        [io_lib:format("- ~ts: ~b matches (seasons ~ts-~ts)~n",
                       [C, Cnt, opt_int(Min), opt_int(Max)])
         || {C, {Cnt, Min, Max}} <- lists:sort(maps:to_list(Comps))],
    bin([io_lib:format(
           "Brazilian Soccer dataset summary:~n"
           "Total matches: ~b (~b cross-source duplicates skipped)~n"
           "Teams: ~b | FIFA players: ~b~n"
           "Competitions:~n",
           [maps:get(matches, S), maps:get(duplicates_skipped, S),
            maps:get(teams, S), maps:get(players, S)]),
         CompLines]).

opt_int(undefined) -> <<"?">>;
opt_int(I) -> integer_to_binary(I).
