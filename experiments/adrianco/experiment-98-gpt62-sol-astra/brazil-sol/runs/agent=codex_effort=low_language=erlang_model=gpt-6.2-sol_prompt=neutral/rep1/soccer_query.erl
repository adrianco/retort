-module(soccer_query).
-export([tools/0, run/3]).

tools() ->
    Match = [team, opponent, venue, competition, season, seasons, date_from, date_to, stage, round,
             source, status, derby],
    Page = [limit, offset],
    [tool(<<"find_matches">>, <<"Find fixtures or scores, newest first. Team and opponent match either orientation unless venue is given. Use stage for finals or knockout rounds, derby=true for traditional rivalries, and status=scheduled for fixtures without scores.">>, Match ++ Page ++ [sort], []),
     tool(<<"team_stats">>, <<"Calculate wins, draws, losses, goals and win rate. Includes home/away splits and breakdowns by competition and season. Set opponent for head-to-head.">>, Match, [team]),
     tool(<<"standings">>, <<"Calculate a league table from recorded scores, with points, goals, provisional relegation positions and coverage. Use find_matches for knockout brackets.">>, [competition, season, source | Page], [competition, season]),
     tool(<<"analyze_matches">>, <<"Calculate goals per match, home win rate and biggest wins for a selection, with season and competition breakdowns. Includes team rankings by wins, win rate, points or goals. Venue affects the team rankings.">>, Match ++ Page ++ [rank_by, min_matches], []),
     tool(<<"find_players">>, <<"Search the FIFA snapshot by player name, nationality, club, or position (including forward, midfielder, defender and goalkeeper). Sorted by overall rating. Clubs reflect the snapshot. Request include_attributes for detailed skill ratings.">>, [name, nationality, club, club_match, position, include_attributes | Page], []),
     tool(<<"club_profile">>, <<"Join match statistics and FIFA player records for the same club. The season filter applies to matches. Player memberships come from a single FIFA snapshot.">>, Match ++ Page ++ [position, include_attributes], [team]),
     tool(<<"data_coverage">>, <<"List available dataset files, record counts and data limitations, including the absence of goalscorer events.">>, [], [])].

tool(Name, Description, Fields, Required) ->
    #{name => Name, description => Description,
      annotations => #{readOnlyHint => true, openWorldHint => false},
      inputSchema => #{type => <<"object">>, additionalProperties => false,
                       properties => maps:from_list([{key(F), field(F)} || F <- Fields]),
                       required => [key(F) || F <- Required]}}.

key(Atom) -> atom_to_binary(Atom).

field(venue) -> enum([<<"home">>, <<"away">>, <<"either">>]);
field(status) -> enum([<<"played">>, <<"scheduled">>]);
field(sort) -> enum([<<"newest">>, <<"oldest">>, <<"biggest_win">>]);
field(rank_by) -> enum([<<"wins">>, <<"win_rate">>, <<"points">>, <<"goals_for">>]);
field(derby) -> #{type => <<"boolean">>};
field(include_attributes) -> #{type => <<"boolean">>};
field(season) -> integer_field(1, 9999);
field(seasons) -> #{type => <<"array">>, items => integer_field(1, 9999), minItems => 1, maxItems => 100};
field(club_match) -> enum([<<"exact">>, <<"contains">>]);
field(round) -> integer_field(1, 100);
field(limit) -> (integer_field(1, 500))#{default => 25};
field(offset) -> (integer_field(0, 1000000))#{default => 0};
field(min_matches) -> (integer_field(1, 1000000))#{default => 1};
field(team) -> string_field(<<"Club name. Accents, common aliases and state suffixes are supported.">>);
field(opponent) -> string_field(<<"Second club in a head-to-head query.">>);
field(competition) -> string_field(<<"Serie A (Brasileirão), Serie B, Serie C, Copa do Brasil or Libertadores."/utf8>>);
field(source) -> string_field(<<"Exact CSV filename. Selects the original records from that match source. Omit for merged fixtures.">>);
field(stage) -> string_field(<<"Knockout or group stage, for example final, semifinals, knockout, or group stage.">>);
field(date_from) -> string_field(<<"Inclusive start date, YYYY-MM-DD or DD/MM/YYYY.">>);
field(date_to) -> string_field(<<"Inclusive end date, YYYY-MM-DD or DD/MM/YYYY.">>);
field(_) -> #{type => <<"string">>, minLength => 1}.

