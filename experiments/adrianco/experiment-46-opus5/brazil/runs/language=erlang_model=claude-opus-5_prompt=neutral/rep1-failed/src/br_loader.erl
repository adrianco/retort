%%%-------------------------------------------------------------------
%%% @doc Reads the six Kaggle CSV files into normalised records.
%%%
%%% Each source has its own column names, date format and team-name
%%% convention; the per-file functions below map them all onto
%%% `#match{}' / `#player{}' records with canonical team ids.
%%%
%%% Season handling: the Brazilian league runs inside a calendar year,
%%% except for the pandemic-shifted 2020 season whose last rounds were
%%% played in January/February 2021.  For the league competitions of
%%% `BR-Football-Dataset.csv' (which only carries a date) a match played
%%% in January or February therefore belongs to the previous season.
%%% @end
%%%-------------------------------------------------------------------
-module(br_loader).

-include("br_soccer.hrl").

-export([data_dir/0,
         data_files/0,
         load_all/1,
         load_file/2,
         load_matches/2,
         load_players/1,
         source_file/1,
         sources/0]).

-define(SERIE_A, <<"brasileirao_serie_a">>).
-define(SERIE_B, <<"brasileirao_serie_b">>).
-define(SERIE_C, <<"brasileirao_serie_c">>).
-define(CUP, <<"copa_do_brasil">>).
-define(LIB, <<"libertadores">>).

%%--------------------------------------------------------------------
%% @doc The match data sets, in descending order of trust.  When the
%% same fixture appears in more than one file the earlier source wins
%% and the later one only contributes extra statistics.
-spec sources() -> [atom()].
sources() ->
    [brasileirao_matches, novo_brasileirao, copa_do_brasil, libertadores, br_football].

-spec source_file(atom()) -> string().
source_file(brasileirao_matches) -> "Brasileirao_Matches.csv";
source_file(novo_brasileirao)    -> "novo_campeonato_brasileiro.csv";
source_file(copa_do_brasil)      -> "Brazilian_Cup_Matches.csv";
source_file(libertadores)        -> "Libertadores_Matches.csv";
source_file(br_football)         -> "BR-Football-Dataset.csv";
source_file(fifa_players)        -> "fifa_data.csv".

-spec data_files() -> [{atom(), string()}].
data_files() ->
    [{S, source_file(S)} || S <- sources() ++ [fifa_players]].

%%--------------------------------------------------------------------
%% @doc Locate `data/kaggle'.
%%
%% Honours `$BR_SOCCER_DATA_DIR' and the `data_dir' application
%% environment key, then walks up from the current directory and from
%% the code path so that it works from an escript, a release, `rebar3
%% shell' and a Common Test run alike.
-spec data_dir() -> file:filename() | undefined.
data_dir() ->
    Candidates =
        [os:getenv("BR_SOCCER_DATA_DIR"),
         application:get_env(br_soccer, data_dir, undefined)]
        ++ walk_up(element(2, file:get_cwd()))
        ++ walk_up(filename:dirname(code:which(?MODULE))),
    case [D || D <- Candidates, D =/= undefined, D =/= false, is_data_dir(D)] of
        [Dir | _] -> Dir;
        [] -> undefined
    end.

walk_up(Dir) ->
    walk_up(Dir, 6, []).

walk_up(_Dir, 0, Acc) -> lists:reverse(Acc);
walk_up(Dir, N, Acc) ->
    Candidate = filename:join([Dir, "data", "kaggle"]),
    Parent = filename:dirname(Dir),
    case Parent of
        Dir -> lists:reverse([Candidate | Acc]);
        _ -> walk_up(Parent, N - 1, [Candidate | Acc])
    end.

is_data_dir(Dir) ->
    filelib:is_regular(filename:join(Dir, source_file(brasileirao_matches))).

%%--------------------------------------------------------------------
%% @doc Load every data set from `Dir'.
-spec load_all(file:filename()) -> #{matches := [#match{}], players := [#player{}]}.
load_all(Dir) ->
    Matches = lists:append([load_matches(S, Dir) || S <- sources()]),
    #{matches => Matches, players => load_players(Dir)}.

