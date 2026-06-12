%% Data loading and query module for Brazilian soccer datasets.
%% Loads all 6 CSV files into persistent_term for zero-copy reads.
-module(soccer_data).
-export([init/0,
         reset/0,
         find_matches_all/1,
         find_players_all/1,
         get_head_to_head/3,
         get_standings/2,
         compute_team_stats/2,
         stats_biggest_wins/1,
         stats_avg_goals/1,
         format_match/1,
         format_player/1,
         format_standing/1,
         to_integer/1,
         team_matches/2]).

-define(KEY_MATCHES, soccer_matches).
-define(KEY_PLAYERS, soccer_players).
-define(KEY_INIT, soccer_data_initialized).

%%--------------------------------------------------------------------
%% Initialization
%%--------------------------------------------------------------------

init() ->
    case persistent_term:get(?KEY_INIT, false) of
        true -> ok;
        false ->
            DataDir = data_dir(),
            Matches = load_all_matches(DataDir),
            Players = load_players(DataDir),
            persistent_term:put(?KEY_MATCHES, Matches),
            persistent_term:put(?KEY_PLAYERS, Players),
            persistent_term:put(?KEY_INIT, true),
            ok
    end.

reset() ->
    persistent_term:erase(?KEY_INIT),
    persistent_term:erase(?KEY_MATCHES),
    persistent_term:erase(?KEY_PLAYERS),
    ok.

data_dir() ->
    case os:getenv("DATA_DIR") of
        false -> "data/kaggle";
        Dir -> Dir
    end.

%%--------------------------------------------------------------------
%% Data Loading
%%--------------------------------------------------------------------

load_all_matches(DataDir) ->
    Specs = [
        {fun parse_brasileirao/1, filename:join(DataDir, "Brasileirao_Matches.csv")},
        {fun parse_cup/1,         filename:join(DataDir, "Brazilian_Cup_Matches.csv")},
        {fun parse_libertadores/1,filename:join(DataDir, "Libertadores_Matches.csv")},
        {fun parse_br_football/1, filename:join(DataDir, "BR-Football-Dataset.csv")},
        {fun parse_novo/1,        filename:join(DataDir, "novo_campeonato_brasileiro.csv")}
    ],
    lists:flatmap(fun({Parser, File}) ->
        try
            Rows = soccer_csv:parse_file(File),
            lists:filtermap(fun(Row) ->
                case Parser(Row) of
                    {ok, Match} -> {true, Match};
                    skip -> false
                end
            end, Rows)
        catch _:_ -> []
        end
    end, Specs).

load_players(DataDir) ->
    File = filename:join(DataDir, "fifa_data.csv"),
    try soccer_csv:parse_file(File)
    catch _:_ -> []
    end.

%%--------------------------------------------------------------------
%% Row Parsers - each returns {ok, match_map()} | skip
%%--------------------------------------------------------------------

parse_brasileirao(Row) ->
    try
        {ok, #{
            home_team   => maps:get(<<"home_team">>, Row, <<>>),
            away_team   => maps:get(<<"away_team">>, Row, <<>>),
            home_goal   => to_integer(maps:get(<<"home_goal">>, Row, <<"0">>)),
            away_goal   => to_integer(maps:get(<<"away_goal">>, Row, <<"0">>)),
            competition => <<"brasileirao">>,
            season      => to_integer(maps:get(<<"season">>, Row, <<"0">>)),
            date        => extract_date(maps:get(<<"datetime">>, Row, <<>>)),
            round       => maps:get(<<"round">>, Row, <<>>)
        }}
    catch _:_ -> skip
    end.

