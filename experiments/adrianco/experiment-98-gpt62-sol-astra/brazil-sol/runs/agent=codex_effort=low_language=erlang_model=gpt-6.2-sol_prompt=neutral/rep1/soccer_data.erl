-module(soccer_data).
-export([load/1, csv/1, fold/1, team/1, competition/1, date/1]).

-define(A, <<"Serie A">>).
-define(CUP, <<"Copa do Brasil">>).
-define(LIB, <<"Libertadores">>).

load(Directory) ->
    Sources = [{"novo_campeonato_brasileiro.csv", historical},
               {"Brasileirao_Matches.csv", league},
               {"Brazilian_Cup_Matches.csv", cup},
               {"Libertadores_Matches.csv", libertadores},
               {"BR-Football-Dataset.csv", extended}],
    Raw = maps:from_list([{list_to_binary(File), load_matches(Directory, File, Kind)}
                          || {File, Kind} <- Sources]),
    Merged = lists:foldl(fun({File, _}, Acc) ->
        lists:foldl(fun merge_match/2, Acc, maps:get(list_to_binary(File), Raw))
    end, #{}, Sources),
    Matches = sort_matches(lists:append(maps:values(Merged))),
    Players = lists:sort(fun(A, B) ->
        {-maps:get(overall, A), maps:get(id, A)} < {-maps:get(overall, B), maps:get(id, B)}
    end, [player(Row) || Row <- read(Directory, "fifa_data.csv")]),
    #{matches => Matches, sources => maps:map(fun(_, Rows) -> sort_matches(Rows) end, Raw),
      players => Players}.

sort_matches(Rows) ->
    lists:reverse(lists:sort(fun(A, B) -> order(A) < order(B) end, Rows)).

order(M) -> {maps:get(date, M) =/= null, maps:get(date, M), maps:get(id, M)}.

load_matches(Dir, File, Kind) ->
    Rows = read(Dir, File),
    [match(Row, Kind, list_to_binary(File), N) || {N, Row} <- lists:enumerate(Rows)].

read(Dir, File) ->
    Path = filename:join(Dir, File),
    case file:read_file(Path) of
        {ok, Bytes} ->
            [Header | Rows] = csv(Bytes),
            [maps:from_list(lists:zip(Header, Row)) || Row <- Rows];
        {error, Reason} -> error({cannot_read_dataset, Path, Reason})
    end.

csv(<<239,187,191, Rest/binary>>) -> csv(Rest);
csv(Bytes) -> csv(Bytes, false, [], [], []).

