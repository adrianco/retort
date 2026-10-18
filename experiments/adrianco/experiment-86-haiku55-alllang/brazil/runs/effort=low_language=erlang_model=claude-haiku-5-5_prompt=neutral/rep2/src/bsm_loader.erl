%% @doc Loads and normalises the Kaggle CSV files into match and player maps.
%%
%% Match: #{date, season, competition, stage, home, away, home_goals, away_goals}
%% Player: #{id, name, age, nationality, club, position, overall, potential, ...}
%%
%% Overlapping sources (Brasileirão 2012-2019 appears in two files, and the
%% BR-Football feed repeats Serie A/Copa do Brasil) are de-duplicated on
%% competition + season + home base + away base + score, keeping the first
%% source. The date is deliberately not part of the key: the BR-Football feed
%% is often a day or two off for the same match.
-module(bsm_loader).
-export([matches/1, players/1]).
-include("bsm.hrl").

-spec matches(file:filename()) -> [map()].
matches(Dir) ->
    Sources = [
        {"Brasileirao_Matches.csv", fun brasileirao_row/1},
        {"novo_campeonato_brasileiro.csv", fun novo_campeonato_row/1},
        {"BR-Football-Dataset.csv", fun br_football_row/1},
        {"Brazilian_Cup_Matches.csv", fun cup_row/1},
        {"Libertadores_Matches.csv", fun libertadores_row/1}
    ],
    Parsed = [M || {File, Mapper} <- Sources, Row <- read_maps(Dir, File),
                   M <- [Mapper(Row)], M =/= skip],
    fill_states(dedupe(Parsed)).

-spec players(file:filename()) -> [map()].
players(Dir) ->
    [P || R <- read_maps(Dir, "fifa_data.csv"), P <- [player(R)], P =/= skip].

read_maps(Dir, File) ->
    Path = filename:join(Dir, File),
    case file:read_file(Path) of
        {ok, Bin} -> bsm_csv:rows_as_maps(Bin);
        {error, Reason} -> erlang:error({dataset_unreadable, Path, Reason})
    end.

get(R, K) -> maps:get(K, R, <<>>).

brasileirao_row(R) ->
    build(get(R, <<"datetime">>), ?SERIE_A, round_stage(get(R, <<"round">>)),
          get(R, <<"home_team">>), get(R, <<"home_team_state">>),
          get(R, <<"away_team">>), get(R, <<"away_team_state">>),
          get(R, <<"home_goal">>), get(R, <<"away_goal">>)).

novo_campeonato_row(R) ->
    build(get(R, <<"Data">>), ?SERIE_A, round_stage(get(R, <<"Rodada">>)),
          get(R, <<"Equipe_mandante">>), get(R, <<"Mandante_UF">>),
          get(R, <<"Equipe_visitante">>), get(R, <<"Visitante_UF">>),
          get(R, <<"Gols_mandante">>), get(R, <<"Gols_visitante">>)).

br_football_row(R) ->
    build(get(R, <<"date">>), tournament_name(get(R, <<"tournament">>)), <<>>,
          get(R, <<"home">>), <<>>, get(R, <<"away">>), <<>>,
          get(R, <<"home_goal">>), get(R, <<"away_goal">>)).

cup_row(R) ->
    build(get(R, <<"datetime">>), <<"Copa do Brasil">>, round_stage(get(R, <<"round">>)),
          get(R, <<"home_team">>), <<>>, get(R, <<"away_team">>), <<>>,
          get(R, <<"home_goal">>), get(R, <<"away_goal">>)).

libertadores_row(R) ->
    build(get(R, <<"datetime">>), <<"Copa Libertadores">>, get(R, <<"stage">>),
          get(R, <<"home_team">>), <<>>, get(R, <<"away_team">>), <<>>,
          get(R, <<"home_goal">>), get(R, <<"away_goal">>)).

tournament_name(<<"Serie A">>) -> ?SERIE_A;
tournament_name(<<"Serie B">>) -> <<"Brasileirão Série B"/utf8>>;
tournament_name(<<"Serie C">>) -> <<"Brasileirão Série C"/utf8>>;
tournament_name(Other) -> Other.