%% @doc Load one data set by name (matches or players).
-spec load_file(atom(), file:filename()) -> [#match{}] | [#player{}].
load_file(fifa_players, Dir) -> load_players(Dir);
load_file(Source, Dir) -> load_matches(Source, Dir).

%%====================================================================
%% Matches
%%====================================================================

-spec load_matches(atom(), file:filename()) -> [#match{}].
load_matches(Source, Dir) ->
    Path = filename:join(Dir, source_file(Source)),
    Fun = row_parser(Source),
    case br_csv:fold_file(Path, fun(Row, Acc) -> add(Fun(Row), Acc) end, []) of
        {ok, Acc} -> lists:reverse(Acc);
        {error, Reason} -> error({cannot_read, Path, Reason})
    end.

add(skip, Acc) -> Acc;
add(Match, Acc) -> [Match | Acc].

row_parser(brasileirao_matches) -> fun brasileirao_row/1;
row_parser(novo_brasileirao)    -> fun novo_row/1;
row_parser(copa_do_brasil)      -> fun cup_row/1;
row_parser(libertadores)        -> fun libertadores_row/1;
row_parser(br_football)         -> fun br_football_row/1.

%% Brasileirao_Matches.csv
brasileirao_row(Row) ->
    Home = get_bin(<<"home_team">>, Row),
    Away = get_bin(<<"away_team">>, Row),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            {Date, Time} = datetime(get_bin(<<"datetime">>, Row)),
            make_match(brasileirao_matches, ?SERIE_A,
                       #{season => int(get_bin(<<"season">>, Row)),
                         date => Date, time => Time,
                         round => round_bin(get_bin(<<"round">>, Row)),
                         home => Home, away => Away,
                         home_goals => int(get_bin(<<"home_goal">>, Row)),
                         away_goals => int(get_bin(<<"away_goal">>, Row))})
    end.

%% novo_campeonato_brasileiro.csv (2003-2019, Portuguese column names)
novo_row(Row) ->
    Home = get_bin(<<"Equipe_mandante">>, Row),
    Away = get_bin(<<"Equipe_visitante">>, Row),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            Date = case br_date:parse_date(get_bin(<<"Data">>, Row)) of
                       {ok, D} -> D;
                       error -> undefined
                   end,
            Arena = get_bin(<<"Arena">>, Row),
            make_match(novo_brasileirao, ?SERIE_A,
                       #{season => int(get_bin(<<"Ano">>, Row)),
                         date => Date,
                         round => round_bin(get_bin(<<"Rodada">>, Row)),
                         home => Home, away => Away,
                         home_goals => int(get_bin(<<"Gols_mandante">>, Row)),
                         away_goals => int(get_bin(<<"Gols_visitante">>, Row)),
                         venue => empty_to_undefined(Arena)})
    end.

%% Brazilian_Cup_Matches.csv
cup_row(Row) ->
    Home = get_bin(<<"home_team">>, Row),
    Away = get_bin(<<"away_team">>, Row),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            {Date, Time} = datetime(get_bin(<<"datetime">>, Row)),
            RoundNo = get_bin(<<"round">>, Row),
            make_match(copa_do_brasil, ?CUP,
                       #{season => int(get_bin(<<"season">>, Row)),
                         date => Date, time => Time,
                         round => round_bin(RoundNo),
                         stage => cup_stage(RoundNo),
                         home => Home, away => Away,
                         home_goals => int(get_bin(<<"home_goal">>, Row)),
                         away_goals => int(get_bin(<<"away_goal">>, Row))})
    end.

%% Libertadores_Matches.csv
libertadores_row(Row) ->
    Home = get_bin(<<"home_team">>, Row),
    Away = get_bin(<<"away_team">>, Row),
    case {Home, Away} of
        {<<>>, _} -> skip;
        {_, <<>>} -> skip;
        _ ->
            {Date, Time} = datetime(get_bin(<<"datetime">>, Row)),
            Season = case int(get_bin(<<"season">>, Row)) of
                         undefined -> br_date:year(Date);
                         S -> S
                     end,
            make_match(libertadores, ?LIB,
                       #{season => Season, date => Date, time => Time,
                         stage => empty_to_undefined(get_bin(<<"stage">>, Row)),
                         home => Home, away => Away,
                         home_goals => int(get_bin(<<"home_goal">>, Row)),
                         away_goals => int(get_bin(<<"away_goal">>, Row))})
    end.

