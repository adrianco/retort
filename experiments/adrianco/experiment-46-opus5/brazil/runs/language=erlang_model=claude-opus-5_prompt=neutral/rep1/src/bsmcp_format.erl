%%%-------------------------------------------------------------------
%%% @doc Human readable rendering of query results.
%%%
%%% Context: an MCP tool result carries both `structuredContent' (the
%%% raw map, for programmatic use) and a `text' block.  The text block
%%% is what the LLM reads most of the time, so it is written in the
%%% answer shapes the specification asks for - score lines, league
%%% tables, win/loss summaries - rather than as pretty printed JSON.
%%% Everything is UTF-8; Brazilian club names keep their accents.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_format).

-export([render/2, match_line/1, error_text/1]).

%%====================================================================
%% API
%%====================================================================

-spec render(atom(), map()) -> binary().
render(Tool, Result) ->
    to_bin(lines(Tool, Result)).

-spec error_text(map()) -> binary().
error_text(E = #{error := unknown_team}) ->
    Suggestions = maps:get(suggestions, E, []),
    to_bin([io_lib:format("No team matched \"~ts\".", [maps:get(query, E, <<>>)]),
            case Suggestions of
                [] -> "Try list_teams to browse the clubs in the dataset.";
                _ -> io_lib:format("Did you mean: ~ts?", [join(Suggestions, <<", ">>)])
            end]);
error_text(E = #{error := unknown_competition}) ->
    Available = [maps:get(name, C) || C <- maps:get(available, E, [])],
    to_bin([io_lib:format("Unknown competition \"~ts\".", [maps:get(query, E, <<>>)]),
            io_lib:format("Available: ~ts", [join(Available, <<", ">>)])]);
error_text(E = #{error := no_squad_data}) ->
    Clubs = [io_lib:format("~ts (~b)", [maps:get(club, C), maps:get(players, C)])
             || C <- lists:sublist(maps:get(clubs_with_squads, E, []), 20)],
    to_bin([maps:get(message, E, <<>>),
            io_lib:format("Brazilian clubs that do have squads: ~ts",
                          [join([iolist_to_binary(C) || C <- Clubs], <<", ">>)])]);
error_text(E = #{error := missing_season}) ->
    to_bin([maps:get(message, E, <<"A season is required">>),
            io_lib:format("Seasons in the dataset: ~ts",
                          [join([bsmcp_text:bin(S)
                                 || S <- maps:get(available_seasons, E, [])], <<", ">>)])]);
error_text(E) ->
    to_bin([maps:get(message, E, <<"Query failed">>)]).

%%====================================================================
%% Per tool rendering
%%====================================================================

lines(search_matches, #{total := 0}) ->
    ["No matches found for those filters."];
lines(search_matches, #{total := Total, matches := Matches, filters := F}) ->
    [io_lib:format("~ts~n~b matching fixtures (showing ~b)",
                   [filter_header(F), Total, length(Matches)])
     | [["  ", match_line(M)] || M <- Matches]];

lines(head_to_head, R) ->
    #{team_a := #{name := A}, team_b := #{name := B}, summary := S,
      by_competition := ByComp, matches := Matches} = R,
    #{matches := N, team_a_wins := WA, team_b_wins := WB, draws := D,
      team_a_goals := GA, team_b_goals := GB} = S,
    [io_lib:format("~ts vs ~ts - head to head", [A, B]),
     io_lib:format("~b matches in the dataset: ~ts ~b wins, ~ts ~b wins, ~b draws",
                   [N, A, WA, B, WB, D]),
     io_lib:format("Goals: ~ts ~b, ~ts ~b", [A, GA, B, GB]),
     "By competition:"
     | [io_lib:format("  ~ts: ~b matches (~bW ~bD ~bL for ~ts)",
                      [maps:get(competition_name, C), maps:get(matches, C),
                       maps:get(wins, C), maps:get(draws, C), maps:get(losses, C), A])
        || C <- ByComp]]
        ++ ["Most recent:" | [["  ", match_line(M)] || M <- Matches]];

lines(team_stats, R) ->
    #{team := #{name := Name}, record := Rec, filters := F, by_competition := ByComp} = R,
    [io_lib:format("~ts~ts", [Name, scope_suffix(F)]) | record_lines(Rec)]
        ++ case ByComp of
               [_, _ | _] ->
                   ["By competition:"
                    | [io_lib:format("  ~ts: ~b played, ~bW ~bD ~bL, ~b:~b",
                                     [maps:get(competition_name, C),
                                      maps:get(played, maps:get(record, C)),
                                      maps:get(wins, maps:get(record, C)),
                                      maps:get(draws, maps:get(record, C)),
                                      maps:get(losses, maps:get(record, C)),
                                      maps:get(goals_for, maps:get(record, C)),
                                      maps:get(goals_against, maps:get(record, C))])
                       || C <- ByComp]];
               _ ->
                   []
           end;

lines(team_profile, R) ->
    #{team := Team, record := Rec, competitions := Comps, seasons := Seasons,
      first_match := First, last_match := Last, biggest_win := Big,
      squad_size := Squad, top_players := Players} = R,
    #{name := Name, state := State, matches := N} = Team,
    [io_lib:format("~ts~ts - ~b matches in the dataset",
                   [Name, case State of undefined -> ""; _ -> [" (", State, ")"] end, N])
     | record_lines(Rec)]
        ++ [io_lib:format("Seasons: ~ts", [range_text(Seasons)]),
            "Competitions:"]
        ++ [io_lib:format("  ~ts: ~b matches, ~bW ~bD ~bL (seasons ~ts)",
                          [maps:get(competition_name, C), maps:get(matches, C),
                           maps:get(wins, maps:get(record, C)),
                           maps:get(draws, maps:get(record, C)),
                           maps:get(losses, maps:get(record, C)),
                           range_text(maps:get(seasons, C))]) || C <- Comps]
        ++ optional_line("First match: ", First)
        ++ optional_line("Last match:  ", Last)
        ++ optional_line("Biggest win: ", Big)
        ++ case Players of
               [] -> [];
               _ -> [io_lib:format("FIFA squad: ~b players", [Squad])
                     | [["  ", player_line(P)] || P <- Players]]
           end;

lines(standings, #{table := []} = R) ->
    [io_lib:format("No matches loaded for ~ts ~ts.",
                   [maps:get(competition_name, R), bsmcp_text:bin(maps:get(season, R))])];
lines(standings, R) ->
    #{competition_name := Comp, season := Season, table := Table,
      matches := N, complete := Complete, champion := Champion,
      relegated := Relegated} = R,
    Header = io_lib:format("~ts ~ts ~ts (calculated from ~b matches)",
                           [bsmcp_text:bin(Season), Comp,
                            case Complete of
                                true -> "final standings";
                                false -> "standings so far - the dataset is "
                                         "missing some fixtures"
                            end, N]),
    Rows = [io_lib:format("~3.b. ~-24ts ~3.b pts (~bW ~bD ~bL) ~b:~b ~s~b~ts",
                          [maps:get(position, Row), maps:get(team_name, Row),
                           maps:get(points, Row), maps:get(wins, Row),
                           maps:get(draws, Row), maps:get(losses, Row),
                           maps:get(goals_for, Row), maps:get(goals_against, Row),
                           case maps:get(goal_difference, Row) >= 0 of
                               true -> "+"; false -> ""
                           end,
                           maps:get(goal_difference, Row),
                           case {Champion, maps:get(position, Row)} of
                               {undefined, _} -> "";
                               {_, 1} -> " - Champion";
                               _ -> ""
                           end])
            || Row <- Table],
    [Header | Rows]
        ++ case Relegated of
               undefined -> [];
               _ -> [io_lib:format("Relegated: ~ts", [join(Relegated, <<", ">>)])]
           end
        ++ case maps:get(excluded_teams, R, []) of
               [] -> [];
               Ex -> [io_lib:format("Excluded (too few matches, likely mislabelled in "
                                    "the source data): ~ts",
                                    [join([maps:get(team, E) || E <- Ex], <<", ">>)])]
           end;

lines(competition_stats, #{overall := #{matches := 0}}) ->
    ["No played matches for those filters."];
lines(competition_stats, #{overall := O, by_season := BySeason, filters := F}) ->
    [filter_header(F) | stats_lines(O)]
        ++ case BySeason of
               [_, _ | _] ->
                   ["By season:"
                    | [io_lib:format("  ~ts: ~b matches, ~.2f goals/match, "
                                     "home wins ~.1f%, draws ~.1f%",
                                     [bsmcp_text:bin(S), maps:get(matches, St),
                                      float(maps:get(goals_per_match, St)),
                                      float(maps:get(home_win_pct, St)),
                                      float(maps:get(draw_pct, St))])
                       || #{season := S, stats := St} <- BySeason]];
               _ ->
                   []
           end;

lines(Tool, #{leaderboard := []}) when Tool =:= leaderboard; Tool =:= league_leaderboard ->
    ["No teams match those filters."];
lines(Tool, #{metric := Metric, leaderboard := Rows, filters := F})
  when Tool =:= leaderboard; Tool =:= league_leaderboard ->
    [io_lib:format("~ts ranked by ~ts", [filter_header(F), Metric])
     | [io_lib:format("~3.b. ~-24ts ~ts (~b played, ~bW ~bD ~bL, ~b:~b)",
                      [Pos, maps:get(team_name, R), number(maps:get(value, R)),
                       maps:get(played, R), maps:get(wins, R), maps:get(draws, R),
                       maps:get(losses, R), maps:get(goals_for, R),
                       maps:get(goals_against, R)])
        || {Pos, R} <- enumerate(Rows)]];

lines(biggest_wins, #{matches := []}) ->
    ["No matches found for those filters."];
lines(biggest_wins, #{matches := Matches, filters := F}) ->
    [io_lib:format("~ts - biggest winning margins", [filter_header(F)])
     | [io_lib:format("~3.b. ~ts", [Pos, match_line(M)]) || {Pos, M} <- enumerate(Matches)]];

lines(search_players, #{total := 0}) ->
    ["No players match those filters."];
lines(search_players, #{total := Total, players := Players}) ->
    [io_lib:format("~b players match (showing ~b)", [Total, length(Players)])
     | [[" ", integer_to_list(Pos), ". ", player_line(P)] || {Pos, P} <- enumerate(Players)]];

lines(player_profile, #{player := P, also_matching := Others}) ->
    #{name := Name, age := Age, nationality := Nat, club := Club,
      position := Pos, overall := Overall, potential := Potential} = P,
    [io_lib:format("~ts - ~ts, age ~ts, ~ts",
                   [Name, opt(Nat), opt(Age), opt(Club)]),
     io_lib:format("Overall ~ts, potential ~ts, position ~ts, shirt ~ts",
                   [opt(Overall), opt(Potential), opt(Pos),
                    opt(maps:get(jersey_number, P, undefined))]),
     io_lib:format("Height ~ts, weight ~ts, foot ~ts, value ~ts, wage ~ts",
                   [opt(maps:get(height, P, undefined)), opt(maps:get(weight, P, undefined)),
                    opt(maps:get(preferred_foot, P, undefined)),
                    opt(maps:get(value, P, undefined)), opt(maps:get(wage, P, undefined))])]
        ++ case top_skills(maps:get(skills, P, #{})) of
               [] -> [];
               Skills -> [io_lib:format("Top attributes: ~ts", [join(Skills, <<", ">>)])]
           end
        ++ case Others of
               [] -> [];
               _ -> [io_lib:format("Also matching: ~ts",
                                   [join([N || #{name := N} <- Others], <<", ">>)])]
           end;

lines(club_squad, R) ->
    #{club := Club, squad_size := N, summary := S, players := Players} = R,
    [io_lib:format("~ts - ~b players in the FIFA dataset (avg rating ~ts, avg age ~ts)",
                   [Club, N, opt(maps:get(avg_overall, S, undefined)),
                    opt(maps:get(avg_age, S, undefined))])
     | [[" ", integer_to_list(Pos), ". ", player_line(P)] || {Pos, P} <- enumerate(Players)]];

lines(club_ratings, #{clubs := []}) ->
    ["No clubs match those filters."];
lines(club_ratings, #{total_clubs := Total, clubs := Clubs}) ->
    [io_lib:format("~b clubs (showing ~b), ranked by average rating",
                   [Total, length(Clubs)])
     | [io_lib:format("  ~ts: ~b players (avg rating ~ts, best ~ts)",
                      [maps:get(club, C), maps:get(players, C),
                       opt(maps:get(avg_overall, C, undefined)),
                       opt(maps:get(top_player, C, undefined))])
        || C <- Clubs]];

lines(list_teams, #{teams := []}) ->
    ["No teams match that query."];
lines(list_teams, #{total := Total, teams := Teams}) ->
    [io_lib:format("~b teams (showing ~b)", [Total, length(Teams)])
     | [io_lib:format("  ~ts~ts - ~b matches; spellings in the data: ~ts",
                      [maps:get(name, T),
                       case maps:get(state, T) of
                           undefined -> "";
                           S -> [" (", S, ")"]
                       end,
                       maps:get(matches, T),
                       join(maps:get(name_variants, T, []), <<" | ">>)])
        || T <- Teams]];

lines(dataset_summary, S) ->
    #{matches := M, teams := T, players := P, files := Files,
      competitions := Comps, source_rows := Rows, load_time_ms := Ms} = S,
    [io_lib:format("Brazilian soccer knowledge graph: ~b matches, ~b teams, "
                   "~b players", [M, T, P]),
     io_lib:format("~b source rows loaded in ~b ms from ~ts",
                   [Rows, Ms, maps:get(data_dir, S, <<>>)]),
     "Files:"]
        ++ [io_lib:format("  ~ts: ~b rows", [maps:get(file, F), maps:get(rows, F)])
            || F <- Files]
        ++ ["Competitions (after de-duplicating overlapping sources):"]
        ++ [io_lib:format("  ~ts: ~b matches, seasons ~ts",
                          [maps:get(name, C), maps:get(matches, C),
                           range_text(maps:get(seasons, C))]) || C <- Comps]
        ++ [maps:get(note, S, <<>>)];

lines(_Tool, Result) ->
    [io_lib:format("~tp", [Result])].

%%====================================================================
%% Pieces
%%====================================================================

-spec match_line(map()) -> iolist().
match_line(M) ->
    #{date := Date, home_team := H, away_team := A, competition_name := Comp} = M,
    Score = case maps:get(score, M, undefined) of
                undefined -> <<"not played / unknown">>;
                S -> S
            end,
    [io_lib:format("~ts: ~ts ~ts ~ts (~ts~ts~ts)",
                   [opt(Date), H, Score, A, Comp,
                    season_suffix(maps:get(season, M, undefined)),
                    stage_suffix(M)])].

season_suffix(undefined) -> "";
season_suffix(S) -> [" ", bsmcp_text:bin(S)].

stage_suffix(M) ->
    case {maps:get(round, M, undefined), maps:get(stage, M, undefined)} of
        {undefined, undefined} -> "";
        {undefined, Stage} -> [", ", Stage];
        {Round, undefined} -> [", round ", bsmcp_text:bin(Round)];
        {Round, Stage} -> [", ", Stage, " round ", bsmcp_text:bin(Round)]
    end.

player_line(P) ->
    io_lib:format("~ts - overall ~ts, ~ts, ~ts~ts",
                  [maps:get(name, P), opt(maps:get(overall, P, undefined)),
                   opt(maps:get(position, P, undefined)),
                   opt(maps:get(club, P, undefined)),
                   case maps:get(nationality, P, undefined) of
                       undefined -> "";
                       Nat -> [" (", Nat, ")"]
                   end]).

record_lines(Rec) ->
    #{played := P, wins := W, draws := D, losses := L, goals_for := GF,
      goals_against := GA, points := Pts, win_rate := Rate} = Rec,
    Home = maps:get(home, Rec, #{}),
    Away = maps:get(away, Rec, #{}),
    ["  Matches: " ++ integer_to_list(P),
     io_lib:format("  Wins: ~b, Draws: ~b, Losses: ~b", [W, D, L]),
     io_lib:format("  Goals For: ~b, Goals Against: ~b (~s~b)",
                   [GF, GA, case GF - GA >= 0 of true -> "+"; false -> "" end, GF - GA]),
     io_lib:format("  Win rate: ~.1f% | Points: ~b (~.2f per match)",
                   [float(Rate), Pts, float(maps:get(points_per_match, Rec, 0.0))])]
        ++ case {maps:get(played, Home, 0), maps:get(played, Away, 0)} of
               {0, 0} ->
                   [];
               {HP, AP} ->
                   [io_lib:format("  Home: ~b played, ~bW ~bD ~bL, ~b:~b",
                                  [HP, maps:get(wins, Home), maps:get(draws, Home),
                                   maps:get(losses, Home), maps:get(goals_for, Home),
                                   maps:get(goals_against, Home)]),
                    io_lib:format("  Away: ~b played, ~bW ~bD ~bL, ~b:~b",
                                  [AP, maps:get(wins, Away), maps:get(draws, Away),
                                   maps:get(losses, Away), maps:get(goals_for, Away),
                                   maps:get(goals_against, Away)])]
           end.

stats_lines(S) ->
    [io_lib:format("  Matches: ~b, goals: ~b (~.2f per match)",
                   [maps:get(matches, S), maps:get(goals, S),
                    float(maps:get(goals_per_match, S))]),
     io_lib:format("  Home wins ~.1f%, away wins ~.1f%, draws ~.1f%",
                   [float(maps:get(home_win_pct, S)), float(maps:get(away_win_pct, S)),
                    float(maps:get(draw_pct, S))]),
     io_lib:format("  Matches over 2.5 goals: ~.1f%, goalless: ~.1f%",
                   [float(maps:get(over_2_5_goals_pct, S)),
                    float(maps:get(goalless_pct, S))])].

filter_header(F) when map_size(F) =:= 0 ->
    "All competitions and seasons";
filter_header(F0) ->
    %% "Flamengo vs Fluminense" reads better than "Flamengo, vs Fluminense"
    {Fixture, F} =
        case {maps:get(team, F0, undefined), maps:get(opponent, F0, undefined)} of
            {A, B} when A =/= undefined, B =/= undefined ->
                {[[A, " vs ", B]], maps:without([team, opponent], F0)};
            _ ->
                {[], F0}
        end,
    Parts = Fixture ++
        [describe(K, V) || K <- [competition, season, seasons, season_from,
                                 season_to, date_from, date_to, team, opponent,
                                 home_team, away_team, venue, stage, round],
                           V <- [maps:get(K, F, undefined)], V =/= undefined],
    join([bsmcp_text:bin(P) || P <- Parts], <<", ">>).

describe(competition, V) -> ["competition ", bsmcp_data:competition_name(V)];
describe(season, V) -> ["season ", bsmcp_text:bin(V)];
describe(seasons, V) -> ["seasons ", join([bsmcp_text:bin(S) || S <- V], <<"/">>)];
describe(season_from, V) -> ["from ", bsmcp_text:bin(V)];
describe(season_to, V) -> ["to ", bsmcp_text:bin(V)];
describe(date_from, V) -> ["since ", V];
describe(date_to, V) -> ["until ", V];
describe(team, V) -> [V];
describe(opponent, V) -> ["vs ", V];
describe(home_team, V) -> ["home ", V];
describe(away_team, V) -> ["away ", V];
describe(venue, V) -> [bsmcp_text:bin(V), " matches"];
describe(stage, V) -> ["stage ", V];
describe(round, V) -> ["round ", bsmcp_text:bin(V)].

scope_suffix(F) ->
    Parts = [X || X <- [case maps:get(venue, F, undefined) of
                            undefined -> undefined;
                            V -> [bsmcp_text:bin(V), " record"]
                        end,
                        case maps:get(season, F, undefined) of
                            undefined -> undefined;
                            S -> bsmcp_text:bin(S)
                        end,
                        case maps:get(competition, F, undefined) of
                            undefined -> undefined;
                            C -> bsmcp_data:competition_name(C)
                        end], X =/= undefined],
    case Parts of
        [] -> " - overall record";
        _ -> [" - ", join([bsmcp_text:bin(P) || P <- Parts], <<", ">>)]
    end.

top_skills(Skills) when map_size(Skills) =:= 0 -> [];
top_skills(Skills) ->
    Sorted = lists:sort(fun({_, A}, {_, B}) -> A >= B end, maps:to_list(Skills)),
    [<<K/binary, " ", (integer_to_binary(V))/binary>> || {K, V} <- lists:sublist(Sorted, 5)].

optional_line(_Label, undefined) -> [];
optional_line(Label, M) -> [[Label, match_line(M)]].

range_text([]) -> "none";
range_text([S]) -> bsmcp_text:bin(S);
range_text(Seasons) ->
    Sorted = lists:sort(Seasons),
    First = hd(Sorted),
    Last = lists:last(Sorted),
    case Last - First + 1 =:= length(Sorted) of
        true -> [bsmcp_text:bin(First), "-", bsmcp_text:bin(Last)];
        false -> join([bsmcp_text:bin(S) || S <- Sorted], <<", ">>)
    end.

enumerate(List) ->
    lists:zip(lists:seq(1, length(List)), List).

opt(undefined) -> "-";
opt(null) -> "-";
opt(V) when is_binary(V) -> V;
opt(V) -> bsmcp_text:bin(V).

number(V) when is_integer(V) -> integer_to_binary(V);
number(V) when is_float(V) -> float_to_binary(V, [{decimals, 2}, compact]);
number(V) -> bsmcp_text:bin(V).

join(Items, Sep) ->
    bsmcp_text:join([bsmcp_text:bin(I) || I <- Items], Sep).

to_bin(Lines) ->
    unicode:characters_to_binary(lists:join("\n", [L || L <- Lines, L =/= []]), utf8, utf8).
