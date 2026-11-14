%%% Loads the six Kaggle CSV files into memory (persistent_term) as a small
%%% knowledge graph: matches, teams (canonical key -> display name) and players.
%%%
%%% A match is a map:
%%%   #{id, source, comp, season, date, time, round, stage, home, away,
%%%     home_raw, away_raw, hg, ag, arena, stats, dup}
%%% `home`/`away` are canonical team keys (see brsoccer_norm:team/1).
%%% `dup` marks a record that repeats a match already loaded from another
%%% file (the Serie A files overlap heavily); default queries skip those.
-module(brsoccer_data).
-export([ensure_loaded/0, load/0, load/1, unload/0, data_dir/0,
         matches/0, players/0, teams/0, display/1, summary/0, sources/0]).

-define(KEY, {?MODULE, db}).

sources() ->
    [{novo_campeonato, "novo_campeonato_brasileiro.csv"},
     {brasileirao, "Brasileirao_Matches.csv"},
     {copa_do_brasil, "Brazilian_Cup_Matches.csv"},
     {libertadores, "Libertadores_Matches.csv"},
     {br_football, "BR-Football-Dataset.csv"},
     {fifa, "fifa_data.csv"}].

data_dir() ->
    case os:getenv("BRSOCCER_DATA_DIR") of
        false -> application:get_env(brsoccer, data_dir, find_dir());
        Dir -> Dir
    end.

find_dir() ->
    Cands = ["data/kaggle", "../data/kaggle", "../../data/kaggle", "../../../data/kaggle",
             "../../../../data/kaggle"],
    case [D || D <- Cands, filelib:is_dir(D)] of
        [D | _] -> D;
        [] -> "data/kaggle"
    end.

ensure_loaded() ->
    case persistent_term:get(?KEY, undefined) of
        undefined -> load();
        _ -> ok
    end.

load() -> load(data_dir()).

-spec load(file:name_all()) -> ok | {error, term()}.
load(Dir) ->
    %% Each file is parsed and converted in its own short-lived process: the
    %% parsed rows are thousands of sub-binaries of the file contents, and
    %% keeping them all on one heap makes garbage collection very expensive.
    Each = fun(F) -> fun(R, Acc) -> [F(R) | Acc] end end,
    All = fun(F) -> {all, F} end,
    Loaders = [{novo_campeonato, Each(fun novo/1)},
               {brasileirao, Each(fun brasileirao/1)},
               {copa_do_brasil, All(fun cup/1)},
               {libertadores, All(fun libertadores/1)},
               {br_football, Each(fun br_football/1)},
               {fifa, Each(fun player/1)}],
    Files = sources(),
    Refs = [begin
                Path = filename:join(Dir, proplists:get_value(Src, Files)),
                {_, Ref} = spawn_monitor(fun() -> exit(load_file(Path, Loader)) end),
                {Src, Ref}
            end || {Src, Loader} <- Loaders],
    Results = [receive {'DOWN', Ref, process, _, Res} -> {Src, Res} end || {Src, Ref} <- Refs],
    case [E || {_, E} <- Results, element(1, E) =/= loaded] of
        [] ->
            Get = fun(S) -> {loaded, L} = proplists:get_value(S, Results), L end,
            Ms = lists:append([Get(S) || S <- [novo_campeonato, brasileirao, copa_do_brasil,
                                               libertadores, br_football]]),
            {Ms1, Teams} = finish(Ms),
            persistent_term:put(?KEY, #{matches => Ms1, teams => Teams, players => Get(fifa),
                                        dir => Dir}),
            ok;
        [E | _] -> {error, E}
    end.

load_file(Path, {all, F}) ->
    case brsoccer_csv:fold_file_maps(Path, fun(R, Acc) -> [R | Acc] end, []) of
        {ok, Rows} -> {loaded, [X || X <- F(lists:reverse(Rows)), X =/= skip]};
        {error, Reason} -> {load_error, {Path, Reason}}
    end;
load_file(Path, Fun) ->
    case brsoccer_csv:fold_file_maps(Path, Fun, []) of
        {ok, Out} -> {loaded, [X || X <- lists:reverse(Out), X =/= skip]};
        {error, Reason} -> {load_error, {Path, Reason}}
    end.

unload() -> persistent_term:erase(?KEY), ok.

db() ->
    case ensure_loaded() of
        ok -> ok;
        {error, E} -> erlang:error({brsoccer_data_not_loaded, E})
    end,
    persistent_term:get(?KEY).

matches() -> maps:get(matches, db()).
players() -> maps:get(players, db()).
teams() -> maps:get(teams, db()).

display(Key) -> maps:get(Key, teams(), Key).