%% BR-Football-Dataset.csv (extended statistics, date only)
br_football_row(Row) ->
    Home = get_bin(<<"home">>, Row),
    Away = get_bin(<<"away">>, Row),
    Comp = competition_of(get_bin(<<"tournament">>, Row)),
    case {Home, Away, Comp} of
        {<<>>, _, _} -> skip;
        {_, <<>>, _} -> skip;
        {_, _, undefined} -> skip;
        _ ->
            Date = case br_date:parse_date(get_bin(<<"date">>, Row)) of
                       {ok, D} -> D;
                       error -> undefined
                   end,
            Time = case br_date:parse_time(get_bin(<<"time">>, Row)) of
                       {ok, T} -> T;
                       error -> undefined
                   end,
            make_match(br_football, Comp,
                       #{season => season_of(Comp, Date),
                         date => Date, time => Time,
                         home => Home, away => Away,
                         home_goals => int(get_bin(<<"home_goal">>, Row)),
                         away_goals => int(get_bin(<<"away_goal">>, Row)),
                         stats => match_stats(Row)})
    end.

competition_of(<<"Serie A">>) -> ?SERIE_A;
competition_of(<<"Serie B">>) -> ?SERIE_B;
competition_of(<<"Serie C">>) -> ?SERIE_C;
competition_of(<<"Copa do Brasil">>) -> ?CUP;
competition_of(Other) -> br_names:competition(Other).

%% League seasons that spill into January/February belong to the
%% previous year (the 2020 season finished in February 2021).
season_of(_Comp, undefined) -> undefined;
season_of(Comp, {Y, M, _}) when M =< 2 ->
    case is_league(Comp) of
        true -> Y - 1;
        false -> Y
    end;
season_of(_Comp, {Y, _, _}) -> Y.

is_league(?SERIE_A) -> true;
is_league(?SERIE_B) -> true;
is_league(?SERIE_C) -> true;
is_league(_) -> false.