parse_cup(Row) ->
    try
        {ok, #{
            home_team   => maps:get(<<"home_team">>, Row, <<>>),
            away_team   => maps:get(<<"away_team">>, Row, <<>>),
            home_goal   => to_integer(maps:get(<<"home_goal">>, Row, <<"0">>)),
            away_goal   => to_integer(maps:get(<<"away_goal">>, Row, <<"0">>)),
            competition => <<"copa_do_brasil">>,
            season      => to_integer(maps:get(<<"season">>, Row, <<"0">>)),
            date        => extract_date(maps:get(<<"datetime">>, Row, <<>>)),
            round       => maps:get(<<"round">>, Row, <<>>)
        }}
    catch _:_ -> skip
    end.

parse_libertadores(Row) ->
    try
        {ok, #{
            home_team   => maps:get(<<"home_team">>, Row, <<>>),
            away_team   => maps:get(<<"away_team">>, Row, <<>>),
            home_goal   => to_integer(maps:get(<<"home_goal">>, Row, <<"0">>)),
            away_goal   => to_integer(maps:get(<<"away_goal">>, Row, <<"0">>)),
            competition => <<"libertadores">>,
            season      => to_integer(maps:get(<<"season">>, Row, <<"0">>)),
            date        => extract_date(maps:get(<<"datetime">>, Row, <<>>)),
            round       => maps:get(<<"stage">>, Row, <<>>)
        }}
    catch _:_ -> skip
    end.

parse_br_football(Row) ->
    try
        DateBin = maps:get(<<"date">>, Row, <<>>),
        Tournament = maps:get(<<"tournament">>, Row, <<>>),
        {ok, #{
            home_team   => maps:get(<<"home">>, Row, <<>>),
            away_team   => maps:get(<<"away">>, Row, <<>>),
            home_goal   => to_integer(maps:get(<<"home_goal">>, Row, <<"0">>)),
            away_goal   => to_integer(maps:get(<<"away_goal">>, Row, <<"0">>)),
            competition => normalize_tournament(Tournament),
            season      => extract_year(DateBin),
            date        => DateBin,
            round       => <<>>
        }}
    catch _:_ -> skip
    end.

parse_novo(Row) ->
    try
        {ok, #{
            home_team   => maps:get(<<"Equipe_mandante">>, Row, <<>>),
            away_team   => maps:get(<<"Equipe_visitante">>, Row, <<>>),
            home_goal   => to_integer(maps:get(<<"Gols_mandante">>, Row, <<"0">>)),
            away_goal   => to_integer(maps:get(<<"Gols_visitante">>, Row, <<"0">>)),
            competition => <<"novo_brasileiro">>,
            season      => to_integer(maps:get(<<"Ano">>, Row, <<"0">>)),
            date        => normalize_br_date(maps:get(<<"Data">>, Row, <<>>)),
            round       => maps:get(<<"Rodada">>, Row, <<>>)
        }}
    catch _:_ -> skip
    end.

%%--------------------------------------------------------------------
%% Query Functions
%%--------------------------------------------------------------------

find_matches_all(Criteria) ->
    All = persistent_term:get(?KEY_MATCHES, []),
    lists:filter(fun(M) -> match_criteria(M, Criteria) end, All).

match_criteria(Match, Criteria) ->
    maps:fold(fun(Key, Value, Acc) ->
        Acc andalso check_criterion(Match, Key, Value)
    end, true, Criteria).

