%% Loads the six Kaggle CSV files into memory (persistent_term).
%%
%% A match is a map:
%%   #{comp => serie_a | serie_b | serie_c | copa_do_brasil | libertadores,
%%     source => atom(), date => {Y,M,D} | undefined, season => integer() | undefined,
%%     round => integer() | undefined, stage => binary() | undefined,
%%     home => Key, away => Key, hg => integer() | undefined, ag => ...,
%%     extra => map()}
%%
%% Several files overlap (three of them contain Serie A seasons), so besides
%% the full list a de-duplicated list is kept and used by default for queries.
-module(bs_data).
-export([ensure_loaded/0, load/1, data_dir/0, matches/0, all_matches/0, players/0,
         sources/0, parse_date/1, comp_label/1]).

-define(PT(K), {brsoccer, K}).

ensure_loaded() ->
    case persistent_term:get(?PT(loaded), false) of
        true -> ok;
        false -> load(data_dir())
    end.

data_dir() ->
    Cands = [os:getenv("BRSOCCER_DATA_DIR"),
             filename:join(["data", "kaggle"]),
             script_relative()],
    case [D || D <- Cands, is_list(D), filelib:is_regular(filename:join(D, "fifa_data.csv"))] of
        [D | _] -> D;
        [] -> filename:join(["data", "kaggle"])
    end.

script_relative() ->
    try filename:join([filename:dirname(filename:absname(escript:script_name())),
                       "..", "..", "..", "data", "kaggle"])
    catch _:_ -> false
    end.

matches() -> persistent_term:get(?PT(matches)).
all_matches() -> persistent_term:get(?PT(all_matches)).
players() -> persistent_term:get(?PT(players)).
sources() -> persistent_term:get(?PT(sources)).

comp_label(serie_a) -> <<"Brasileirão"/utf8>>;
comp_label(serie_b) -> <<"Série B"/utf8>>;
comp_label(serie_c) -> <<"Série C"/utf8>>;
comp_label(copa_do_brasil) -> <<"Copa do Brasil">>;
comp_label(libertadores) -> <<"Copa Libertadores">>.

