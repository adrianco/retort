%% @doc Human-readable formatting of query results as UTF-8 text.
-module(bsmcp_format).

-export([match_line/1, matches/1, team_record/2, head_to_head/4,
         players/1, standings/3]).

%% @doc One-line summary of a match.
-spec match_line(map()) -> binary().
match_line(M) ->
    Date = orq(maps:get(date, M)),
    Home = maps:get(home, M),
    Away = maps:get(away, M),
    Score = score_str(M),
    Ctx = context(M),
    iolist_to_binary([Date, ": ", Home, " ", Score, " ", Away, Ctx]).

score_str(M) ->
    case {maps:get(home_goal, M), maps:get(away_goal, M)} of
        {HG, AG} when is_integer(HG), is_integer(AG) ->
            [integer_to_binary(HG), "-", integer_to_binary(AG)];
        _ ->
            "vs"
    end.

context(M) ->
    Comp = maps:get(competition, M),
    Parts = [Comp] ++ round_part(M) ++ stage_part(M),
    [" (", lists:join(", ", Parts), ")"].

round_part(M) ->
    case maps:get(round, M, undefined) of
        undefined -> [];
        <<>> -> [];
        R when is_binary(R) -> [["Round ", R]];
        R when is_integer(R) -> [["Round ", integer_to_binary(R)]]
    end.

stage_part(M) ->
    case maps:get(stage, M, undefined) of
        undefined -> [];
        <<>> -> [];
        S -> [S]
    end.

%% @doc Format a list of matches, newest first, with a count header.
-spec matches([map()]) -> binary().
matches([]) ->
    <<"No matches found.">>;
matches(Ms) ->
    Sorted = lists:sort(fun(A, B) -> orq(maps:get(date, A)) >= orq(maps:get(date, B)) end, Ms),
    Header = [count_word(length(Ms), <<"match">>, <<"matches">>), " found:"],
    Lines = [["- ", match_line(M)] || M <- Sorted],
    join_lines([Header | Lines]).

%% @doc Format a team's aggregate record.
-spec team_record(binary(), map()) -> binary().
team_record(Team, Rec) ->
    join_lines(
      [[Team, " record:"],
       ["- Matches: ", integer_to_binary(maps:get(matches, Rec))],
       ["- Wins: ", integer_to_binary(maps:get(wins, Rec)),
        ", Draws: ", integer_to_binary(maps:get(draws, Rec)),
        ", Losses: ", integer_to_binary(maps:get(losses, Rec))],
       ["- Goals For: ", integer_to_binary(maps:get(goals_for, Rec)),
        ", Goals Against: ", integer_to_binary(maps:get(goals_against, Rec))],
       ["- Win rate: ", fmt_float(maps:get(win_rate, Rec)), "%"]]).

%% @doc Format a head-to-head summary between two teams.
-spec head_to_head(binary(), binary(), [map()], map()) -> binary().
head_to_head(A, B, Ms, Rec) ->
    Summary = [A, " vs ", B, " head-to-head (", integer_to_binary(length(Ms)),
               " matches): ",
               A, " ", integer_to_binary(maps:get(a_wins, Rec)), " wins, ",
               B, " ", integer_to_binary(maps:get(b_wins, Rec)), " wins, ",
               integer_to_binary(maps:get(draws, Rec)), " draws"],
    Lines = [["- ", match_line(M)]
             || M <- lists:sort(fun(X, Y) -> orq(maps:get(date, X)) >= orq(maps:get(date, Y)) end, Ms)],
    join_lines([Summary | Lines]).

%% @doc Format a list of players, one per line.
-spec players([map()]) -> binary().
players([]) ->
    <<"No players found.">>;
players(Ps) ->
    Header = [count_word(length(Ps), <<"player">>, <<"players">>), " found:"],
    Lines = [player_line(I, P) || {I, P} <- enumerate(Ps)],
    join_lines([Header | Lines]).

player_line(I, P) ->
    [integer_to_binary(I), ". ", maps:get(name, P),
     " - Overall: ", int_or_na(maps:get(overall, P, undefined)),
     ", Position: ", or_na(maps:get(position, P, <<>>)),
     ", Club: ", or_na(maps:get(club, P, <<>>)),
     ", Nationality: ", or_na(maps:get(nationality, P, <<>>))].

%% @doc Format a standings table.
-spec standings(binary(), integer(), [map()]) -> binary().
standings(Comp, Season, Rows) ->
    Header = [integer_to_binary(Season), " ", Comp, " standings:"],
    Lines = [standing_line(I, R) || {I, R} <- enumerate(Rows)],
    join_lines([Header | Lines]).

standing_line(I, R) ->
    [integer_to_binary(I), ". ", maps:get(team, R), " - ",
     integer_to_binary(maps:get(points, R)), " pts (",
     integer_to_binary(maps:get(wins, R)), "W ",
     integer_to_binary(maps:get(draws, R)), "D ",
     integer_to_binary(maps:get(losses, R)), "L), GF ",
     integer_to_binary(maps:get(goals_for, R)), " GA ",
     integer_to_binary(maps:get(goals_against, R)), " GD ",
     fmt_signed(maps:get(goal_diff, R))].

%% --- helpers ----------------------------------------------------------

orq(undefined) -> <<"?">>;
orq(B) -> B.

or_na(<<>>) -> <<"N/A">>;
or_na(undefined) -> <<"N/A">>;
or_na(B) -> B.

int_or_na(undefined) -> <<"N/A">>;
int_or_na(N) when is_integer(N) -> integer_to_binary(N).

count_word(1, Singular, _Plural) -> [<<"1 ">>, Singular];
count_word(N, _Singular, Plural) -> [integer_to_binary(N), <<" ">>, Plural].

fmt_float(F) when is_float(F) ->
    float_to_binary(F, [{decimals, 1}]);
fmt_float(N) when is_integer(N) ->
    integer_to_binary(N).

fmt_signed(N) when N >= 0 -> [<<"+">>, integer_to_binary(N)];
fmt_signed(N) -> integer_to_binary(N).

enumerate(L) -> lists:zip(lists:seq(1, length(L)), L).

join_lines(Lines) ->
    iolist_to_binary(lists:join("\n", Lines)).