check_criterion(_, limit, _) -> true;
check_criterion(#{home_team := Home, away_team := Away}, team, Team) ->
    team_matches(Home, Team) orelse team_matches(Away, Team);
check_criterion(#{home_team := Home}, home_team, Team) ->
    team_matches(Home, Team);
check_criterion(#{away_team := Away}, away_team, Team) ->
    team_matches(Away, Team);
check_criterion(#{competition := Comp}, competition, CompFilter) ->
    string:lowercase(Comp) =:= string:lowercase(CompFilter);
check_criterion(#{season := Season}, season, SeasonFilter) ->
    Season =:= to_integer(SeasonFilter);
check_criterion(#{date := Date}, date_from, DateFrom) ->
    Date >= DateFrom;
check_criterion(#{date := Date}, date_to, DateTo) ->
    Date =< DateTo;
check_criterion(_, _, _) -> true.

find_players_all(Criteria) ->
    All = persistent_term:get(?KEY_PLAYERS, []),
    Filtered = lists:filter(fun(P) -> player_criteria(P, Criteria) end, All),
    lists:sort(fun(P1, P2) ->
        to_integer(maps:get(<<"Overall">>, P1, <<"0">>)) >=
        to_integer(maps:get(<<"Overall">>, P2, <<"0">>))
    end, Filtered).

player_criteria(Player, Criteria) ->
    maps:fold(fun(Key, Value, Acc) ->
        Acc andalso check_player_criterion(Player, Key, Value)
    end, true, Criteria).

check_player_criterion(_, limit, _) -> true;
check_player_criterion(P, name, Name) ->
    team_matches(maps:get(<<"Name">>, P, <<>>), Name);
check_player_criterion(P, nationality, Nat) ->
    team_matches(maps:get(<<"Nationality">>, P, <<>>), Nat);
check_player_criterion(P, club, Club) ->
    team_matches(maps:get(<<"Club">>, P, <<>>), Club);
check_player_criterion(P, position, Pos) ->
    string:lowercase(maps:get(<<"Position">>, P, <<>>)) =:= string:lowercase(Pos);
check_player_criterion(P, min_rating, MinRating) ->
    to_integer(maps:get(<<"Overall">>, P, <<"0">>)) >= to_integer(MinRating);
check_player_criterion(_, _, _) -> true.

get_head_to_head(Team1, Team2, Criteria) ->
    All = find_matches_all(Criteria),
    H2H = lists:filter(fun(Match) ->
        #{home_team := Home, away_team := Away} = Match,
        (team_matches(Home, Team1) andalso team_matches(Away, Team2)) orelse
        (team_matches(Home, Team2) andalso team_matches(Away, Team1))
    end, All),
    Sorted = lists:sort(fun(A, B) ->
        maps:get(date, A, <<>>) >= maps:get(date, B, <<>>)
    end, H2H),
    compute_h2h(Team1, Team2, Sorted).

compute_h2h(Team1, Team2, Matches) ->
    Init = #{t1_wins => 0, t2_wins => 0, draws => 0, t1_goals => 0, t2_goals => 0},
    Stats = lists:foldl(fun(Match, Acc) ->
        #{home_team := Home, home_goal := HG, away_goal := AG} = Match,
        {T1G, T2G} = case team_matches(Home, Team1) of
            true  -> {HG, AG};
            false -> {AG, HG}
        end,
        Result = if T1G > T2G -> t1; T1G =:= T2G -> draw; true -> t2 end,
        Acc#{
            t1_wins  := maps:get(t1_wins, Acc)  + (if Result =:= t1 -> 1; true -> 0 end),
            t2_wins  := maps:get(t2_wins, Acc)  + (if Result =:= t2 -> 1; true -> 0 end),
            draws    := maps:get(draws, Acc)    + (if Result =:= draw -> 1; true -> 0 end),
            t1_goals := maps:get(t1_goals, Acc) + T1G,
            t2_goals := maps:get(t2_goals, Acc) + T2G
        }
    end, Init, Matches),
    #{
        team1         => Team1,
        team2         => Team2,
        total_matches => length(Matches),
        team1_wins    => maps:get(t1_wins, Stats),
        team2_wins    => maps:get(t2_wins, Stats),
        draws         => maps:get(draws, Stats),
        team1_goals   => maps:get(t1_goals, Stats),
        team2_goals   => maps:get(t2_goals, Stats),
        recent_matches => [format_match(M) || M <- lists:sublist(Matches, 5)]
    }.

get_standings(Competition, Season) ->
    Matches = find_matches_all(#{competition => Competition, season => Season}),
    TeamStats = lists:foldl(fun(Match, Acc) ->
        #{home_team := Home, away_team := Away,
          home_goal := HG, away_goal := AG} = Match,
        Acc1 = update_standing(Acc, Home, HG, AG),
        update_standing(Acc1, Away, AG, HG)
    end, #{}, Matches),
    Standings0 = maps:to_list(TeamStats),
    Sorted = lists:sort(fun({_, S1}, {_, S2}) ->
        Pts1 = maps:get(wins, S1) * 3 + maps:get(draws, S1),
        Pts2 = maps:get(wins, S2) * 3 + maps:get(draws, S2),
        if
            Pts1 =/= Pts2 -> Pts1 > Pts2;
            true ->
                GD1 = maps:get(goals_for, S1) - maps:get(goals_against, S1),
                GD2 = maps:get(goals_for, S2) - maps:get(goals_against, S2),
                GD1 >= GD2
        end
    end, Standings0),
    lists:map(fun({Pos, {Team, Stats}}) ->
        #{wins := W, draws := D, losses := L,
          played := P, goals_for := GF, goals_against := GA} = Stats,
        #{position => Pos, team => Team, played => P,
          wins => W, draws => D, losses => L,
          goals_for => GF, goals_against => GA,
          goal_difference => GF - GA, points => W * 3 + D}
    end, lists:zip(lists:seq(1, length(Sorted)), Sorted)).

update_standing(Acc, Team, GF, GA) ->
    Default = #{played => 0, wins => 0, draws => 0, losses => 0,
                goals_for => 0, goals_against => 0},
    S = maps:get(Team, Acc, Default),
    Result = if GF > GA -> win; GF =:= GA -> draw; true -> loss end,
    maps:put(Team, S#{
        played        := maps:get(played, S) + 1,
        goals_for     := maps:get(goals_for, S) + GF,
        goals_against := maps:get(goals_against, S) + GA,
        wins   := maps:get(wins, S)   + (if Result =:= win  -> 1; true -> 0 end),
        draws  := maps:get(draws, S)  + (if Result =:= draw -> 1; true -> 0 end),
        losses := maps:get(losses, S) + (if Result =:= loss -> 1; true -> 0 end)
    }, Acc).

compute_team_stats(TeamSearch, Matches) ->
    Init = #{played => 0, wins => 0, draws => 0, losses => 0,
             goals_for => 0, goals_against => 0,
             home_wins => 0, home_draws => 0, home_losses => 0,
             away_wins => 0, away_draws => 0, away_losses => 0},
    Stats = lists:foldl(fun(Match, Acc) ->
        #{home_team := Home, home_goal := HG, away_goal := AG} = Match,
        IsHome = team_matches(Home, TeamSearch),
        {GF, GA, Side} = case IsHome of
            true  -> {HG, AG, home};
            false -> {AG, HG, away}
        end,
        Result = if GF > GA -> win; GF =:= GA -> draw; true -> loss end,
        Acc#{
            played        := maps:get(played, Acc) + 1,
            goals_for     := maps:get(goals_for, Acc) + GF,
            goals_against := maps:get(goals_against, Acc) + GA,
            wins   := maps:get(wins, Acc)   + (if Result =:= win  -> 1; true -> 0 end),
            draws  := maps:get(draws, Acc)  + (if Result =:= draw -> 1; true -> 0 end),
            losses := maps:get(losses, Acc) + (if Result =:= loss -> 1; true -> 0 end),
            home_wins   := maps:get(home_wins, Acc)   + (if Side =:= home, Result =:= win  -> 1; true -> 0 end),
            home_draws  := maps:get(home_draws, Acc)  + (if Side =:= home, Result =:= draw -> 1; true -> 0 end),
            home_losses := maps:get(home_losses, Acc) + (if Side =:= home, Result =:= loss -> 1; true -> 0 end),
            away_wins   := maps:get(away_wins, Acc)   + (if Side =:= away, Result =:= win  -> 1; true -> 0 end),
            away_draws  := maps:get(away_draws, Acc)  + (if Side =:= away, Result =:= draw -> 1; true -> 0 end),
            away_losses := maps:get(away_losses, Acc) + (if Side =:= away, Result =:= loss -> 1; true -> 0 end)
        }
    end, Init, Matches),
    Played = maps:get(played, Stats),
    Wins = maps:get(wins, Stats),
    Draws = maps:get(draws, Stats),
    WinRate = case Played of
        0 -> 0.0;
        _ -> round(Wins * 1000.0 / Played) / 10.0
    end,
    Stats#{win_rate => WinRate, points => Wins * 3 + Draws}.

