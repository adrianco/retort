%% Loads all six Kaggle CSV files into persistent_term.
-module(brsoccer_data).
-export([load/0, load/1, ensure_loaded/0, matches/0, players/0, data_dir/0, source_counts/0]).

-define(KEY, {?MODULE, db}).

ensure_loaded() ->
    case persistent_term:get(?KEY, undefined) of
        undefined -> load();
        _ -> ok
    end.

load() -> load(data_dir()).

load(Dir) ->
    F = fun(Name) -> brsoccer_csv:parse_file(filename:join(Dir, Name)) end,
    Sources = [{brasileirao, [m_brasileirao(R) || R <- F("Brasileirao_Matches.csv")]},
               {historical, [m_historical(R) || R <- F("novo_campeonato_brasileiro.csv")]},
               {copa_do_brasil, cup_finals([m_cup(R) || R <- F("Brazilian_Cup_Matches.csv")])},
               {libertadores, [m_libertadores(R) || R <- F("Libertadores_Matches.csv")]},
               {br_football, [m_brfootball(R) || R <- F("BR-Football-Dataset.csv")]}],
    Valid = [{S, [M || M <- Ms, is_integer(maps:get(hg, M)), is_integer(maps:get(ag, M))]}
             || {S, Ms} <- Sources],
    All = dedupe(lists:append([Ms || {_, Ms} <- Valid])),
    Sorted = lists:sort(fun(A, B) -> maps:get(date, A) >= maps:get(date, B) end, All),
    Players = [player(R) || R <- F("fifa_data.csv")],
    Counts = [{S, length(Ms)} || {S, Ms} <- Valid] ++ [{fifa, length(Players)}],
    persistent_term:put(?KEY, #{matches => Sorted, players => Players, counts => Counts}),
    ok.

matches() -> ensure_loaded(), maps:get(matches, persistent_term:get(?KEY)).
players() -> ensure_loaded(), maps:get(players, persistent_term:get(?KEY)).
source_counts() -> ensure_loaded(), maps:get(counts, persistent_term:get(?KEY)).

data_dir() ->
    case os:getenv("BRSOCCER_DATA") of
        false -> find_dir();
        D -> D
    end.

find_dir() ->
    {ok, Cwd} = file:get_cwd(),
    Here = case code:which(?MODULE) of
               P when is_list(P) -> filename:dirname(P);
               _ -> Cwd
           end,
    Candidates = [filename:join(D, "data/kaggle") || D <- ancestors(Cwd) ++ ancestors(Here)],
    case [C || C <- Candidates, filelib:is_file(filename:join(C, "fifa_data.csv"))] of
        [C | _] -> C;
        [] -> "data/kaggle"
    end.

ancestors(D) ->
    Parent = filename:dirname(D),
    case Parent of
        D -> [D];
        _ -> [D | ancestors(Parent)]
    end.

%% Keep the first occurrence of each fixture across sources. Sources disagree on
%% dates by a day (time zones), so leagues key on season+teams (each home fixture is
%% unique per season) and cups additionally on the score.
dedupe(Ms) ->
    {Out, _} = lists:foldl(
                 fun(M, {Acc, Seen}) ->
                         K = fixture_key(M),
                         Src = maps:get(source, M),
                         case maps:get(K, Seen, Src) of
                             Src -> {[M | Acc], Seen#{K => Src}};
                             _Other -> {Acc, Seen}
                         end
                 end, {[], #{}}, Ms),
    lists:reverse(Out).

fixture_key(#{competition := C, season := S, hk := H, ak := A, hg := HG, ag := AG}) ->
    case lists:member(C, [<<"Copa do Brasil">>, <<"Libertadores">>]) of
        true -> {C, S, H, A, HG, AG};
        false -> {C, S, H, A}
    end.

match(Source, Comp, Date, Season, Stage, Home, Away, HG, AG, Extra) ->
    D = brsoccer_norm:date(Date),
    S = case brsoccer_norm:int(Season) of
            undefined -> brsoccer_norm:int(binary:part(D, 0, min(4, byte_size(D))));
            I -> I
        end,
    Extra#{source => Source, competition => Comp, date => D, season => S, stage => Stage,
           home => brsoccer_norm:display(Home), away => brsoccer_norm:display(Away),
           hk => brsoccer_norm:team_key(Home), ak => brsoccer_norm:team_key(Away),
           ht => brsoccer_norm:tokens(Home), at => brsoccer_norm:tokens(Away),
           hg => goal(HG), ag => goal(AG)}.

goal(B) ->
    case brsoccer_norm:trim(B) of
        <<"NA">> -> undefined;
        <<>> -> undefined;
        S -> case string:to_float(S) of
                 {F, _} when is_float(F) -> round(F);
                 _ -> brsoccer_norm:int(S)
             end
    end.

g(K, R) -> maps:get(K, R, <<>>).

m_brasileirao(R) ->
    match(brasileirao, <<"Brasileirão"/utf8>>, g(<<"datetime">>, R), g(<<"season">>, R),
          <<"Round ", (g(<<"round">>, R))/binary>>, g(<<"home_team">>, R), g(<<"away_team">>, R),
          g(<<"home_goal">>, R), g(<<"away_goal">>, R), #{}).

m_historical(R) ->
    match(historical, <<"Brasileirão"/utf8>>, g(<<"Data">>, R), g(<<"Ano">>, R),
          <<"Round ", (g(<<"Rodada">>, R))/binary>>, g(<<"Equipe_mandante">>, R),
          g(<<"Equipe_visitante">>, R), g(<<"Gols_mandante">>, R), g(<<"Gols_visitante">>, R),
          #{arena => g(<<"Arena">>, R)}).

m_cup(R) ->
    M = match(copa_do_brasil, <<"Copa do Brasil">>, g(<<"datetime">>, R), g(<<"season">>, R),
              <<"Round ", (g(<<"round">>, R))/binary>>, g(<<"home_team">>, R), g(<<"away_team">>, R),
              g(<<"home_goal">>, R), g(<<"away_goal">>, R), #{}),
    M#{round => brsoccer_norm:int(g(<<"round">>, R))}.

%% The last round of each cup season is the final.
cup_finals(Ms) ->
    Max = lists:foldl(fun(#{season := S, round := Rd}, Acc) when is_integer(Rd) ->
                              Acc#{S => max(Rd, maps:get(S, Acc, 0))};
                         (_, Acc) -> Acc
                      end, #{}, Ms),
    [case maps:get(S, Max, none) of
         Rd -> M#{stage := <<"Final">>};
         _ -> M
     end || #{season := S, round := Rd} = M <- Ms].

m_libertadores(R) ->
    Stage = g(<<"stage">>, R),
    match(libertadores, <<"Libertadores">>, g(<<"datetime">>, R), g(<<"season">>, R),
          Stage, g(<<"home_team">>, R), g(<<"away_team">>, R),
          g(<<"home_goal">>, R), g(<<"away_goal">>, R), #{}).

m_brfootball(R) ->
    Comp = case g(<<"tournament">>, R) of
               <<"Serie A">> -> <<"Brasileirão"/utf8>>;
               T -> T
           end,
    Stats = maps:from_list([{binary_to_atom(K), goal(g(K, R))}
                            || K <- [<<"home_corner">>, <<"away_corner">>, <<"home_attack">>,
                                     <<"away_attack">>, <<"home_shots">>, <<"away_shots">>]]),
    Date = g(<<"date">>, R),
    %% The 2020 league season (COVID) finished in Feb 2021.
    Season = case Date of
                 <<"2021-0", M, _/binary>> when M =< $2, Comp =/= <<"Copa do Brasil">> -> <<"2020">>;
                 _ -> <<>>
             end,
    match(br_football, Comp, Date, Season, <<>>, g(<<"home">>, R), g(<<"away">>, R),
          g(<<"home_goal">>, R), g(<<"away_goal">>, R), #{stats => Stats}).

player(R) ->
    I = fun(K) -> brsoccer_norm:int(g(K, R)) end,
    Club = g(<<"Club">>, R),
    #{id => I(<<"ID">>), name => g(<<"Name">>, R), age => I(<<"Age">>),
      nationality => g(<<"Nationality">>, R), overall => I(<<"Overall">>),
      potential => I(<<"Potential">>), club => Club, club_key => brsoccer_norm:team_key(Club),
      club_toks => brsoccer_norm:tokens(Club),
      position => g(<<"Position">>, R), jersey => I(<<"Jersey Number">>),
      height => g(<<"Height">>, R), weight => g(<<"Weight">>, R), value => g(<<"Value">>, R),
      foot => g(<<"Preferred Foot">>, R),
      skills => maps:from_list([{K, I(K)} || K <- [<<"Crossing">>, <<"Finishing">>, <<"Dribbling">>,
                                                   <<"ShortPassing">>, <<"SprintSpeed">>, <<"Stamina">>,
                                                   <<"Strength">>, <<"GKReflexes">>]])}.
