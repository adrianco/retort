%%%-------------------------------------------------------------------
%%% @doc Human readable rendering of query results.
%%%
%%% MCP tools return both `structuredContent' (the raw map, for
%%% programmatic use) and a text block.  The text is what an LLM reads,
%%% so it follows the layouts given in the specification, e.g.
%%%
%%% ```
%%% Corinthians home record (2022 Brasileirão Série A):
%%% - Matches: 19
%%% - Wins: 11, Draws: 5, Losses: 3
%%% - Goals For: 28, Goals Against: 15
%%% - Win rate: 57.9%
%%% '''
%%% @end
%%%-------------------------------------------------------------------
-module(br_format).

-include("br_soccer.hrl").

-export([render/2,
         match_line/1,
         match_line_map/1,
         error_text/1]).

-define(NL, "\n").

%%--------------------------------------------------------------------
%% @doc One line summary of a match record (also used as graph label).
-spec match_line(#match{}) -> binary().
match_line(#match{} = M) -> match_line_map(br_query:match_map(M)).

%% @doc One line summary of a match map.
-spec match_line_map(map()) -> binary().
match_line_map(#{home_name := H, away_name := A} = M) ->
    Date = str(maps:get(date, M, null), <<"date unknown">>),
    Score = case maps:get(score, M, null) of
                null -> <<"vs">>;
                S -> S
            end,
    Context = context(M),
    bin([Date, ": ", H, " ", Score, " ", A, Context]).

context(M) ->
    Comp = str(maps:get(competition_name, M, null), <<>>),
    Extra = case {maps:get(round, M, null), maps:get(stage, M, null)} of
                {null, null} -> <<>>;
                {null, Stage} -> <<" ", (cap(Stage))/binary>>;
                {Round, _} -> <<" Round ", (str(Round, <<"?">>))/binary>>
            end,
    Season = case maps:get(season, M, null) of
                 null -> <<>>;
                 S -> <<" ", (num(S))/binary>>
             end,
    case Comp of
        <<>> -> <<>>;
        _ -> <<" (", Comp/binary, Season/binary, Extra/binary, ")">>
    end.

%%--------------------------------------------------------------------
%% @doc Render a tool result as text.
-spec render(atom() | binary(), map()) -> binary().
render(Tool, Result) when is_binary(Tool) ->
    render(binary_to_atom(Tool, utf8), Result);

render(find_matches, #{matches := Matches, total := Total} = R) ->
    Header = case maps:get(query, R, #{}) of
                 #{team := T, opponent := O} when T =/= null, O =/= null ->
                     io_lib:format("Matches between ~ts and ~ts", [name_of(T), name_of(O)]);
                 #{team := T} when T =/= null ->
                     io_lib:format("Matches involving ~ts", [name_of(T)]);
                 _ -> "Matches"
             end,
    lines([bin([Header, filters_suffix(maps:get(query, R, #{})), ":"])
           | bullet_matches(Matches)] ++ [total_line(Total, length(Matches), "matches")]);

render(head_to_head, R) ->
    #{team_a := #{team_name := A}, team_b := #{team_name := B},
      team_a_wins := AW, team_b_wins := BW, draws := D,
      team_a_goals := AG, team_b_goals := BG,
      played := Played, total := Total, matches := Matches} = R,
    Title = case maps:get(derby, R, null) of
                null -> io_lib:format("~ts vs ~ts:", [A, B]);
                Derby -> io_lib:format("~ts vs ~ts (~ts):", [A, B, Derby])
            end,
    Summary = io_lib:format("Head-to-head in dataset (~p matches): ~ts ~p wins, "
                            "~ts ~p wins, ~p draws~nGoals: ~ts ~p - ~p ~ts",
                            [Played, A, AW, B, BW, D, A, AG, BG, B]),
    lines([bin(Title)] ++ bullet_matches(Matches)
          ++ [total_line(Total, length(Matches), "matches"), <<>>,
              bin(Summary)]);

render(team_stats, R) ->
    #{team_name := Name, played := P, wins := W, draws := D, losses := L,
      goals_for := GF, goals_against := GA, win_rate := WR,
      home := Home, away := Away, venue := Venue} = R,
    Scope = scope_text(R, Venue),
    Head = io_lib:format("~ts ~tsrecord~ts:", [Name, venue_word(Venue), Scope]),
    Body = [io_lib:format("- Matches: ~p", [P]),
            io_lib:format("- Wins: ~p, Draws: ~p, Losses: ~p", [W, D, L]),
            io_lib:format("- Goals For: ~p, Goals Against: ~p (~p goal difference)",
                          [GF, GA, maps:get(goal_difference, R)]),
            io_lib:format("- Points: ~p (~ts per game)",
                          [maps:get(points, R), num(maps:get(points_per_game, R))]),
            io_lib:format("- Win rate: ~ts%", [num(WR)])],
    Splits = case Venue of
                 <<"any">> ->
                     [io_lib:format("- Home: ~p-~p-~p (W-D-L), ~p goals for",
                                    [maps:get(wins, Home), maps:get(draws, Home),
                                     maps:get(losses, Home), maps:get(goals_for, Home)]),
                      io_lib:format("- Away: ~p-~p-~p (W-D-L), ~p goals for",
                                    [maps:get(wins, Away), maps:get(draws, Away),
                                     maps:get(losses, Away), maps:get(goals_for, Away)])];
                 _ -> []
             end,
    Biggest = case maps:get(biggest_win, R, null) of
                  null -> [];
                  M -> [bin(["- Biggest win: ", match_line_map(M)])]
              end,
    lines([bin(Head)] ++ [bin(X) || X <- Body ++ Splits] ++ Biggest);

render(team_profile, R) ->
    #{team_name := Name, overall := O, by_competition := ByComp,
      by_season := BySeason, squad := Squad} = R,
    Head = io_lib:format("~ts (~ts~ts) - ~p matches in the data set",
                         [Name, str(maps:get(state, R, null), <<"?">>),
                          case maps:get(country, R, null) of
                              null -> <<>>;
                              C -> <<", ", C/binary>>
                          end,
                          maps:get(played, O)]),
    Record = io_lib:format("Overall: ~p W, ~p D, ~p L - ~p goals for, ~p against",
                           [maps:get(wins, O), maps:get(draws, O), maps:get(losses, O),
                            maps:get(goals_for, O), maps:get(goals_against, O)]),
    Comps = [io_lib:format("- ~ts: ~p matches, ~p W ~p D ~p L",
                           [maps:get(competition_name, C), maps:get(played, C),
                            maps:get(wins, C), maps:get(draws, C), maps:get(losses, C)])
             || C <- ByComp],
    Seasons = [io_lib:format("- ~p: ~p W ~p D ~p L (~p pts)",
                             [maps:get(season, S), maps:get(wins, S), maps:get(draws, S),
                              maps:get(losses, S), maps:get(points, S)])
               || S <- lists:sublist(BySeason, 10)],
    SquadLines = case Squad of
                     [] -> [maps:get(squad_note, R, <<>>)];
                     _ -> [player_line(P) || P <- Squad]
                 end,
    lines([bin(Head), bin(Record), <<>>, <<"By competition:">>]
          ++ [bin(X) || X <- Comps]
          ++ [<<>>, <<"Recent seasons:">>] ++ [bin(X) || X <- Seasons]
          ++ [<<>>, <<"Squad (FIFA data):">>] ++ SquadLines);

render(standings, R) ->
    #{competition_name := Comp, season := Season, table := Table} = R,
    Suffix = case {maps:get(competition_type, R, <<"league">>),
                   maps:get(complete, R, false)} of
                 {<<"knockout">>, _} ->
                     " - points table over the matches in the data "
                     "(this is a knockout competition, not a league):";
                 {_, true} -> " Final Standings (calculated from matches):";
                 {_, false} -> " Standings so far (calculated from matches):"
             end,
    Head = io_lib:format("~p ~ts~ts", [Season, Comp, Suffix]),
    Champion = maps:get(champion, R, null),
    Relegated = maps:get(relegated, R, []),
    Rows = [begin
                Mark = case {maps:get(position, Row), Champion} of
                           {1, C} when C =/= null -> " - Champion";
                           _ ->
                               case lists:member(maps:get(team_name, Row), Relegated) of
                                   true -> " - Relegated";
                                   false -> ""
                               end
                       end,
                io_lib:format("~p. ~ts - ~p pts (~pW, ~pD, ~pL) ~p:~p~ts",
                              [maps:get(position, Row), maps:get(team_name, Row),
                               maps:get(points, Row), maps:get(wins, Row),
                               maps:get(draws, Row), maps:get(losses, Row),
                               maps:get(goals_for, Row), maps:get(goals_against, Row), Mark])
            end || Row <- Table],
    lines([bin(Head)] ++ [bin(X) || X <- Rows]);

render(team_rankings, R) ->
    Scope = bin(
              [case maps:get(competition_name, R, null) of
                   null -> <<"all competitions">>;
                   C -> C
               end,
               case maps:get(season, R, null) of
                   null -> <<>>;
                   S -> <<" ", (num(S))/binary>>
               end]),
    Head = io_lib:format("Teams ranked by ~ts (~ts record, ~ts, minimum ~p matches):",
                         [maps:get(metric, R), maps:get(venue, R), Scope,
                          maps:get(min_matches, R)]),
    Rows = [io_lib:format("~p. ~ts - ~p pts from ~p matches (~pW ~pD ~pL), "
                          "~p:~p goals, win rate ~ts%",
                          [maps:get(position, Row), maps:get(team_name, Row),
                           maps:get(points, Row), maps:get(played, Row),
                           maps:get(wins, Row), maps:get(draws, Row), maps:get(losses, Row),
                           maps:get(goals_for, Row), maps:get(goals_against, Row),
                           num(maps:get(win_rate, Row))])
            || Row <- maps:get(rankings, R, [])],
    lines([bin(Head) | [bin(X) || X <- Rows]]);

render(competition_stats, R) ->
    Name = str(maps:get(competition_name, R, null), <<"All competitions">>),
    Season = case maps:get(season, R, null) of
                 null ->
                     case maps:get(seasons_covered, R, []) of
                         [] -> <<"">>;
                         Seasons -> bin(io_lib:format(" ~p-~p",
                                                                   [hd(Seasons),
                                                                    lists:last(Seasons)]))
                     end;
                 S -> bin(io_lib:format(" ~p", [S]))
             end,
    Body = [io_lib:format("Matches: ~p", [maps:get(matches, R)]),
            io_lib:format("Goals: ~p (average ~ts per match)",
                          [maps:get(goals, R), num(maps:get(goals_per_match, R))]),
            io_lib:format("Home win rate: ~ts%  Draw rate: ~ts%  Away win rate: ~ts%",
                          [num(maps:get(home_win_rate, R)), num(maps:get(draw_rate, R)),
                           num(maps:get(away_win_rate, R))]),
            bin(["Biggest win: ", match_line_map(maps:get(biggest_win, R))])],
    Top = [io_lib:format("- ~ts: ~p goals in ~p matches",
                         [maps:get(team_name, T), maps:get(goals_for, T),
                          maps:get(played, T)])
           || T <- maps:get(top_scoring_teams, R, [])],
    lines([bin([Name, Season, ":"])]
          ++ [bin(X) || X <- Body]
          ++ [<<>>, <<"Top scoring teams:">>] ++ [bin(X) || X <- Top]);

render(compare_seasons, R) ->
    #{competition_name := Comp, season_a := A, season_b := B, deltas := D} = R,
    Fmt = fun(S) ->
                  io_lib:format("~p: ~p matches, ~p goals (~ts per match), "
                                "home wins ~ts%, draws ~ts%, away wins ~ts%",
                                [maps:get(season, S), maps:get(matches, S),
                                 maps:get(goals, S), num(maps:get(goals_per_match, S)),
                                 num(maps:get(home_win_rate, S)),
                                 num(maps:get(draw_rate, S)),
                                 num(maps:get(away_win_rate, S))])
          end,
    lines([bin([Comp, ":"]), bin(Fmt(A)), bin(Fmt(B)),
           bin(io_lib:format("Change: ~ts goals per match, ~ts% home wins",
                                          [num(maps:get(goals_per_match, D)),
                                           num(maps:get(home_win_rate, D))]))]);

render(biggest_wins, #{matches := Matches} = R) ->
    Rows = [bin(io_lib:format("~p. ~ts", [I, match_line_map(M)]))
            || {I, M} <- lists:zip(lists:seq(1, length(Matches)), Matches)],
    lines([<<"Biggest victories:">> | Rows]
          ++ [total_line(maps:get(total, R, length(Matches)), length(Matches), "matches")]);

render(search_players, #{players := Players} = R) ->
    Rows = [bin(io_lib:format("~p. ~ts", [I, player_line_bare(P)]))
            || {I, P} <- lists:zip(lists:seq(1, length(Players)), Players)],
    Note = case maps:get(note, R, null) of
               null -> [];
               Text -> [Text]
           end,
    lines([<<"Players:">> | Rows]
          ++ [total_line(maps:get(total, R, length(Players)), length(Players), "players")]
          ++ Note);

render(player_profile, P) ->
    Head = io_lib:format("~ts - Overall: ~ts, Potential: ~ts, Position: ~ts, Club: ~ts",
                         [maps:get(name, P), num(maps:get(overall, P)),
                          num(maps:get(potential, P)), str(maps:get(position, P), <<"?">>),
                          str(maps:get(club, P), <<"no club">>)]),
    Bio = io_lib:format("Age ~ts, ~ts, ~ts, ~ts, prefers ~ts foot",
                        [num(maps:get(age, P)), str(maps:get(nationality, P), <<"?">>),
                         str(maps:get(height, P), <<"?">>), str(maps:get(weight, P), <<"?">>),
                         str(maps:get(preferred_foot, P), <<"?">>)]),
    Skills = [io_lib:format("- ~ts: ~p", [maps:get(skill, S), maps:get(value, S)])
              || S <- maps:get(top_skills, P, [])],
    Club = case maps:get(club_in_match_data, P, null) of
               null -> [<<"Club not present in the match data sets.">>];
               C -> [bin(
                       io_lib:format("~ts appears in ~p matches of the match data sets.",
                                     [maps:get(team_name, C),
                                      maps:get(matches_in_dataset, C)]))]
           end,
    lines([bin(Head), bin(Bio), <<>>, <<"Best attributes:">>]
          ++ [bin(X) || X <- Skills] ++ [<<>>] ++ Club);

render(club_squad, R) ->
    #{club_name := Name, squad_size := N, players := Players} = R,
    Head = io_lib:format("~ts squad in fifa_data.csv: ~p players (average overall ~ts)",
                         [Name, N, num(maps:get(average_overall, R))]),
    case Players of
        [] -> lines([bin(Head), maps:get(note, R, <<>>)]);
        _ -> lines([bin(Head) | [player_line(P) || P <- Players]])
    end;

render(player_club_summary, R) ->
    Nat = str(maps:get(nationality, R, null), <<"All">>),
    Head = io_lib:format("~ts players by club (~p players, ~p clubs):",
                         [Nat, maps:get(total_players, R), maps:get(clubs, R)]),
    Rows = [io_lib:format("- ~ts: ~p players (avg rating: ~ts), best ~ts",
                          [maps:get(club_name, C), maps:get(players, C),
                           num(maps:get(average_overall, C)),
                           maps:get(name, maps:get(best, C))])
            || C <- maps:get(by_club, R, [])],
    lines([bin(Head) | [bin(X) || X <- Rows]]);

render(derbies, R) ->
    Season = case maps:get(season, R, null) of
                 null -> <<"all seasons">>;
                 S -> num(S)
             end,
    Head = bin(["Derbies (", Season, "):"]),
    Blocks = lists:map(
               fun(D) ->
                       Title = io_lib:format("~ts - ~ts vs ~ts (~p matches)",
                                             [maps:get(derby, D),
                                              maps:get(team_name, maps:get(team_a, D)),
                                              maps:get(team_name, maps:get(team_b, D)),
                                              maps:get(matches, D)]),
                       lines([bin(Title)
                              | bullet_matches(maps:get(fixtures, D, []))])
               end, maps:get(derbies, R, [])),
    lines([Head | Blocks]);

render(list_teams, #{teams := Teams} = R) ->
    Rows = [io_lib:format("- ~ts (~ts) - ~p matches, competitions: ~ts",
                          [maps:get(name, T), maps:get(team, T), maps:get(matches, T),
                           br_text:join(maps:get(competitions, T), <<", ">>)])
            || T <- Teams],
    lines([<<"Teams:">> | [bin(X) || X <- Rows]]
          ++ [total_line(maps:get(total, R), length(Teams), "teams")]);

render(list_competitions, #{competitions := Comps}) ->
    Rows = [io_lib:format("- ~ts (~ts): ~p matches, seasons ~ts",
                          [maps:get(name, C), maps:get(competition, C),
                           maps:get(matches, C), seasons_text(maps:get(seasons, C))])
            || C <- Comps],
    lines([<<"Competitions:">> | [bin(X) || X <- Rows]]);

render(dataset_summary, R) ->
    Body = [io_lib:format("Matches: ~p (from ~p rows, ~p duplicates merged, "
                          "~p invalid rows dropped)",
                          [maps:get(matches, R), maps:get(rows_read, R),
                           maps:get(duplicates_merged, R),
                           maps:get(invalid_rows, R, 0)]),
            io_lib:format("Teams: ~p   Players: ~p", [maps:get(teams, R),
                                                      maps:get(players, R)]),
            io_lib:format("Graph: ~p nodes, ~p edges", [maps:get(graph_nodes, R),
                                                        maps:get(graph_edges, R)]),
            io_lib:format("Loaded in ~p ms from ~ts",
                          [maps:get(load_time_ms, R), maps:get(data_dir, R)])],
    Comps = [io_lib:format("- ~ts: ~p matches, seasons ~ts",
                           [maps:get(name, C), maps:get(matches, C),
                            seasons_text(maps:get(seasons, C))])
             || C <- maps:get(competitions, R, [])],
    lines([<<"Brazilian soccer knowledge graph:">>]
          ++ [bin(X) || X <- Body]
          ++ [<<>>] ++ [bin(X) || X <- Comps]);

render(graph_neighbors, R) ->
    #{node := Node, neighbours := Neighbours} = R,
    Head = io_lib:format("~ts (~ts) - ~p connections:",
                         [maps:get(label, Node), maps:get(id, Node),
                          maps:get(degree, R, length(Neighbours))]),
    Rows = [io_lib:format("- ~ts ~ts ~ts (~ts)",
                          [maps:get(relation, N),
                           case maps:get(direction, N) of
                               out -> "->";
                               _ -> "<-"
                           end,
                           maps:get(label, maps:get(node, N)),
                           maps:get(id, maps:get(node, N))])
            || N <- Neighbours],
    lines([bin(Head) | [bin(X) || X <- Rows]]);

render(graph_path, #{found := false} = R) ->
    bin(io_lib:format("No path found between ~ts and ~ts",
                                   [maps:get(from, R), maps:get(to, R)]));
render(graph_path, #{path := Path} = R) ->
    Rows = [io_lib:format("  ~ts-[~ts]-> ~ts (~ts)",
                          [case I of 1 -> ""; _ -> "" end,
                           maps:get(relation, S), maps:get(label, maps:get(node, S)),
                           maps:get(id, maps:get(node, S))])
            || {I, S} <- lists:zip(lists:seq(1, length(Path)), Path)],
    lines([bin(io_lib:format("Path (~p hops):", [maps:get(length, R)]))
           | [bin(X) || X <- Rows]]);

render(_Tool, Result) ->
    %% Fallback: pretty-print the structured result.
    bin(io_lib:format("~tp", [Result])).

%%--------------------------------------------------------------------
%% @doc Render an error map.
-spec error_text(map()) -> binary().
error_text(#{message := Msg} = E) ->
    case maps:get(suggestions, E, []) of
        [] -> Msg;
        S -> <<Msg/binary, " - did you mean: ", (br_text:join(S, <<", ">>))/binary, "?">>
    end.

%%====================================================================
%% Internal
%%====================================================================

%% Team ids in a result map are rendered with their display name.
name_of(Id) ->
    case br_store:team(Id) of
        {ok, #team{name = Name}} -> Name;
        error -> br_names:display(Id)
    end.

bullet_matches(Matches) ->
    [bin(["- ", match_line_map(M)]) || M <- Matches].

total_line(Total, Shown, Noun) when Total > Shown ->
    bin(io_lib:format("... (~p more ~ts in dataset, ~p total)",
                                   [Total - Shown, Noun, Total]));
total_line(Total, _Shown, Noun) ->
    bin(io_lib:format("(~p ~ts)", [Total, Noun])).

player_line(P) ->
    bin(["- ", player_line_bare(P)]).

player_line_bare(P) ->
    bin(
      io_lib:format("~ts - Overall: ~ts, Position: ~ts, Club: ~ts~ts",
                    [maps:get(name, P), num(maps:get(overall, P)),
                     str(maps:get(position, P), <<"?">>),
                     str(maps:get(club, P), <<"no club">>),
                     case maps:get(nationality, P, null) of
                         null -> "";
                         Nat -> io_lib:format(" (~ts)", [Nat])
                     end])).

filters_suffix(Query) when is_map(Query) ->
    Parts = [case maps:get(competition, Query, null) of
                 null -> <<>>;
                 C -> <<" in ", (br_names:competition_display(C))/binary>>
             end,
             case maps:get(season, Query, null) of
                 null -> <<>>;
                 S -> <<" (", (num(S))/binary, ")">>
             end],
    bin(Parts);
filters_suffix(_) -> <<>>.

scope_text(R, Venue) ->
    Season = case maps:get(season, R, null) of
                 null -> <<>>;
                 S -> <<" ", (num(S))/binary>>
             end,
    Comp = case maps:get(competition_name, R, null) of
               null -> <<>>;
               C -> <<" ", C/binary>>
           end,
    case {Season, Comp, Venue} of
        {<<>>, <<>>, _} -> <<" (all data)">>;
        _ -> <<" (", (string:trim(<<Season/binary, Comp/binary>>))/binary, ")">>
    end.

venue_word(<<"home">>) -> "home ";
venue_word(<<"away">>) -> "away ";
venue_word(_) -> "".

seasons_text([]) -> <<"none">>;
seasons_text(Seasons) ->
    bin(io_lib:format("~p-~p", [hd(Seasons), lists:last(Seasons)])).

lines(Parts) ->
    br_text:join([to_line(P) || P <- Parts], <<?NL>>).

to_line(B) when is_binary(B) -> B;
to_line(L) -> bin(L).

%% All rendering goes through here.  `io_lib:format' with `~ts' yields a
%% list of *codepoints*, so it must be encoded with
%% `unicode:characters_to_binary/1'; `iolist_to_binary/1' would turn
%% "São Paulo" into "SÃ£o Paulo".
bin(Data) ->
    case unicode:characters_to_binary(Data) of
        Bin when is_binary(Bin) -> Bin;
        Error -> error({not_unicode, Error})
    end.

str(null, Default) -> Default;
str(undefined, Default) -> Default;
str(V, _) when is_binary(V) -> V;
str(V, _) -> br_text:to_binary(V).

num(null) -> <<"?">>;
num(undefined) -> <<"?">>;
num(N) when is_integer(N) -> integer_to_binary(N);
num(F) when is_float(F) -> float_to_binary(F, [{decimals, 1}]);
num(B) when is_binary(B) -> B.

cap(B) -> br_text:titlecase(B).