stats_biggest_wins(Criteria) ->
    Limit = to_integer(maps:get(limit, Criteria, 10)),
    Matches = find_matches_all(maps:remove(limit, Criteria)),
    WithDiff = [{abs(maps:get(home_goal, M) - maps:get(away_goal, M)), M} || M <- Matches],
    Sorted = lists:sort(fun({D1, _}, {D2, _}) -> D1 >= D2 end, WithDiff),
    Top = lists:sublist(Sorted, Limit),
    lists:map(fun({D, M}) ->
        Formatted = format_match(M),
        Formatted#{<<"goal_difference">> => D}
    end, Top).

stats_avg_goals(Criteria) ->
    Matches = find_matches_all(maps:remove(limit, Criteria)),
    Total = length(Matches),
    case Total of
        0 ->
            #{total_matches => 0, total_goals => 0, avg_goals_per_match => 0.0,
              home_wins => 0, away_wins => 0, draws => 0,
              home_win_rate => 0.0, away_win_rate => 0.0, draw_rate => 0.0};
        _ ->
            {TotalGoals, HomeWins, AwayWins, Draws} =
                lists:foldl(fun(M, {TG, HW, AW, D}) ->
                    HG = maps:get(home_goal, M, 0),
                    AG = maps:get(away_goal, M, 0),
                    {TG + HG + AG,
                     HW + (if HG > AG -> 1; true -> 0 end),
                     AW + (if AG > HG -> 1; true -> 0 end),
                     D  + (if HG =:= AG -> 1; true -> 0 end)}
                end, {0, 0, 0, 0}, Matches),
            Avg = round(TotalGoals * 100.0 / Total) / 100.0,
            #{
                total_matches       => Total,
                total_goals         => TotalGoals,
                avg_goals_per_match => Avg,
                home_wins           => HomeWins,
                away_wins           => AwayWins,
                draws               => Draws,
                home_win_rate       => round(HomeWins * 1000.0 / Total) / 1000.0,
                away_win_rate       => round(AwayWins * 1000.0 / Total) / 1000.0,
                draw_rate           => round(Draws * 1000.0 / Total) / 1000.0
            }
    end.