round_stage(R) ->
    case bsm_text:parse_int(R) of
        I when is_integer(I) -> <<"Round ", (integer_to_binary(I))/binary>>;
        _ -> bsm_text:trim(R)
    end.

build(Date, Competition, Stage, Home, HomeState, Away, AwayState, HomeGoals, AwayGoals) ->
    case {bsm_date:parse(Date), bsm_text:parse_int(HomeGoals), bsm_text:parse_int(AwayGoals)} of
        {{ok, Iso}, Hg, Ag} when is_integer(Hg), is_integer(Ag), Home =/= <<>>, Away =/= <<>> ->
            #{date => Iso,
              season => binary_to_integer(binary:part(Iso, 0, 4)),
              competition => Competition,
              stage => Stage,
              home => bsm_team:parse(Home, HomeState),
              away => bsm_team:parse(Away, AwayState),
              home_goals => Hg,
              away_goals => Ag};
        _ ->
            skip
    end.

dedupe(Matches) -> dedupe(Matches, #{}, []).

%% Candidates are grouped by a coarse key, then confirmed with bsm_team:same/2
%% so that "Atletico-GO" and "Atletico-MG" playing the same opponent with the
%% same score are not merged.
dedupe([], _Seen, Acc) ->
    lists:reverse(Acc);
dedupe([M | Ms], Seen, Acc) ->
    K = {maps:get(competition, M), maps:get(season, M),
         maps:get(base, maps:get(home, M)), maps:get(base, maps:get(away, M)),
         maps:get(home_goals, M), maps:get(away_goals, M)},
    Existing = maps:get(K, Seen, []),
    case lists:any(fun(O) -> same_match(O, M) end, Existing) of
        true -> dedupe(Ms, Seen, Acc);
        false -> dedupe(Ms, Seen#{K => [M | Existing]}, [M | Acc])
    end.

same_match(A, B) ->
    bsm_team:same(maps:get(home, A), maps:get(home, B))
        andalso bsm_team:same(maps:get(away, A), maps:get(away, B)).

%% Feeds without state columns (BR-Football, Cup, Libertadores) inherit the
%% state of their team when that team has exactly one state across the data.
fill_states(Matches) ->
    Teams = [T || M <- Matches, T <- [maps:get(home, M), maps:get(away, M)]],
    Known = lists:foldl(fun(#{base := B, state := S}, Acc) when S =/= <<>> ->
                                Acc#{B => [S | maps:get(B, Acc, [])]};
                           (_, Acc) -> Acc
                        end, #{}, Teams),
    Unique = maps:from_list([{B, hd(Ss)} || {B, Ss} <- maps:to_list(Known),
                                            length(lists:usort(Ss)) =:= 1]),
    [M#{home => fill_team(Unique, maps:get(home, M)),
        away => fill_team(Unique, maps:get(away, M))} || M <- Matches].

fill_team(Unique, #{base := B, state := <<>>} = T) ->
    case maps:find(B, Unique) of
        {ok, S} -> T#{state => S};
        error -> T
    end;
fill_team(_Unique, T) ->
    T.

player(R) ->
    case bsm_text:trim(get(R, <<"Name">>)) of
        <<>> -> skip;
        Name ->
            #{id => int(R, <<"ID">>),
              name => Name,
              age => int(R, <<"Age">>),
              nationality => get(R, <<"Nationality">>),
              club => get(R, <<"Club">>),
              position => get(R, <<"Position">>),
              jersey_number => int(R, <<"Jersey Number">>),
              overall => int(R, <<"Overall">>),
              potential => int(R, <<"Potential">>),
              value => get(R, <<"Value">>),
              wage => get(R, <<"Wage">>),
              preferred_foot => get(R, <<"Preferred Foot">>),
              height => get(R, <<"Height">>),
              weight => get(R, <<"Weight">>)}
    end.

int(R, K) ->
    case bsm_text:parse_int(get(R, K)) of
        undefined -> 0;
        I -> I
    end.
