%% Context: reads the six Kaggle CSV files into one normalized match list and
%% one player list. Matches from every source share a shape (see to_match/2),
%% and duplicates across overlapping files are removed, keeping the first copy.
%% Team names are resolved to canonical clubs by soccer_teams.
-module(soccer_loader).
-export([load/1]).

-type match() :: #{source := atom(), date := integer(), season := integer(),
                   competition := binary(), stage := binary(), round := integer() | undefined,
                   home := binary(), away := binary(),
                   home_tokens := [binary()], away_tokens := [binary()],
                   home_goals := integer(), away_goals := integer()}.
-type player() :: #{name := binary(), name_tokens := [binary()], age := integer() | undefined,
                    nationality := binary(), nationality_tokens := [binary()],
                    overall := integer() | undefined, potential := integer() | undefined,
                    club := binary(), club_tokens := [binary()], position := binary()}.
-export_type([match/0, player/0]).

-spec load(file:filename()) -> #{matches := [match()], players := [player()]}.
load(Dir) ->
    Matches = lists:append([read_matches(Dir, Src) || Src <- sources()]),
    #{matches => dedupe(mark_cup_finals(Matches)),
      players => read_players(Dir)}.

sources() ->
    [{"Brasileirao_Matches.csv", brasileirao},
     {"novo_campeonato_brasileiro.csv", historical},
     {"Brazilian_Cup_Matches.csv", cup},
     {"Libertadores_Matches.csv", libertadores},
     {"BR-Football-Dataset.csv", br_football}].

read_matches(Dir, {File, Source}) ->
    Rows = read_rows(Dir, File),
    lists:filtermap(fun(R) ->
                        case to_match(Source, R) of
                            skip -> false;
                            M -> {true, M}
                        end
                    end, Rows).

read_players(Dir) ->
    Rows = read_rows(Dir, "fifa_data.csv"),
    lists:filtermap(fun(R) ->
                        case to_player(R) of
                            skip -> false;
                            P -> {true, P}
                        end
                    end, Rows).

read_rows(Dir, File) ->
    Path = filename:join(Dir, File),
    case file:read_file(Path) of
        {ok, Bin} -> soccer_csv:parse_maps(Bin);
        {error, Reason} -> erlang:error({cannot_read, Path, Reason})
    end.

get(Key, Row) ->
    maps:get(Key, Row, <<>>).

to_match(brasileirao, R) ->
    build(brasileirao, #{competition => <<"Brasileirão Série A"/utf8>>,
                         date => get(<<"datetime">>, R),
                         home => get(<<"home_team">>, R), away => get(<<"away_team">>, R),
                         home_goals => get(<<"home_goal">>, R), away_goals => get(<<"away_goal">>, R),
                         season => get(<<"season">>, R), round => get(<<"round">>, R)});
to_match(historical, R) ->
    build(historical, #{competition => <<"Brasileirão Série A"/utf8>>,
                        date => get(<<"Data">>, R),
                        home => get(<<"Equipe_mandante">>, R), away => get(<<"Equipe_visitante">>, R),
                        home_goals => get(<<"Gols_mandante">>, R), away_goals => get(<<"Gols_visitante">>, R),
                        season => get(<<"Ano">>, R), round => get(<<"Rodada">>, R)});
to_match(cup, R) ->
    build(cup, #{competition => <<"Copa do Brasil">>,
                 date => get(<<"datetime">>, R),
                 home => get(<<"home_team">>, R), away => get(<<"away_team">>, R),
                 home_goals => get(<<"home_goal">>, R), away_goals => get(<<"away_goal">>, R),
                 season => get(<<"season">>, R), round => get(<<"round">>, R)});
to_match(libertadores, R) ->
    build(libertadores, #{competition => <<"Copa Libertadores">>,
                          date => get(<<"datetime">>, R),
                          home => get(<<"home_team">>, R), away => get(<<"away_team">>, R),
                          home_goals => get(<<"home_goal">>, R), away_goals => get(<<"away_goal">>, R),
                          season => get(<<"season">>, R), stage => get(<<"stage">>, R)});
to_match(br_football, R) ->
    build(br_football, #{competition => football_competition(get(<<"tournament">>, R)),
                         date => get(<<"date">>, R),
                         home => get(<<"home">>, R), away => get(<<"away">>, R),
                         home_goals => get(<<"home_goal">>, R), away_goals => get(<<"away_goal">>, R)}).