summary() ->
    Ms = matches(),
    BySrc = lists:foldl(fun(#{source := S}, A) -> maps:update_with(S, fun(N) -> N + 1 end, 1, A) end,
                        #{}, Ms),
    #{matches_by_source => BySrc,
      unique_matches => length([M || #{dup := false} = M <- Ms]),
      total_match_records => length(Ms),
      teams => maps:size(teams()),
      players => length(players())}.

%% ------------------------------------------------------------ row mappers
%% Field accessor: trimmed and copied so no reference to the file binary is kept.
g(K, R) -> binary:copy(brsoccer_norm:trim(maps:get(K, R, <<>>))).

%% Memoised (per loader process) wrappers: the same few hundred names repeat
%% thousands of times.
memo(Tag, Arg, Fun) ->
    case get({Tag, Arg}) of
        undefined -> V = Fun(Arg), put({Tag, Arg}, V), V;
        V -> V
    end.

team(Raw) -> memo(team, Raw, fun brsoccer_norm:team/1).
fold(Text) -> memo(fold, Text, fun brsoccer_norm:fold/1).

base(Source, Comp, HomeRaw, AwayRaw, DateBin, HG, AG) ->
    {Date, Time} = case brsoccer_norm:parse_date(DateBin) of
                       undefined -> {undefined, undefined};
                       DT -> DT
                   end,
    #{source => Source, comp => Comp, date => Date, time => Time,
      home_raw => HomeRaw, away_raw => AwayRaw,
      hg => brsoccer_norm:to_int(HG), ag => brsoccer_norm:to_int(AG),
      season => undefined, round => undefined, stage => undefined,
      arena => undefined, stats => #{}, dup => false}.

novo(R) ->
    case g(<<"Equipe_mandante">>, R) of
        <<>> -> skip;
        Home ->
            M = base(novo_campeonato, serie_a, Home, g(<<"Equipe_visitante">>, R),
                     g(<<"Data">>, R), g(<<"Gols_mandante">>, R), g(<<"Gols_visitante">>, R)),
            M#{season => brsoccer_norm:to_int(g(<<"Ano">>, R)),
               round => brsoccer_norm:to_int(g(<<"Rodada">>, R)),
               arena => nonempty(g(<<"Arena">>, R))}
    end.

brasileirao(R) ->
    M = base(brasileirao, serie_a, g(<<"home_team">>, R), g(<<"away_team">>, R),
             g(<<"datetime">>, R), g(<<"home_goal">>, R), g(<<"away_goal">>, R)),
    M#{season => brsoccer_norm:to_int(g(<<"season">>, R)),
       round => brsoccer_norm:to_int(g(<<"round">>, R))}.

%% Cup rounds are numbered; the last round of a completed season (<= 2 legs)
%% is labelled as the final, the two before it semifinals / quarterfinals.
cup(Rows) ->
    Ms = [begin
              M = base(copa_do_brasil, copa_do_brasil, g(<<"home_team">>, R), g(<<"away_team">>, R),
                       g(<<"datetime">>, R), g(<<"home_goal">>, R), g(<<"away_goal">>, R)),
              M#{season => brsoccer_norm:to_int(g(<<"season">>, R)),
                 round => brsoccer_norm:to_int(g(<<"round">>, R))}
          end || R <- Rows],
    Counts = lists:foldl(fun(#{season := S, round := Rd}, A) ->
                                 maps:update_with({S, Rd}, fun(N) -> N + 1 end, 1, A)
                         end, #{}, Ms),
    MaxRound = maps:fold(fun({S, Rd}, _, A) when is_integer(Rd) ->
                                 maps:update_with(S, fun(X) -> max(X, Rd) end, Rd, A);
                            (_, _, A) -> A
                         end, #{}, Counts),
    [begin
         Max = maps:get(S, MaxRound, undefined),
         Complete = Max =/= undefined andalso maps:get({S, Max}, Counts) =< 2,
         Stage = if not Complete; not is_integer(Rd) -> undefined;
                    Rd =:= Max -> <<"final">>;
                    Rd =:= Max - 1 -> <<"semifinals">>;
                    Rd =:= Max - 2 -> <<"quarterfinals">>;
                    Rd =:= Max - 3 -> <<"round of 16">>;
                    true -> undefined
                 end,
         M#{stage => Stage}
     end || #{season := S, round := Rd} = M <- Ms].

%% A row with an unknown season ("NA") inherits the season of the previous row.
libertadores(Rows) ->
    {Ms, _} = lists:mapfoldl(
        fun(R, Last) ->
                M = base(libertadores, libertadores, g(<<"home_team">>, R), g(<<"away_team">>, R),
                         g(<<"datetime">>, R), g(<<"home_goal">>, R), g(<<"away_goal">>, R)),
                Season = case brsoccer_norm:to_int(g(<<"season">>, R)) of
                             undefined -> Last;
                             S -> S
                         end,
                {M#{season => Season, stage => nonempty(g(<<"stage">>, R))}, Season}
        end, undefined, Rows),
    Ms.

br_football(R) ->
    Comp = case brsoccer_norm:competition(g(<<"tournament">>, R)) of
               C when C =:= unknown; C =:= undefined -> other;
               C -> C
           end,
    M = base(br_football, Comp, g(<<"home">>, R), g(<<"away">>, R), g(<<"date">>, R),
             g(<<"home_goal">>, R), g(<<"away_goal">>, R)),
    Stats = maps:from_list(
              [{K, V} || {K, Col} <- [{home_corners, <<"home_corner">>}, {away_corners, <<"away_corner">>},
                                      {home_attacks, <<"home_attack">>}, {away_attacks, <<"away_attack">>},
                                      {home_shots, <<"home_shots">>}, {away_shots, <<"away_shots">>},
                                      {total_corners, <<"total_corners">>}],
                         V <- [brsoccer_norm:to_int(g(Col, R))], V =/= undefined]),
    %% The 2020 season was played until early 2021 (pandemic calendar).
    Season = case maps:get(date, M) of
                 {2021, Mo, D} when {Mo, D} < {3, 8} -> 2020;
                 {Y, _, _} -> Y;
                 undefined -> undefined
             end,
    M#{season => Season, time => nonempty(g(<<"time">>, R)), stats => Stats}.

nonempty(<<>>) -> undefined;
nonempty(<<"NA">>) -> undefined;
nonempty(B) -> B.

%% Assign ids + canonical team keys, build the team registry, flag duplicates.
%% Two records are the same match when competition, home and away team agree
%% and the dates are at most two days apart (sources disagree on time zones).
%% Records with a score win over score-less ones (fixtures not yet played
%% when a file was exported).
finish(Ms) ->
    {Keyed, {_, Teams}} = lists:mapfoldl(
        fun(#{home_raw := HR, away_raw := AR} = M, {Id, Teams}) ->
                {HK, HD} = team(HR),
                {AK, AD} = team(AR),
                {M#{id => Id, home => HK, away => AK},
                 {Id + 1, add_team(AK, AD, add_team(HK, HD, Teams))}}
        end, {1, #{}}, Ms),
    {Scored, Unscored} = lists:partition(fun(#{hg := HG, ag := AG}) ->
                                                 is_integer(HG) andalso is_integer(AG)
                                         end, Keyed),
    {Out, _} = lists:mapfoldl(
        fun(#{comp := Comp, home := HK, away := AK, date := Date, season := Season,
              hg := HG} = M, Seen) ->
                DKey = {Comp, HK, AK},
                League = lists:member(Comp, [serie_a, serie_b, serie_c]),
                %% League pairings are unique per season: a postponed fixture
                %% listed without score duplicates the played match even if
                %% the dates differ.
                SKey = {Comp, HK, AK, Season},
                if Date =:= undefined -> {M, Seen};
                   League, HG =:= undefined, is_map_key(SKey, Seen) -> {M#{dup := true}, Seen};
                   true ->
                        Day = calendar:date_to_gregorian_days(Date),
                        Days = maps:get(DKey, Seen, []),
                        case lists:any(fun(D) -> abs(D - Day) =< 2 end, Days) of
                            true -> {M#{dup := true}, Seen};
                            false -> {M, Seen#{DKey => [Day | Days], SKey => true}}
                        end
                end
        end, #{}, Scored ++ Unscored),
    {lists:sort(fun(#{id := A}, #{id := B}) -> A =< B end, Out), Teams}.

add_team(K, D, Teams) ->
    case Teams of
        #{K := _} -> Teams;
        _ -> Teams#{K => D}
    end.

%% ---------------------------------------------------------------- players
-define(SKILLS, [<<"Crossing">>, <<"Finishing">>, <<"HeadingAccuracy">>, <<"ShortPassing">>,
                 <<"Volleys">>, <<"Dribbling">>, <<"Curve">>, <<"FKAccuracy">>, <<"LongPassing">>,
                 <<"BallControl">>, <<"Acceleration">>, <<"SprintSpeed">>, <<"Agility">>,
                 <<"Reactions">>, <<"Balance">>, <<"ShotPower">>, <<"Jumping">>, <<"Stamina">>,
                 <<"Strength">>, <<"LongShots">>, <<"Aggression">>, <<"Interceptions">>,
                 <<"Positioning">>, <<"Vision">>, <<"Penalties">>, <<"Composure">>, <<"Marking">>,
                 <<"StandingTackle">>, <<"SlidingTackle">>, <<"GKDiving">>, <<"GKHandling">>,
                 <<"GKKicking">>, <<"GKPositioning">>, <<"GKReflexes">>]).

player(R) ->
    case g(<<"Name">>, R) of
        <<>> -> skip;
        Name ->
            Club = g(<<"Club">>, R),
            I = fun(K) -> brsoccer_norm:to_int(g(K, R)) end,
            #{id => I(<<"ID">>), name => Name, name_fold => brsoccer_norm:fold(Name),
              age => I(<<"Age">>), nationality => g(<<"Nationality">>, R),
              nationality_fold => fold(g(<<"Nationality">>, R)),
              overall => I(<<"Overall">>), potential => I(<<"Potential">>),
              club => Club, club_fold => fold(Club),
              club_key => case Club of <<>> -> <<>>; _ -> element(1, team(Club)) end,
              position => g(<<"Position">>, R), jersey => I(<<"Jersey Number">>),
              height => g(<<"Height">>, R), weight => g(<<"Weight">>, R),
              foot => g(<<"Preferred Foot">>, R), value => g(<<"Value">>, R),
              wage => g(<<"Wage">>, R),
              skills => maps:from_list([{S, V} || S <- ?SKILLS, V <- [I(S)], V =/= undefined])}
    end.