match_stats(Row) ->
    Keys = [{<<"home_corner">>, home_corners}, {<<"away_corner">>, away_corners},
            {<<"home_attack">>, home_attacks}, {<<"away_attack">>, away_attacks},
            {<<"home_shots">>, home_shots}, {<<"away_shots">>, away_shots},
            {<<"total_corners">>, total_corners}],
    lists:foldl(
      fun({Col, Key}, Acc) ->
              case num(get_bin(Col, Row)) of
                  undefined -> Acc;
                  V -> Acc#{Key => V}
              end
      end, #{}, Keys).

cup_stage(<<>>) -> undefined;
cup_stage(Round) ->
    case int(Round) of
        undefined -> undefined;
        N -> <<"round ", (integer_to_binary(N))/binary>>
    end.

%%--------------------------------------------------------------------
%% Build a #match{} with canonical ids and a deterministic dedupe id.
make_match(Source, Competition, Fields) ->
    HomeName = maps:get(home, Fields),
    AwayName = maps:get(away, Fields),
    {HomeId, _, _, _} = br_names:canonical(HomeName),
    {AwayId, _, _, _} = br_names:canonical(AwayName),
    Season = maps:get(season, Fields, undefined),
    Date = maps:get(date, Fields, undefined),
    Id = match_id(Competition, Season, HomeId, AwayId, Date),
    #match{id = Id,
           sources = [Source],
           competition = Competition,
           season = Season,
           date = Date,
           time = maps:get(time, Fields, undefined),
           round = maps:get(round, Fields, undefined),
           stage = maps:get(stage, Fields, undefined),
           home = HomeId,
           away = AwayId,
           home_name = HomeName,
           away_name = AwayName,
           home_goals = maps:get(home_goals, Fields, undefined),
           away_goals = maps:get(away_goals, Fields, undefined),
           venue = maps:get(venue, Fields, undefined),
           stats = maps:get(stats, Fields, #{})}.

%% Round-robin leagues meet each pairing once per season, so the date is
%% deliberately left out of the key: the same fixture recorded with
%% slightly different dates in two files still collapses into one match.
%% Cup ties can repeat within a season, so there the date is part of the key.
match_id(Competition, Season, Home, Away, Date) ->
    SeasonBin = case Season of
                    undefined -> <<"?">>;
                    S -> integer_to_binary(S)
                end,
    Suffix = case is_league(Competition) of
                 true -> <<>>;
                 false -> <<"/", (br_date:format(Date))/binary>>
             end,
    <<Competition/binary, "/", SeasonBin/binary, "/", Home/binary, "/", Away/binary,
      Suffix/binary>>.

%%====================================================================
%% Players
%%====================================================================

-spec load_players(file:filename()) -> [#player{}].
load_players(Dir) ->
    Path = filename:join(Dir, source_file(fifa_players)),
    case br_csv:fold_file(Path, fun(Row, Acc) -> add(player_row(Row), Acc) end, []) of
        {ok, Acc} -> lists:reverse(Acc);
        {error, Reason} -> error({cannot_read, Path, Reason})
    end.

player_row(Row) ->
    Name = get_bin(<<"Name">>, Row),
    case {Name, int(get_bin(<<"ID">>, Row))} of
        {<<>>, _} -> skip;
        {_, undefined} -> skip;
        {_, Id} ->
            Club = empty_to_undefined(get_bin(<<"Club">>, Row)),
            ClubId = case Club of
                         undefined -> undefined;
                         C -> br_names:canonical_id(C)
                     end,
            #player{id = Id,
                    name = Name,
                    norm_name = br_text:normalize(Name),
                    age = int(get_bin(<<"Age">>, Row)),
                    nationality = empty_to_undefined(get_bin(<<"Nationality">>, Row)),
                    overall = int(get_bin(<<"Overall">>, Row)),
                    potential = int(get_bin(<<"Potential">>, Row)),
                    club = Club,
                    club_id = ClubId,
                    position = empty_to_undefined(get_bin(<<"Position">>, Row)),
                    jersey = int(get_bin(<<"Jersey Number">>, Row)),
                    height = empty_to_undefined(get_bin(<<"Height">>, Row)),
                    weight = empty_to_undefined(get_bin(<<"Weight">>, Row)),
                    value = empty_to_undefined(get_bin(<<"Value">>, Row)),
                    wage = empty_to_undefined(get_bin(<<"Wage">>, Row)),
                    foot = empty_to_undefined(get_bin(<<"Preferred Foot">>, Row)),
                    skills = skills(Row)}
    end.

skills(Row) ->
    Cols = [<<"Crossing">>, <<"Finishing">>, <<"HeadingAccuracy">>, <<"ShortPassing">>,
            <<"Volleys">>, <<"Dribbling">>, <<"Curve">>, <<"FKAccuracy">>,
            <<"LongPassing">>, <<"BallControl">>, <<"Acceleration">>, <<"SprintSpeed">>,
            <<"Agility">>, <<"Reactions">>, <<"Balance">>, <<"ShotPower">>, <<"Jumping">>,
            <<"Stamina">>, <<"Strength">>, <<"LongShots">>, <<"Aggression">>,
            <<"Interceptions">>, <<"Positioning">>, <<"Vision">>, <<"Penalties">>,
            <<"Composure">>, <<"Marking">>, <<"StandingTackle">>, <<"SlidingTackle">>,
            <<"GKDiving">>, <<"GKHandling">>, <<"GKKicking">>, <<"GKPositioning">>,
            <<"GKReflexes">>],
    lists:foldl(fun(Col, Acc) ->
                        case int(get_bin(Col, Row)) of
                            undefined -> Acc;
                            V -> Acc#{Col => V}
                        end
                end, #{}, Cols).

%%====================================================================
%% Field helpers
%%====================================================================

get_bin(Key, Row) ->
    br_text:trim(maps:get(Key, Row, <<>>)).

empty_to_undefined(<<>>) -> undefined;
empty_to_undefined(Bin) -> Bin.

round_bin(<<>>) -> undefined;
round_bin(Bin) -> Bin.

datetime(<<>>) -> {undefined, undefined};
datetime(Bin) ->
    case br_date:parse(Bin) of
        {ok, D, T} -> {D, T};
        error -> {undefined, undefined}
    end.

%% Integers may arrive as "3", "3.0" or "NA".
int(<<>>) -> undefined;
int(Bin) ->
    case num(Bin) of
        undefined -> undefined;
        N when is_integer(N) -> N;
        F when is_float(F) -> round(F)
    end.

num(<<C, _/binary>> = Bin) when (C >= $0 andalso C =< $9) orelse C =:= $- ->
    try binary_to_integer(Bin)
    catch error:badarg ->
            try binary_to_float(Bin)
            catch error:badarg -> undefined
            end
    end;
num(_) -> undefined.