-spec load(file:filename()) -> ok | {error, term()}.
load(Dir) ->
    try
        %% Order = priority when the same match appears in several files.
        Raw = [{brasileirao, read(Dir, "Brasileirao_Matches.csv", fun brasileirao/1)},
               {novo_brasileirao, read(Dir, "novo_campeonato_brasileiro.csv", fun novo/1)},
               {copa_do_brasil, read(Dir, "Brazilian_Cup_Matches.csv", fun cup/1)},
               {libertadores, read(Dir, "Libertadores_Matches.csv", fun libertadores/1)},
               {br_football, read(Dir, "BR-Football-Dataset.csv", fun br_football/1)}],
        Players = read(Dir, "fifa_data.csv", fun player/1),
        {All, BareMap, Display} = normalise_teams(lists:append([Ms || {_, Ms} <- Raw])),
        All1 = mark_cup_finals(All),
        Dedup = dedup(drop_mislabelled(All1)),
        Counts = lists:foldl(
                   fun(#{home := H, away := A}, M) ->
                           Inc = fun(V) -> V + 1 end,
                           maps:update_with(A, Inc, 1, maps:update_with(H, Inc, 1, M))
                   end, #{}, Dedup),
        Sources = [{S, length(Ms)} || {S, Ms} <- Raw] ++ [{fifa_players, length(Players)}],
        persistent_term:put(?PT(bare_map), BareMap),
        persistent_term:put(?PT(team_display), Display),
        persistent_term:put(?PT(team_counts), Counts),
        persistent_term:put(?PT(all_matches), All1),
        persistent_term:put(?PT(matches), Dedup),
        persistent_term:put(?PT(players), Players),
        persistent_term:put(?PT(sources), Sources),
        persistent_term:put(?PT(loaded), true),
        ok
    catch
        throw:{load_error, _} = E -> {error, E}
    end.

read(Dir, File, Fun) ->
    Path = filename:join(Dir, File),
    case file:read_file(Path) of
        {ok, Bin} -> lists:filtermap(Fun, bs_csv:parse_maps(Bin));
        {error, Reason} -> throw({load_error, {Path, Reason}})
    end.

%% --- row converters --------------------------------------------------------

brasileirao(R) ->
    match(serie_a, brasileirao, R, <<"datetime">>, <<"home_team">>, <<"away_team">>,
          <<"home_goal">>, <<"away_goal">>,
          #{season => int(f(<<"season">>, R)), round => int(f(<<"round">>, R))}).

cup(R) ->
    match(copa_do_brasil, copa_do_brasil, R, <<"datetime">>, <<"home_team">>, <<"away_team">>,
          <<"home_goal">>, <<"away_goal">>,
          #{season => int(f(<<"season">>, R)), round => int(f(<<"round">>, R))}).

libertadores(R) ->
    match(libertadores, libertadores, R, <<"datetime">>, <<"home_team">>, <<"away_team">>,
          <<"home_goal">>, <<"away_goal">>,
          #{season => int(f(<<"season">>, R)), stage => bs_team:fold(f(<<"stage">>, R))}).

novo(R) ->
    Extra = #{arena => f(<<"Arena">>, R)},
    match(serie_a, novo_brasileirao, R, <<"Data">>, <<"Equipe_mandante">>, <<"Equipe_visitante">>,
          <<"Gols_mandante">>, <<"Gols_visitante">>,
          #{season => int(f(<<"Ano">>, R)), round => int(f(<<"Rodada">>, R)), extra => Extra}).

br_football(R) ->
    Comp = case bs_team:fold(f(<<"tournament">>, R)) of
               <<"serie a">> -> serie_a;
               <<"serie b">> -> serie_b;
               <<"serie c">> -> serie_c;
               <<"copa do brasil">> -> copa_do_brasil;
               _ -> undefined
           end,
    Extra = maps:from_list(
              [{K, V} || {K, Col} <- [{home_corners, <<"home_corner">>}, {away_corners, <<"away_corner">>},
                                      {home_shots, <<"home_shots">>}, {away_shots, <<"away_shots">>},
                                      {home_attacks, <<"home_attack">>}, {away_attacks, <<"away_attack">>}],
                         V <- [int(f(Col, R))], V =/= undefined]),
    case Comp of
        undefined -> false;
        _ ->
            match(Comp, br_football, R, <<"date">>, <<"home">>, <<"away">>,
                  <<"home_goal">>, <<"away_goal">>, #{extra => Extra})
    end.

match(Comp, Source, R, DateC, HomeC, AwayC, HgC, AgC, More) ->
    Home = trim(f(HomeC, R)),
    Away = trim(f(AwayC, R)),
    Date = parse_date(f(DateC, R)),
    case Home =:= <<>> orelse Away =:= <<>> of
        true -> false;
        false ->
            M0 = #{comp => Comp, source => Source, date => Date,
                   season => undefined, round => undefined, stage => undefined,
                   home_raw => Home, away_raw => Away,
                   hg => int(f(HgC, R)), ag => int(f(AgC, R)), extra => #{}},
            M = maps:merge(M0, More),
            {true, case {maps:get(season, M), Date} of
                       {undefined, {Y, _, _}} -> M#{season => Y};
                       _ -> M
                   end}
    end.

player(R) ->
    case f(<<"Name">>, R) of
        <<>> -> false;
        Name ->
            Club = f(<<"Club">>, R),
            Nat = f(<<"Nationality">>, R),
            Skills = [{S, V} || S <- skill_columns(), V <- [int(f(S, R))], V =/= undefined],
            {true, #{id => int(f(<<"ID">>, R)), name => Name, age => int(f(<<"Age">>, R)),
                     nationality => Nat, overall => int(f(<<"Overall">>, R)),
                     potential => int(f(<<"Potential">>, R)), club => Club,
                     position => f(<<"Position">>, R), jersey => int(f(<<"Jersey Number">>, R)),
                     height => f(<<"Height">>, R), weight => f(<<"Weight">>, R),
                     foot => f(<<"Preferred Foot">>, R), value => f(<<"Value">>, R),
                     wage => f(<<"Wage">>, R), skills => Skills,
                     name_f => bs_team:fold(Name), club_f => bs_team:fold(Club),
                     nat_f => bs_team:fold(Nat),
                     club_key => case Club of
                                     <<>> -> undefined;
                                     _ -> case bs_team:classify(Club) of
                                              {club, K} -> K;
                                              _ -> undefined
                                          end
                                 end}}
    end.

skill_columns() ->
    [<<"Crossing">>, <<"Finishing">>, <<"HeadingAccuracy">>, <<"ShortPassing">>, <<"Volleys">>,
     <<"Dribbling">>, <<"Curve">>, <<"FKAccuracy">>, <<"LongPassing">>, <<"BallControl">>,
     <<"Acceleration">>, <<"SprintSpeed">>, <<"Agility">>, <<"Reactions">>, <<"Balance">>,
     <<"ShotPower">>, <<"Jumping">>, <<"Stamina">>, <<"Strength">>, <<"LongShots">>,
     <<"Aggression">>, <<"Interceptions">>, <<"Positioning">>, <<"Vision">>, <<"Penalties">>].

%% --- team normalisation ----------------------------------------------------

normalise_teams(Ms) ->
    Names = lists:usort(lists:append([[H, A] || #{home_raw := H, away_raw := A} <- Ms])),
    Classified = maps:from_list([{N, bs_team:classify(N)} || N <- Names]),
    %% A bare name ("Tupi") is merged with its "base-uf" form ("Tupi MG") when
    %% exactly one such form exists in the data.
    Ufs = maps:fold(fun(_, {uf, FB, _, Code}, Acc) ->
                            maps:update_with(FB, fun(L) -> lists:usort([Code | L]) end, [Code], Acc);
                       (_, _, Acc) -> Acc
                    end, #{}, Classified),
    BareMap = maps:from_list([{FB, <<FB/binary, "-", Code/binary>>} || FB := [Code] <- Ufs]),
    Keys = maps:map(fun(_, C) -> bs_team:key(C, BareMap) end, Classified),
    Display = maps:fold(
                fun(N, C, Acc) ->
                        K = maps:get(N, Keys),
                        D = case C of
                                {uf, _, Base, Code} -> <<Base/binary, "-", (string:uppercase(Code))/binary>>;
                                {bare, _, Name} -> Name;
                                {club, _} -> K
                            end,
                        case Acc of
                            #{K := Old} when byte_size(Old) >= byte_size(D) -> Acc;
                            _ -> Acc#{K => D}
                        end
                end, #{}, Classified),
    Display2 = maps:merge(Display, maps:with(maps:values(Keys), bs_team:club_displays())),
    All = [maps:without([home_raw, away_raw],
                        M#{home => maps:get(H, Keys), away => maps:get(A, Keys)})
           || #{home_raw := H, away_raw := A} = M <- Ms],
    {All, BareMap, Display2}.

%% The cup file only has numeric rounds; the last round of a season with at
%% most two matches (two-legged final) is tagged as the final.
mark_cup_finals(Ms) ->
    Rounds = lists:foldl(
               fun(#{source := copa_do_brasil, season := S, round := R}, Acc) when is_integer(R) ->
                       maps:update_with(S, fun(L) -> [R | L] end, [R], Acc);
                  (_, Acc) -> Acc
               end, #{}, Ms),
    Finals = maps:filtermap(
               fun(_, Rs) ->
                       Max = lists:max(Rs),
                       case length([R || R <- Rs, R =:= Max]) =< 2 of
                           true -> {true, Max};
                           false -> false
                       end
               end, Rounds),
    [case M of
         #{source := copa_do_brasil, season := S, round := R} when map_get(S, Finals) =:= R ->
             M#{stage => <<"final">>};
         _ -> M
     end || M <- Ms].

%% The extended statistics file labels a few state-league games as national
%% competitions. Where a dedicated file covers the same competition and
%% season, its rows are only accepted for teams that file knows.
drop_mislabelled(Ms) ->
    Known = maps:from_list(
              lists:append([[{{C, S}, true}, {{C, S, H}, true}, {{C, S, A}, true}]
                            || #{source := Src, comp := C, season := S, home := H, away := A} <- Ms,
                               Src =/= br_football])),
    [M || #{source := Src, comp := C, season := S, home := H, away := A} = M <- Ms,
          Src =/= br_football orelse not is_map_key({C, S}, Known)
              orelse (is_map_key({C, S, H}, Known) andalso is_map_key({C, S, A}, Known))].

%% Same competition, same home and away team, dates at most two days apart
%% => same match. Earlier sources win.
dedup(Ms) ->
    %% Played matches first, so a row with a score beats an unplayed fixture.
    {Played, Unplayed} = lists:partition(fun(#{hg := G}) -> is_integer(G) end, Ms),
    %% A fixture without score that was played on another date (rescheduled)
    %% is dropped as well.
    Done = #{{C, S, H, A} => true || #{comp := C, season := S, home := H, away := A} <- Played},
    Pending = [M || #{comp := C, season := S, home := H, away := A} = M <- Unplayed,
                    not is_map_key({C, S, H, A}, Done)],
    {Kept, _} =
        lists:foldl(
          fun(#{comp := C, home := H, away := A, date := D} = M, {Acc, Seen}) ->
                  K = {C, H, A},
                  Days = maps:get(K, Seen, []),
                  case D of
                      undefined -> {[M | Acc], Seen};
                      _ ->
                          N = calendar:date_to_gregorian_days(D),
                          case lists:any(fun(X) -> abs(X - N) =< 2 end, Days) of
                              true -> {Acc, Seen};
                              false -> {[M | Acc], Seen#{K => [N | Days]}}
                          end
                  end
          end, {[], #{}}, Played ++ Pending),
    lists:reverse(Kept).

%% --- field helpers ---------------------------------------------------------

f(K, R) -> maps:get(K, R, <<>>).

%% string:trim/1 is slow on binaries (it compiles a search pattern per call).
trim(<<C, R/binary>>) when C =:= $\s; C =:= $\t -> trim(R);
trim(<<>>) -> <<>>;
trim(B) ->
    case binary:last(B) of
        C when C =:= $\s; C =:= $\t; C =:= $\r -> trim(binary:part(B, 0, byte_size(B) - 1));
        _ -> B
    end.

int(B) ->
    T = trim(B),
    try binary_to_integer(T)
    catch _:_ ->
            try trunc(binary_to_float(T))
            catch _:_ -> undefined
            end
    end.

%% Accepts "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003".
-spec parse_date(binary()) -> calendar:date() | undefined.
parse_date(B0) ->
    case trim(B0) of
        <<Y:4/binary, "-", M:2/binary, "-", D:2/binary, _/binary>> -> date(Y, M, D);
        <<D:2/binary, "/", M:2/binary, "/", Y:4/binary, _/binary>> -> date(Y, M, D);
        _ -> undefined
    end.

date(Y, M, D) ->
    try {binary_to_integer(Y), binary_to_integer(M), binary_to_integer(D)} of
        Date -> case calendar:valid_date(Date) of true -> Date; false -> undefined end
    catch _:_ -> undefined
    end.