enum(Values) -> #{type => <<"string">>, enum => Values}.
integer_field(Min, Max) -> #{type => <<"integer">>, minimum => Min, maximum => Max}.
string_field(Description) -> #{type => <<"string">>, minLength => 1, description => Description}.

run(Name, Args, Data) ->
    try
        Schema = case [S || #{name := N, inputSchema := S} <- tools(), N =:= Name] of
            [Found] -> Found;
            [] -> invalid(<<"Unknown soccer tool">>)
        end,
        validate(Args, Schema),
        {ok, execute(Name, Args, Data)}
    catch throw:{invalid, Message} -> {error, Message}
    end.

validate(Args, #{properties := Properties, required := Required}) when is_map(Args) ->
    lists:foreach(fun(K) ->
        case maps:is_key(K, Args) of
            true -> ok;
            false -> invalid(<<"Missing argument: ", K/binary>>)
        end
    end, Required),
    maps:foreach(fun(K, V) ->
        case valid(V, maps:get(K, Properties, #{})) of
            true -> ok;
            false -> invalid(<<"Invalid or unknown argument: ", K/binary>>)
        end
    end, Args);
validate(_, _) -> invalid(<<"arguments must be an object">>).

valid(V, #{enum := Values}) -> lists:member(V, Values);
valid(V, #{type := <<"string">>}) -> is_binary(V) andalso string:trim(V) =/= <<>>;
valid(V, #{type := <<"boolean">>}) -> is_boolean(V);
valid(V, #{type := <<"array">>, items := Items, minItems := Min, maxItems := Max}) ->
    is_list(V) andalso length(V) >= Min andalso length(V) =< Max andalso
        lists:all(fun(Item) -> valid(Item, Items) end, V);
valid(V, #{minimum := Min, maximum := Max}) -> is_integer(V) andalso V >= Min andalso V =< Max;
valid(_, _) -> false.

invalid(Message) -> throw({invalid, Message}).
arg(Key, Args, Default) -> maps:get(key(Key), Args, Default).

execute(<<"find_matches">>, A, D) ->
    Matches = matches(A, D),
    Sorted = case arg(sort, A, <<"newest">>) of
        <<"newest">> -> Matches;
        <<"oldest">> -> lists:reverse([M || M = #{date := Date} <- Matches, Date =/= null])
                        ++ [M || M = #{date := null} <- Matches];
        <<"biggest_win">> -> [M || M = #{goal_margin := N} <- biggest(Matches), N > 0]
    end,
    page(matches, Sorted, A);
execute(<<"team_stats">>, A, D) -> team_stats(A, matches(A, D));
execute(<<"standings">>, A, D) -> standings(A, matches(A, D));
execute(<<"analyze_matches">>, A, D) -> analyze(A, matches(A, D));
execute(<<"find_players">>, A, D) -> players(A, D);
execute(<<"club_profile">>, A, D) ->
    #{team => team_stats(A, matches(A, D)),
      fifa_snapshot => players(A#{<<"club">> => arg(team, A, <<>>)}, D)};
execute(<<"data_coverage">>, _, D) ->
    #{match_sources => maps:map(fun(_, Rows) ->
          #{rows => length(Rows), competitions => lists:usort([C || #{competition := C} <- Rows]),
            seasons => lists:usort([Y || #{season := Y} <- Rows, is_integer(Y)])}
      end, maps:get(sources, D)),
      merged_fixtures => length(maps:get(matches, D)),
      player_source => <<"fifa_data.csv">>, player_rows => length(maps:get(players, D)),
      goalscorers_available => false,
      notes => <<"Coverage varies by season. Null fixture scores are excluded from computed records. FIFA club affiliations reflect the supplied snapshot. League tables use match results and omit administrative adjustments and official tie-breakers beyond wins, goal difference and goals scored.">>}.

matches(Args, Data) ->
    Tests = maps:fold(fun match_filter/3, [], Args),
    Rows = case arg(source, Args, undefined) of
        undefined -> maps:get(matches, Data);
        Source -> case maps:find(Source, maps:get(sources, Data)) of
            {ok, Found} -> Found;
            error -> invalid(<<"Unknown match source. See data_coverage for filenames.">>)
        end
    end,
    Lower = bound(date_from, Args),
    Upper = bound(date_to, Args),
    case Lower =/= undefined andalso Upper =/= undefined andalso Lower > Upper of
        true -> invalid(<<"date_from must be on or before date_to">>);
        false -> ok
    end,
    Team = soccer_data:team(arg(team, Args, <<>>)),
    Opponent = soccer_data:team(arg(opponent, Args, <<>>)),
    Venue = arg(venue, Args, <<"either">>),
    [M || M = #{home_team := H, away_team := A, date := Date} <- Rows,
          involved(Team, Opponent, Venue, H, A),
          within(Date, Lower, Upper), lists:all(fun(F) -> F(M) end, Tests)].

bound(Key, Args) ->
    case arg(Key, Args, undefined) of
        undefined -> undefined;
        Value -> case soccer_data:date(Value) of
            null -> invalid(<<"Invalid date: ", Value/binary>>);
            Date -> Date
        end
    end.

within(Date, Lower, Upper) ->
    (Lower =:= undefined orelse (Date =/= null andalso Date >= Lower)) andalso
    (Upper =:= undefined orelse (Date =/= null andalso Date =< Upper)).

involved(T, O, V, H, A) ->
    (V =/= <<"away">> andalso compatible(T, H) andalso compatible(O, A)) orelse
    (V =/= <<"home">> andalso compatible(T, A) andalso compatible(O, H)).

compatible(<<>>, _) -> true;
compatible(T, T) -> true;
compatible(_, _) -> false.

match_filter(<<"competition">>, Value, Tests) ->
    C = soccer_data:competition(Value),
    [fun(M) -> maps:get(competition, M) =:= C end | Tests];
match_filter(<<"season">>, Year, Tests) ->
    [fun(M) -> maps:get(season, M) =:= Year end | Tests];
match_filter(<<"seasons">>, Years, Tests) ->
    [fun(M) -> lists:member(maps:get(season, M), Years) end | Tests];
match_filter(<<"round">>, Round, Tests) ->
    [fun(M) -> maps:get(round, maps:get(details, M), null) =:= Round end | Tests];
match_filter(<<"stage">>, Value, Tests) ->
    Stage = stage(Value),
    [fun(M) -> stage_matches(Stage, maps:get(stage, maps:get(details, M), null)) end | Tests];
match_filter(<<"status">>, Status, Tests) ->
    [fun(M) -> played(M) =:= (Status =:= <<"played">>) end | Tests];
match_filter(<<"derby">>, IsDerby, Tests) ->
    [fun(M) -> derby(M) =:= IsDerby end | Tests];
match_filter(_, _, Tests) -> Tests.

stage_matches(<<"knockout">>, Stage) ->
    lists:member(Stage, [<<"round of 16">>, <<"quarterfinals">>, <<"semifinals">>, <<"final">>]);
stage_matches(Stage, Actual) -> Stage =:= Actual.

stage(Value) ->
    case soccer_data:fold(Value) of
        <<"finals">> -> <<"final">>;
        <<"semifinal">> -> <<"semifinals">>;
        <<"semi finals">> -> <<"semifinals">>;
        <<"quarterfinal">> -> <<"quarterfinals">>;
        <<"quarter finals">> -> <<"quarterfinals">>;
        Folded -> Folded
    end.

derby(#{home_team := H, away_team := A}) ->
    lists:any(fun(Rivals) -> lists:member(H, Rivals) andalso lists:member(A, Rivals) end,
        [[<<"flamengo">>, <<"fluminense">>, <<"vasco">>, <<"botafogo">>],
         [<<"corinthians">>, <<"palmeiras">>, <<"santos">>, <<"sao paulo">>],
         [<<"gremio">>, <<"internacional">>],
         [<<"cruzeiro">>, <<"atletico mineiro">>],
         [<<"athletico paranaense">>, <<"coritiba">>],
         [<<"bahia">>, <<"vitoria">>],
         [<<"ceara">>, <<"fortaleza">>],
         [<<"sport">>, <<"nautico">>, <<"santa cruz">>],
         [<<"goias">>, <<"vila nova">>, <<"atletico goianiense">>],
         [<<"avai">>, <<"figueirense">>], [<<"paysandu">>, <<"remo">>],
         [<<"ponte preta">>, <<"guarani">>], [<<"abc">>, <<"america rn">>]]).

played(#{home_goals := H, away_goals := A}) -> is_integer(H) andalso is_integer(A).

page(Key, Rows, A) ->
    Offset = arg(offset, A, 0),
    Limit = arg(limit, A, 25),
    Total = length(Rows),
    Count = min(Offset, Total),
    Next = case Offset + Limit < Total of true -> Offset + Limit; false -> null end,
    #{Key => lists:sublist(Rows, Count + 1, Limit), total => Total,
      offset => Offset, limit => Limit, next_offset => Next}.

biggest(Rows) ->
    Ranked = lists:reverse(lists:keysort(1, [{margin(M), M} || M <- lists:reverse(Rows), played(M)])),
    strip_margins(Ranked).

strip_margins(Rows) -> [M#{goal_margin => Margin} || {Margin, M} <- Rows].
margin(#{home_goals := H, away_goals := A}) -> abs(H - A).

team_stats(Args, Rows) ->
    Team = soccer_data:team(arg(team, Args, <<>>)),
    Opponent = soccer_data:team(arg(opponent, Args, <<>>)),
    Played = [M || M <- Rows, played(M)],
    CompGroups = groups(competition, Played),
    SeasonGroups = groups(season, Played),
    #{team => Team, opponent => case Opponent of <<>> -> null; _ -> Opponent end,
      fixtures => length(Rows), record => record(Team, Played),
      home => record(Team, [M || M = #{home_team := H} <- Played, H =:= Team]),
      away => record(Team, [M || M = #{away_team := A} <- Played, A =:= Team]),
      by_competition => [#{competition => C, record => record(Team, Ms)} || {C, Ms} <- CompGroups],
      by_season => [#{season => S, record => record(Team, Ms)} || {S, Ms} <- SeasonGroups],
      head_to_head => case Opponent of
          <<>> -> null;
          _ -> #{team => record(Team, Played), opponent => record(Opponent, Played)}
      end}.

groups(Key, Rows) ->
    lists:sort(maps:to_list(lists:foldl(fun(M, Acc) ->
        maps:update_with(maps:get(Key, M), fun(Ms) -> [M | Ms] end, [M], Acc)
    end, #{}, Rows))).

record(Team, Rows) ->
    summarize(lists:foldl(fun
        (#{home_team := H, home_goals := F, away_goals := A}, Acc) when H =:= Team ->
            tally(F, A, Acc);
        (#{home_goals := A, away_goals := F}, Acc) -> tally(F, A, Acc)
    end, {0,0,0,0,0}, Rows)).

tally(F, A, {W,D,L,GF,GA}) when F > A -> {W+1,D,L,GF+F,GA+A};
tally(F, A, {W,D,L,GF,GA}) when F < A -> {W,D,L+1,GF+F,GA+A};
tally(F, A, {W,D,L,GF,GA}) -> {W,D+1,L,GF+F,GA+A}.

summarize({W,D,L,GF,GA}) ->
    N = W + D + L,
    #{matches => N, wins => W, draws => D, losses => L, goals_for => GF, goals_against => GA,
      goal_difference => GF - GA, points => 3*W + D, win_rate => ratio(W, N)}.

ratio(_, 0) -> null;
ratio(Value, Total) -> Value / Total.

table(Rows, Venue, Rank, Minimum) ->
    Counts = lists:foldl(fun(#{home_team := H, away_team := A, home_goals := HG, away_goals := AG}, Acc) ->
        case Venue of
            <<"home">> -> add_team(H, HG, AG, Acc);
            <<"away">> -> add_team(A, AG, HG, Acc);
            <<"either">> -> add_team(A, AG, HG, add_team(H, HG, AG, Acc))
        end
    end, #{}, Rows),
    Entries = [(summarize(Count))#{team => T} || {T, Count} <- maps:to_list(Counts)],
    Ranked = lists:sort(fun(A, B) -> ranking(A, Rank) < ranking(B, Rank) end,
                         [E || E = #{matches := N} <- Entries, N >= Minimum]),
    [E#{rank => N} || {N, E} <- lists:enumerate(Ranked)].

add_team(T, F, A, Counts) ->
    maps:update_with(T, fun(X) -> tally(F, A, X) end, tally(F, A, {0,0,0,0,0}), Counts).

ranking(M, Rank) ->
    #{points := P, wins := W, goal_difference := GD, goals_for := GF, team := T} = M,
    {-maps:get(Rank, M), -P, -W, -GD, -GF, T}.

standings(A, Matches) ->
    Comp = soccer_data:competition(arg(competition, A, <<>>)),
    Season = arg(season, A, undefined),
    case lists:member(Comp, [<<"Serie A">>, <<"Serie B">>, <<"Serie C">>]) of
        false -> invalid(<<"Standings require Serie A, Serie B or Serie C. Use find_matches for knockout results.">>);
        true -> ok
    end,
    Played = [M || M <- Matches, played(M)],
    Teams = table(Played, <<"either">>, points, 1),
    Expected = expected_matches(Comp, Season),
    Complete = Expected =/= null andalso length(Played) =:= Expected andalso
        length(Teams) > 1 andalso
        lists:all(fun(#{matches := N}) -> N =:= 2 * (length(Teams) - 1) end, Teams),
    Leader = case Teams of [#{team := T} | _] -> T; [] -> null end,
    Relegation = case Complete andalso Comp =:= <<"Serie A">> andalso Season >= 2006 of
        true -> [T || #{team := T} <- lists:nthtail(length(Teams) - 4, Teams)];
        false -> []
    end,
    (page(standings, Teams, A))#{competition => Comp, season => Season, matches_played => length(Played),
       expected_matches => Expected, complete => Complete, leader => Leader,
       calculated_champion => case Complete of true -> Leader; false -> null end,
       calculated_relegation_places => Relegation,
       note => <<"Calculated from scores using points, wins, goal difference and goals scored. Administrative adjustments and further tie-breakers are unavailable. Serie C can include multiple stages in one table.">>}.

expected_matches(<<"Serie A">>, Y) when Y =:= 2003; Y =:= 2004 -> 552;
expected_matches(<<"Serie A">>, 2005) -> 462;
expected_matches(<<"Serie A">>, _) -> 380;
expected_matches(<<"Serie B">>, Y) when Y >= 2006 -> 380;
expected_matches(_, _) -> null.

analyze(A, Matches) ->
    Played = [M || M <- Matches, played(M)],
    Rank = case arg(rank_by, A, <<"win_rate">>) of
        <<"win_rate">> -> win_rate;
        <<"wins">> -> wins;
        <<"points">> -> points;
        <<"goals_for">> -> goals_for
    end,
    Teams = table(Played, arg(venue, A, <<"either">>), Rank, arg(min_matches, A, 1)),
    #{overall => overview(Played),
      by_season => [#{season => S, statistics => overview(Ms)} || {S, Ms} <- groups(season, Played)],
      by_competition => [#{competition => C, statistics => overview(Ms)} || {C, Ms} <- groups(competition, Played)],
      team_rankings => page(teams, Teams, A),
      biggest_wins => page(matches, [M || M = #{goal_margin := N} <- biggest(Played), N > 0], A)}.

overview(Rows) ->
    R = summarize(lists:foldl(fun(#{home_goals := H, away_goals := A}, Acc) -> tally(H,A,Acc) end,
                             {0,0,0,0,0}, Rows)),
    #{matches := N, wins := W, draws := D, losses := L, goals_for := H, goals_against := A} = R,
    #{matches => N, goals => H + A, home_goals => H, away_goals => A,
      goals_per_match => ratio(H+A,N), home_wins => W, away_wins => L, draws => D,
      home_win_rate => ratio(W,N), away_win_rate => ratio(L,N)}.

players(A, Data) ->
    Name = soccer_data:fold(arg(name, A, <<>>)),
    Club = soccer_data:team(arg(club, A, <<>>)),
    ClubMatch = arg(club_match, A, <<"exact">>),
    Nation = nationality(arg(nationality, A, <<>>)),
    Position = soccer_data:fold(arg(position, A, <<>>)),
    Rows = [P || P = #{name_key := N, club_key := C, nationality_key := Country, position := Pos}
                     <- maps:get(players, Data),
                 contains(N, Name), club_match(C, Club, ClubMatch),
                 (Nation =:= <<>> orelse Country =:= Nation),
                 position(Pos, Position)],
    Page = page(players, Rows, A),
    Hidden = [name_key, club_key, nationality_key],
    Exclude = case arg(include_attributes, A, false) of true -> Hidden; false -> [attributes | Hidden] end,
    Page#{players => [maps:without(Exclude, P) || P <- maps:get(players, Page)],
          source => <<"fifa_data.csv">>,
          average_overall => ratio(lists:sum([R || #{overall := R} <- Rows]), length(Rows))}.

contains(_, <<>>) -> true;
contains(Text, Search) -> binary:match(Text, Search) =/= nomatch.

club_match(_, <<>>, _) -> true;
club_match(Club, Query, <<"contains">>) -> contains(Club, Query);
club_match(Club, Query, <<"exact">>) -> Club =:= Query.

nationality(Value) ->
    case soccer_data:fold(Value) of
        <<"brasil">> -> <<"brazil">>;
        <<"brazilian">> -> <<"brazil">>;
        Folded -> Folded
    end.

position(_, <<>>) -> true;
position(P, <<"forward">>) -> lists:member(P, [<<"ST">>,<<"CF">>,<<"LF">>,<<"RF">>,<<"LW">>,<<"RW">>,<<"LS">>,<<"RS">>]);
position(P, <<"midfielder">>) -> lists:member(P, [<<"CAM">>,<<"CM">>,<<"CDM">>,<<"LM">>,<<"RM">>,<<"LAM">>,<<"RAM">>,<<"LCM">>,<<"RCM">>,<<"LDM">>,<<"RDM">>]);
position(P, <<"defender">>) -> lists:member(P, [<<"CB">>,<<"LCB">>,<<"RCB">>,<<"LB">>,<<"RB">>,<<"LWB">>,<<"RWB">>]);
position(P, <<"goalkeeper">>) -> P =:= <<"GK">>;
position(P, Query) -> string:lowercase(P) =:= Query.