%% The extended file has no season column, so the season comes from the date.
football_competition(<<"Serie A">>) -> <<"Brasileirão Série A"/utf8>>;
football_competition(<<"Serie B">>) -> <<"Brasileirão Série B"/utf8>>;
football_competition(<<"Serie C">>) -> <<"Brasileirão Série C"/utf8>>;
football_competition(Other) -> Other.

build(Source, F) ->
    Date = soccer_util:parse_date(maps:get(date, F)),
    HG = soccer_util:parse_number(maps:get(home_goals, F)),
    AG = soccer_util:parse_number(maps:get(away_goals, F)),
    case {Date, HG, AG} of
        {{ok, D}, H, A} when is_integer(H), is_integer(A) ->
            {Home, HomeTokens} = soccer_teams:resolve(maps:get(home, F)),
            {Away, AwayTokens} = soccer_teams:resolve(maps:get(away, F)),
            Season = case soccer_util:parse_number(maps:get(season, F, <<>>)) of
                         undefined -> D div 10000;
                         S -> S
                     end,
            Round = soccer_util:parse_number(maps:get(round, F, <<>>)),
            #{source => Source, date => D, season => Season,
              competition => maps:get(competition, F),
              stage => stage_label(maps:get(stage, F, undefined), Round),
              round => Round,
              home => Home, away => Away,
              home_tokens => HomeTokens,
              away_tokens => AwayTokens,
              home_goals => H, away_goals => A};
        _ ->
            skip
    end.

stage_label(undefined, undefined) -> <<>>;
stage_label(undefined, Round) -> iolist_to_binary(io_lib:format("Round ~B", [Round]));
stage_label(Stage, _) -> Stage.

to_player(R) ->
    Name = get(<<"Name">>, R),
    Overall = soccer_util:parse_number(get(<<"Overall">>, R)),
    case {soccer_util:trim(Name), Overall} of
        {<<>>, _} -> skip;
        {_, undefined} -> skip;
        {N, O} ->
            Nat = get(<<"Nationality">>, R),
            Club = get(<<"Club">>, R),
            #{name => N, name_tokens => soccer_util:tokens(N),
              age => soccer_util:parse_number(get(<<"Age">>, R)),
              nationality => Nat, nationality_tokens => soccer_util:tokens(Nat),
              overall => O,
              potential => soccer_util:parse_number(get(<<"Potential">>, R)),
              club => Club, club_tokens => soccer_util:tokens(Club),
              position => get(<<"Position">>, R)}
    end.

%% Copa do Brasil finals are two-legged: in each season, the highest numbered
%% round that holds exactly two matches is the final. Seasons whose last round
%% has another shape (e.g. 2021 in the data) get no final label.
mark_cup_finals(Matches) ->
    Cups = [M || #{source := cup, round := R} = M <- Matches, is_integer(R)],
    BySeason = maps:groups_from_list(fun(#{season := S}) -> S end, Cups),
    Finals = maps:from_list([{final_id(M), true}
                             || Ms <- maps:values(BySeason), M <- final_matches(Ms)]),
    [mark_final(M, Finals) || M <- Matches].

mark_final(#{source := cup} = M, Finals) ->
    case maps:is_key(final_id(M), Finals) of
        true -> M#{stage => <<"Final">>};
        false -> M
    end;
mark_final(M, _) ->
    M.

final_matches(Ms) ->
    Max = lists:max([maps:get(round, M) || M <- Ms]),
    case [M || M <- Ms, maps:get(round, M) =:= Max] of
        [_, _] = Top -> Top;
        _ -> []
    end.

final_id(M) ->
    {maps:get(date, M), maps:get(home, M), maps:get(away, M)}.

%% Same match can appear in several files (e.g. Brasileirão 2012-2019 in two
%% of them). The extended file has some dates a day off, so identity is the
%% season, competition, ordered canonical teams and the score, not the date.
dedupe(Matches) ->
    {_, Kept} = lists:foldl(fun(M, {Seen, Acc}) ->
                                K = {maps:get(season, M), maps:get(competition, M),
                                     maps:get(home, M), maps:get(away, M),
                                     maps:get(home_goals, M), maps:get(away_goals, M)},
                                case maps:is_key(K, Seen) of
                                    true -> {Seen, Acc};
                                    false -> {Seen#{K => true}, [M | Acc]}
                                end
                            end, {#{}, []}, Matches),
    lists:reverse(Kept).