%%--------------------------------------------------------------------
%% Format Helpers (atom-keyed internal -> binary-keyed JSON-ready)
%%--------------------------------------------------------------------

format_match(Match) ->
    #{
        <<"date">>        => maps:get(date, Match, <<>>),
        <<"home_team">>   => maps:get(home_team, Match, <<>>),
        <<"away_team">>   => maps:get(away_team, Match, <<>>),
        <<"home_goal">>   => maps:get(home_goal, Match, 0),
        <<"away_goal">>   => maps:get(away_goal, Match, 0),
        <<"competition">> => maps:get(competition, Match, <<>>),
        <<"season">>      => maps:get(season, Match, 0),
        <<"round">>       => maps:get(round, Match, <<>>)
    }.

format_player(Player) ->
    #{
        <<"name">>          => maps:get(<<"Name">>, Player, <<>>),
        <<"age">>           => to_integer(maps:get(<<"Age">>, Player, <<"0">>)),
        <<"nationality">>   => maps:get(<<"Nationality">>, Player, <<>>),
        <<"overall">>       => to_integer(maps:get(<<"Overall">>, Player, <<"0">>)),
        <<"potential">>     => to_integer(maps:get(<<"Potential">>, Player, <<"0">>)),
        <<"club">>          => maps:get(<<"Club">>, Player, <<>>),
        <<"position">>      => maps:get(<<"Position">>, Player, <<>>),
        <<"jersey_number">> => maps:get(<<"Jersey Number">>, Player, <<>>),
        <<"height">>        => maps:get(<<"Height">>, Player, <<>>),
        <<"weight">>        => maps:get(<<"Weight">>, Player, <<>>)
    }.