csv(<<>>, true, _, _, _) -> error(unclosed_csv_quote);
csv(<<>>, false, [], [], Rows) -> lists:reverse(Rows);
csv(<<>>, false, Field, Row, Rows) -> lists:reverse([finish_row(Field, Row) | Rows]);
csv(<<$", $", Rest/binary>>, true, Field, Row, Rows) ->
    csv(Rest, true, [$" | Field], Row, Rows);
csv(<<$", Rest/binary>>, true, Field, Row, Rows) ->
    csv(Rest, false, Field, Row, Rows);
csv(<<$", Rest/binary>>, false, [], Row, Rows) ->
    csv(Rest, true, [], Row, Rows);
csv(<<$,, Rest/binary>>, false, Field, Row, Rows) ->
    csv(Rest, false, [], [finish_field(Field) | Row], Rows);
csv(<<$\r, $\n, Rest/binary>>, false, Field, Row, Rows) ->
    csv(<<$\n, Rest/binary>>, false, Field, Row, Rows);
csv(<<$\n, Rest/binary>>, false, [], [], Rows) ->
    csv(Rest, false, [], [], Rows);
csv(<<$\n, Rest/binary>>, false, Field, Row, Rows) ->
    csv(Rest, false, [], [], [finish_row(Field, Row) | Rows]);
csv(<<Byte, Rest/binary>>, Quoted, Field, Row, Rows) ->
    csv(Rest, Quoted, [Byte | Field], Row, Rows).

finish_field(Bytes) -> list_to_binary(lists:reverse(Bytes)).
finish_row(Field, Row) -> lists:reverse([finish_field(Field) | Row]).

match(R, Kind, File, N) ->
    {Comp, DateTime, Home, Away, HG, AG, Season, Extra} = fixture(R, Kind),
    Date = date(DateTime),
    Id = <<File/binary, "#", (integer_to_binary(N))/binary>>,
    #{id => Id, source => File, sources => [File], competition => Comp,
      date => Date, kickoff => kickoff(DateTime), season => Season, home_team => team(Home),
      away_team => team(Away), original_home => Home, original_away => Away,
      home_goals => number(HG), away_goals => number(AG), details => Extra}.

fixture(R, historical) ->
    {?A, get(R, <<"Data">>), get(R, <<"Equipe_mandante">>), get(R, <<"Equipe_visitante">>),
     get(R, <<"Gols_mandante">>), get(R, <<"Gols_visitante">>), number(get(R, <<"Ano">>)),
     #{round => number(get(R, <<"Rodada">>)), stadium => get(R, <<"Arena">>),
       dataset_id => get(R, <<"ID">>), home_state => get(R, <<"Mandante_UF">>),
       away_state => get(R, <<"Visitante_UF">>), recorded_winner => get(R, <<"Vencedor">>)}};
fixture(R, extended) ->
    Date = get(R, <<"date">>),
    Comp = competition(get(R, <<"tournament">>)),
    Season = extended_season(Comp, Date),
    Details = maps:from_list([{K, number(get(R, K))} || K <-
        [<<"home_corner">>, <<"away_corner">>, <<"home_attack">>, <<"away_attack">>,
         <<"home_shots">>, <<"away_shots">>, <<"total_corners">>, <<"ht_diff">>, <<"at_diff">>]]),
    Extra = case extended_final(Comp, Date) of
        true -> Details#{stage => <<"final">>};
        false -> Details
    end,
    {Comp, <<Date/binary, " ", (get(R, <<"time">>))/binary>>,
     get(R, <<"home">>), get(R, <<"away">>), get(R, <<"home_goal">>), get(R, <<"away_goal">>),
     Season, Extra#{<<"ht_result">> => get(R, <<"ht_result">>), <<"at_result">> => get(R, <<"at_result">>)}};
fixture(R, Kind) ->
    Round = number(get(R, <<"round">>)),
    Year = number(get(R, <<"season">>)),
    {Comp, Extra} = case Kind of
        league -> {?A, #{round => Round, home_state => get(R, <<"home_team_state">>),
                        away_state => get(R, <<"away_team_state">>)}};
        cup -> {?CUP, #{round => Round, stage => cup_stage(Year, Round)}};
        libertadores -> {?LIB, #{stage => get(R, <<"stage">>)}}
    end,
    {Comp, get(R, <<"datetime">>), get(R, <<"home_team">>), get(R, <<"away_team">>),
     get(R, <<"home_goal">>), get(R, <<"away_goal">>), Year, Extra}.

% The numbered cup source ends during the 2021 round of 16.
cup_stage(2021, 4) -> <<"round of 16">>;
cup_stage(2021, _) -> null;
cup_stage(Year, Round) ->
    Last = maps:get(Year, #{2012 => 6, 2013 => 8, 2014 => 8, 2015 => 8,
                            2016 => 7, 2017 => 8, 2018 => 8, 2019 => 8, 2020 => 8}),
    case Last - Round of
        0 -> <<"final">>;
        1 -> <<"semifinals">>;
        2 -> <<"quarterfinals">>;
        3 -> <<"round of 16">>;
        _ -> null
    end.

% The extended file uses calendar dates, including delayed 2020 fixtures.
extended_season(?CUP, D) when D >= <<"2021-01-01">>, D =< <<"2021-03-07">> -> 2020;
extended_season(Comp, D) when Comp =/= ?CUP, D >= <<"2021-01-01">>, D < <<"2021-05-01">> -> 2020;
extended_season(_, D) -> number(binary:part(D, 0, 4)).

% Final match dates represented in the extended cup file.
extended_final(?CUP, D) ->
    lists:member(D, [<<"2014-11-13">>, <<"2014-11-27">>, <<"2015-11-26">>, <<"2015-12-03">>,
                     <<"2016-11-23">>, <<"2016-12-07">>, <<"2017-09-08">>, <<"2017-09-28">>,
                     <<"2018-10-11">>, <<"2018-10-18">>, <<"2019-09-12">>, <<"2019-09-19">>,
                     <<"2021-03-01">>, <<"2021-03-07">>, <<"2021-12-12">>, <<"2021-12-16">>,
                     <<"2022-10-13">>, <<"2022-10-20">>, <<"2023-09-17">>, <<"2023-09-24">>]);
extended_final(_, _) -> false.

% The extended source labels a January 2016 local fixture as national Serie A.
merge_match(#{competition := ?A, date := <<"2016-01-30">>,
              home_team := <<"brasilia fc">>, away_team := <<"ca taguatinga">>}, Acc) -> Acc;
merge_match(M = #{competition := Comp, season := Year, home_team := Home, away_team := Away}, Acc) ->
    Key = {Comp, Year, Home, Away},
    Existing = maps:get(Key, Acc, []),
    Acc#{Key => merge_into(M, Existing)}.

merge_into(M, []) -> [M];
merge_into(M, [Old | Rest]) ->
    case same_fixture(M, Old) of
        true -> [combine(Old, M) | Rest];
        false -> [Old | merge_into(M, Rest)]
    end.

same_fixture(#{source := Source}, #{source := Source}) -> false;
same_fixture(#{competition := ?A}, _) -> true;
same_fixture(#{date := A}, #{date := B}) when A =/= null, B =/= null ->
    abs(day(A) - day(B)) =< 1;
same_fixture(_, _) -> false.

day(<<Y:4/binary, "-", M:2/binary, "-", D:2/binary>>) ->
    calendar:date_to_gregorian_days({binary_to_integer(Y), binary_to_integer(M), binary_to_integer(D)}).

combine(A, B) ->
    % Prefer a completed score and the competition-specific schedule metadata.
    Score = case B of
        #{season := 2016, competition := ?A, home_team := <<"chapecoense">>,
          away_team := <<"atletico mineiro">>, home_goals := null} -> B;
        #{home_goals := null} -> A;
        _ -> B
    end,
    Schedule = case maps:get(source, B) of <<"BR-Football-Dataset.csv">> -> A; _ -> B end,
    A#{home_goals => maps:get(home_goals, Score), away_goals => maps:get(away_goals, Score),
       date => maps:get(date, Schedule), kickoff => maps:get(kickoff, Schedule),
       sources => lists:usort(maps:get(sources, A) ++ maps:get(sources, B)),
       details => maps:merge(maps:get(details, B), maps:get(details, A))}.

player(R) ->
    Club = get(R, <<"Club">>),
    Position = get(R, <<"Position">>),
    #{id => number(get(R, <<"ID">>)), name => get(R, <<"Name">>),
      name_key => fold(get(R, <<"Name">>)), club => Club, club_key => team(Club),
      nationality => get(R, <<"Nationality">>), nationality_key => fold(get(R, <<"Nationality">>)), position => Position,
      overall => number(get(R, <<"Overall">>)), potential => number(get(R, <<"Potential">>)),
      age => number(get(R, <<"Age">>)), jersey_number => number(get(R, <<"Jersey Number">>)),
      height => get(R, <<"Height">>), weight => get(R, <<"Weight">>),
      attributes => maps:without([<<>>, <<"ID">>, <<"Name">>, <<"Club">>], R)}.

get(R, Key) -> maps:get(Key, R, <<>>).

number(B) ->
    case binary:split(B, <<".">>) of
        [Whole, <<"0">>] -> integer(Whole);
        [Whole] -> integer(Whole);
        _ -> null
    end.

integer(<<>>) -> null;
integer(B) ->
    try binary_to_integer(B) catch error:badarg -> null end.

date(<<Y:4/binary, "-", M:2/binary, "-", D:2/binary, _/binary>>) -> valid_date(Y,M,D);
date(<<D:2/binary, "/", M:2/binary, "/", Y:4/binary, _/binary>>) -> valid_date(Y,M,D);
date(_) -> null.

valid_date(Y, M, D) ->
    try calendar:valid_date({binary_to_integer(Y), binary_to_integer(M), binary_to_integer(D)}) of
        true -> <<Y/binary, "-", M/binary, "-", D/binary>>;
        false -> null
    catch error:badarg -> null
    end.

kickoff(<<_:10/binary, Sep, Time:8/binary, _/binary>>) when Sep =:= $ ; Sep =:= $T -> Time;
kickoff(_) -> null.

fold(Bin) ->
    Decomposed = unicode:characters_to_nfd_binary(string:casefold(Bin)),
    Plain = re:replace(Decomposed, "\\p{M}+", <<"">>, [global, unicode, {return, binary}]),
    trim_key(re:replace(Plain, <<"[^\\p{L}\\p{N}]+">>, <<" ">>,
                           [global, unicode, {return, binary}])).

trim_key(<<" ", Rest/binary>>) -> trim_key(Rest);
trim_key(<<>>) -> <<>>;
trim_key(Bin) ->
    case binary:last(Bin) of
        $  -> binary:part(Bin, 0, byte_size(Bin) - 1);
        _ -> Bin
    end.

team(Bin) ->
    case fold(Bin) of
        <<"sport club corinthians paulista">> -> <<"corinthians">>;
        <<"sao paulo fc">> -> <<"sao paulo">>;
        <<"clube de regatas do flamengo">> -> <<"flamengo">>;
        <<"fluminense football club">> -> <<"fluminense">>;
        <<"sociedade esportiva palmeiras">> -> <<"palmeiras">>;
        <<"santos futebol clube">> -> <<"santos">>;
        <<"santos fc">> -> <<"santos">>;
        <<"gremio foot ball porto alegrense">> -> <<"gremio">>;
        <<"sport club internacional">> -> <<"internacional">>;
        <<"fortaleza esporte clube">> -> <<"fortaleza">>;
        <<"fortaleza fc">> -> <<"fortaleza">>;
        <<"ec bahia">> -> <<"bahia">>;
        <<"ec juventude">> -> <<"juventude">>;
        <<"santa cruz fc">> -> <<"santa cruz">>;
        <<"sport recife">> -> <<"sport">>;
        <<"sport club do recife">> -> <<"sport">>;
        <<"botafogo fr">> -> <<"botafogo">>;
        <<"botafogo rj">> -> <<"botafogo">>;
        <<"atletico mg">> -> <<"atletico mineiro">>;
        <<"clube atletico mineiro">> -> <<"atletico mineiro">>;
        <<"atletico go">> -> <<"atletico goianiense">>;
        <<"atletico pr">> -> <<"athletico paranaense">>;
        <<"athletico pr">> -> <<"athletico paranaense">>;
        <<"atletico paranaense">> -> <<"athletico paranaense">>;
        <<"athletico">> -> <<"athletico paranaense">>;
        <<"club athletico paranaense">> -> <<"athletico paranaense">>;
        <<"vasco da gama", _/binary>> -> <<"vasco">>;
        <<"bragantino", _/binary>> -> <<"red bull bragantino">>;
        Folded -> strip_state(Folded)
    end.

strip_state(Name) ->
    Parts = binary:split(Name, <<" ">>, [global]),
    case lists:reverse(Parts) of
        [State | RevBase] when RevBase =/= [] ->
            Base = iolist_to_binary(lists:join(<<" ">>, lists:reverse(RevBase))),
            Ambiguous = [<<"america">>, <<"botafogo">>, <<"csa">>, <<"nacional">>,
                         <<"operario">>, <<"sao jose">>, <<"santa cruz">>, <<"vitoria">>,
                         <<"ypiranga">>, <<"remo">>, <<"sao raimundo">>, <<"ferroviario">>],
            Default = lists:member({Base, State}, [{<<"csa">>, <<"al">>}, {<<"santa cruz">>, <<"pe">>},
                         {<<"vitoria">>, <<"ba">>}, {<<"remo">>, <<"pa">>}, {<<"ferroviario">>, <<"ce">>}]),
            States = [<<"ac">>,<<"al">>,<<"ap">>,<<"am">>,<<"ba">>,<<"ce">>,<<"df">>,<<"es">>,
                      <<"go">>,<<"ma">>,<<"mt">>,<<"ms">>,<<"mg">>,<<"pa">>,<<"pb">>,<<"pr">>,
                      <<"pe">>,<<"pi">>,<<"rj">>,<<"rn">>,<<"rs">>,<<"ro">>,<<"rr">>,<<"sc">>,
                      <<"sp">>,<<"se">>,<<"to">>],
            case Default orelse (lists:member(State, States) andalso not lists:member(Base, Ambiguous)) of
                true -> Base;
                false -> Name
            end;
        _ -> Name
    end.

competition(Bin) ->
    case fold(Bin) of
        <<"brasileirao">> -> ?A;
        <<"brasileirao serie a">> -> ?A;
        <<"campeonato brasileiro">> -> ?A;
        <<"campeonato brasileiro serie a">> -> ?A;
        <<"serie a">> -> ?A;
        <<"serie b">> -> <<"Serie B">>;
        <<"serie c">> -> <<"Serie C">>;
        <<"copa do brasil">> -> ?CUP;
        <<"brazilian cup">> -> ?CUP;
        <<"copa libertadores">> -> ?LIB;
        <<"copa libertadores da america">> -> ?LIB;
        <<"libertadores">> -> ?LIB;
        _ -> Bin
    end.
