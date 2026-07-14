%%% ===================================================================
%%% Brazilian Soccer MCP Server - human-readable rendering
%%%
%%% Context: Every MCP tool returns both machine-readable
%%% `structuredContent' and a text rendering for the LLM/user. This
%%% module turns a tool's structured result map into the formatted
%%% prose shown in the examples of brazilian-soccer-mcp-guide.md
%%% (match lists, head-to-head summaries, standings tables, player
%%% lists, statistics).
%%% ===================================================================
-module(bsoccer_format).

-export([render/2]).

-spec render(binary(), map()) -> binary().
render(<<"find_matches">>, S) ->
    Matches = maps:get(<<"matches">>, S),
    Header = io_lib:format("Found ~p match(es)~s:",
                           [maps:get(<<"count">>, S), shown_suffix(S)]),
    lines([Header | [match_line(M) || M <- Matches]]);

render(<<"head_to_head">>, S) ->
    Head = io_lib:format("~ts vs ~ts head-to-head: ~p matches",
                         [bin(maps:get(<<"team1">>, S)),
                          bin(maps:get(<<"team2">>, S)),
                          maps:get(<<"total_matches">>, S)]),
    Summary = io_lib:format("~ts wins: ~p, ~ts wins: ~p, draws: ~p",
                            [bin(maps:get(<<"team1">>, S)), maps:get(<<"team1_wins">>, S),
                             bin(maps:get(<<"team2">>, S)), maps:get(<<"team2_wins">>, S),
                             maps:get(<<"draws">>, S)]),
    Recent = [match_line(M) || M <- maps:get(<<"matches">>, S)],
    lines([Head, Summary | Recent]);

render(<<"team_statistics">>, S) ->
    lines(
      [io_lib:format("~ts (~ts):",
                     [bin(maps:get(<<"team">>, S)), bin(maps:get(<<"venue">>, S))]),
       io_lib:format("  Matches: ~p", [maps:get(<<"matches">>, S)]),
       io_lib:format("  Wins: ~p, Draws: ~p, Losses: ~p",
                     [maps:get(<<"wins">>, S), maps:get(<<"draws">>, S),
                      maps:get(<<"losses">>, S)]),
       io_lib:format("  Goals For: ~p, Goals Against: ~p (diff ~p)",
                     [maps:get(<<"goals_for">>, S), maps:get(<<"goals_against">>, S),
                      maps:get(<<"goal_difference">>, S)]),
       io_lib:format("  Points: ~p, Win rate: ~ts%",
                     [maps:get(<<"points">>, S), pct(maps:get(<<"win_rate">>, S))])]);

render(<<"competition_standings">>, S) ->
    Title = io_lib:format("~ts ~ts - Standings:",
                          [bin(maps:get(<<"competition">>, S)),
                           bin(maps:get(<<"season">>, S))]),
    Rows = [standings_line(R) || R <- maps:get(<<"standings">>, S)],
    lines([Title | Rows]);

render(<<"search_players">>, S) ->
    Title = io_lib:format("~p player(s) found (showing ~p):",
                          [maps:get(<<"total_available">>, S), maps:get(<<"count">>, S)]),
    Rows = [player_line(I, P)
            || {I, P} <- enumerate(maps:get(<<"players">>, S))],
    lines([Title | Rows]);

render(<<"aggregate_statistics">>, S) ->
    Big = [match_line(M) || M <- maps:get(<<"biggest_wins">>, S)],
    lines(
      [io_lib:format("Total matches: ~p", [maps:get(<<"total_matches">>, S)]),
       io_lib:format("Average goals per match: ~ts",
                     [num(maps:get(<<"avg_goals_per_match">>, S))]),
       io_lib:format("Home win rate: ~ts%", [pct(maps:get(<<"home_win_rate">>, S))]),
       io_lib:format("Home wins: ~p, Away wins: ~p, Draws: ~p",
                     [maps:get(<<"home_wins">>, S), maps:get(<<"away_wins">>, S),
                      maps:get(<<"draws">>, S)]),
       "Biggest wins:" | Big]);

render(<<"list_competitions">>, S) ->
    Rows = [io_lib:format("  ~ts: ~p matches",
                          [bin(maps:get(<<"name">>, C)), maps:get(<<"matches">>, C)])
            || C <- maps:get(<<"competitions">>, S)],
    lines(["Competitions loaded:" | Rows]);

render(_Tool, S) ->
    %% Fallback: pretty-print the structured payload.
    iolist_to_binary(io_lib:format("~tp", [S])).

%%% --- line builders -------------------------------------------------

match_line(M) ->
    Date = bin(maps:get(<<"date">>, M)),
    Comp = bin(maps:get(<<"competition">>, M)),
    Extra = round_stage(M),
    io_lib:format("  ~ts: ~ts ~p-~p ~ts (~ts~ts)",
                  [Date, bin(maps:get(<<"home">>, M)),
                   maps:get(<<"home_goal">>, M), maps:get(<<"away_goal">>, M),
                   bin(maps:get(<<"away">>, M)), Comp, Extra]).

round_stage(M) ->
    R = bin(maps:get(<<"round">>, M, <<>>)),
    St = bin(maps:get(<<"stage">>, M, <<>>)),
    case {R, St} of
        {<<>>, <<>>} -> "";
        {_, <<>>} -> [" Round ", R];
        {<<>>, _} -> [" ", St];
        _ -> [" Round ", R, " ", St]
    end.

standings_line(R) ->
    io_lib:format("  ~p. ~ts - ~p pts (~pW ~pD ~pL, GF ~p GA ~p)",
                  [maps:get(<<"position">>, R), bin(maps:get(<<"team">>, R)),
                   maps:get(<<"points">>, R), maps:get(<<"wins">>, R),
                   maps:get(<<"draws">>, R), maps:get(<<"losses">>, R),
                   maps:get(<<"goals_for">>, R), maps:get(<<"goals_against">>, R)]).

player_line(I, P) ->
    io_lib:format("  ~p. ~ts - Overall: ~p, Position: ~ts, Club: ~ts (~ts)",
                  [I, bin(maps:get(<<"name">>, P)), maps:get(<<"overall">>, P),
                   bin(maps:get(<<"position">>, P)), bin(maps:get(<<"club">>, P)),
                   bin(maps:get(<<"nationality">>, P))]).

shown_suffix(S) ->
    case maps:get(<<"returned">>, S, undefined) of
        undefined -> "";
        R ->
            case maps:get(<<"count">>, S) of
                R -> "";
                _ -> io_lib:format(" (showing ~p)", [R])
            end
    end.

%%% --- helpers -------------------------------------------------------

lines(Parts) ->
    unicode:characters_to_binary(lists:join("\n", [to_str(P) || P <- Parts])).

to_str(B) when is_binary(B) -> B;
to_str(L) -> L.

enumerate(L) ->
    lists:zip(lists:seq(1, length(L)), L).

bin(null) -> <<"?">>;
bin(V) when is_binary(V) -> V;
bin(V) when is_integer(V) -> integer_to_binary(V);
bin(V) -> unicode:characters_to_binary(io_lib:format("~tp", [V])).

pct(F) when is_number(F) -> num(round_to(F * 100, 1));
pct(_) -> <<"0">>.

num(F) when is_float(F) -> iolist_to_binary(io_lib:format("~.2f", [F]));
num(I) when is_integer(I) -> integer_to_binary(I);
num(_) -> <<"0">>.

round_to(F, D) ->
    P = math:pow(10, D),
    round(F * P) / P.