format_standing(Entry) ->
    #{
        <<"position">>        => maps:get(position, Entry),
        <<"team">>            => maps:get(team, Entry),
        <<"played">>          => maps:get(played, Entry),
        <<"wins">>            => maps:get(wins, Entry),
        <<"draws">>           => maps:get(draws, Entry),
        <<"losses">>          => maps:get(losses, Entry),
        <<"goals_for">>       => maps:get(goals_for, Entry),
        <<"goals_against">>   => maps:get(goals_against, Entry),
        <<"goal_difference">> => maps:get(goal_difference, Entry),
        <<"points">>          => maps:get(points, Entry)
    }.

%%--------------------------------------------------------------------
%% Utilities
%%--------------------------------------------------------------------

normalize_team(Name) when is_binary(Name) ->
    Str = binary_to_list(string:trim(Name)),
    S1 = re:replace(Str, " - [A-Z]{2}$", "", [{return, list}]),
    S2 = re:replace(S1, "-[A-Z]{2}$", "", [{return, list}]),
    list_to_binary(string:trim(S2)).

%% BR-Football-Dataset uses different names; keep them distinct to avoid
%% double-counting with the primary Brasileirao_Matches.csv dataset.
normalize_tournament(<<"Copa do Brasil">>) -> <<"copa_brasil_stats">>;
normalize_tournament(<<"Serie A">>)        -> <<"serie_a_stats">>;
normalize_tournament(<<"Serie B">>)        -> <<"serie_b_stats">>;
normalize_tournament(<<"Serie C">>)        -> <<"serie_c_stats">>;
normalize_tournament(T) when is_binary(T) -> string:lowercase(T).

extract_date(DateTimeBin) when is_binary(DateTimeBin) ->
    Size = byte_size(DateTimeBin),
    if Size >= 10 -> binary:part(DateTimeBin, 0, 10);
       true -> DateTimeBin
    end.

normalize_br_date(DateBin) when is_binary(DateBin) ->
    case binary:split(DateBin, <<"/">>, [global]) of
        [D, M, Y] -> <<Y/binary, "-", M/binary, "-", D/binary>>;
        _ -> DateBin
    end.

extract_year(DateBin) when is_binary(DateBin) ->
    case byte_size(DateBin) >= 4 of
        true  -> to_integer(binary:part(DateBin, 0, 4));
        false -> 0
    end.

to_integer(N) when is_integer(N) -> N;
to_integer(B) when is_binary(B) ->
    Str = string:trim(binary_to_list(B)),
    case string:to_integer(Str) of
        {N, []} -> N;
        _ ->
            case string:to_float(Str) of
                {F, _} -> round(F);
                _ -> 0
            end
    end;
to_integer(_) -> 0.

team_matches(TeamName, SearchTerm) when is_binary(TeamName), is_binary(SearchTerm) ->
    %% Normalize search term so "Flamengo-RJ" matches stored "Flamengo".
    NormSearch = normalize_team(SearchTerm),
    try
        string:find(string:lowercase(TeamName), string:lowercase(NormSearch)) =/= nomatch
    catch _:_ ->
        %% Fall back to byte-level comparison for non-UTF-8 binaries.
        binary:match(TeamName, SearchTerm) =/= nomatch
    end;
team_matches(_, _) -> false.
