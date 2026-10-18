%%% Loads the Kaggle CSV files into one in-memory dataset.
%%%
%%% Result shape:
%%%   #{matches => [match()],          % all match files, de-duplicated, date-ascending
%%%     players => [player()],         % FIFA player records
%%%     teams   => #{Key => Name},     % team key -> display name
%%%     bases   => #{Base => [Key]},   % base name -> keys sharing it
%%%     appearances => #{Key => N}}    % matches each team key appears in
%%%
%%% Team keys are base names ("palmeiras") unless several clubs share that
%%% base name in different states; then the key carries the state
%%% ("atletico-mg", "atletico-pr", "atletico-go"). See bs_text:split_team/1.
-module(bs_data).

-export([load/1]).

-type match() :: #{date := binary(), season := integer(), competition := binary(),
                   round := binary(), home := binary(), away := binary(),
                   home_name := binary(), away_name := binary(),
                   home_goals := integer(), away_goals := integer(),
                   source := binary()}.
-type player() :: #{id := integer(), name := binary(), name_key := string(),
                    age := integer(), nationality := binary(), overall := integer(),
                    potential := integer(), club := binary(), club_key := binary(),
                    value := binary(), wage := binary(), position := binary(),
                    preferred_foot := binary(), height := binary(), weight := binary(),
                    jersey := binary()}.
-export_type([match/0, player/0]).

-define(U(S), unicode:characters_to_binary(S)).

-define(MATCH_FILES, [
    {"Brasileirao_Matches.csv", fun brasileirao_row/1},
    {"novo_campeonato_brasileiro.csv", fun historical_row/1},
    {"Brazilian_Cup_Matches.csv", fun cup_row/1},
    {"Libertadores_Matches.csv", fun libertadores_row/1},
    {"BR-Football-Dataset.csv", fun br_football_row/1}
]).

-spec load(file:filename()) -> #{matches := [match()], players := [player()],
                                 teams := #{binary() => binary()},
                                 bases := #{binary() => [binary()]},
                                 appearances := #{binary() => pos_integer()}}.
load(Dir) ->
    Raw = lists:append([read_matches(filename:join(Dir, File), Fun)
                        || {File, Fun} <- ?MATCH_FILES]),
    Deduped = fill_states(dedupe(Raw)),
    Keys = team_keys(Deduped),
    Teams = team_names(Keys),
    Matches = [resolve(M, Keys, Teams) || M <- Deduped],
    Bases = maps:map(fun(_, Ks) -> lists:usort(Ks) end,
                     maps:groups_from_list(fun({{B, _}, _}) -> B end,
                                           fun({_, K}) -> K end,
                                           maps:to_list(Keys))),
    Players = [player_row(R) || R <- bs_csv:read_maps(filename:join(Dir, "fifa_data.csv"))],
    #{matches => Matches, players => Players, teams => Teams, bases => Bases,
      appearances => appearances(Matches)}.

%% Number of matches each team key appears in; used to pick the best-known
%% club when a bare name matches several.
appearances(Matches) ->
    lists:foldl(fun(M, Acc) ->
                    Acc#{maps:get(home, M) => maps:get(maps:get(home, M), Acc, 0) + 1,
                         maps:get(away, M) => maps:get(maps:get(away, M), Acc, 0) + 1}
                end, #{}, Matches).

%% --- match sources ---------------------------------------------------------

read_matches(Path, RowFun) ->
    Name = unicode:characters_to_binary(filename:basename(Path)),
    lists:filtermap(fun(Row) ->
                        case RowFun(Row) of
                            {ok, M} -> {true, M#{source => Name}};
                            skip -> false
                        end
                    end, bs_csv:read_maps(Path)).

brasileirao_row(R) ->
    build(field(<<"datetime">>, R), field(<<"season">>, R), ?U("Brasileirão Série A"),
          <<"Round ", (field(<<"round">>, R))/binary>>,
          field(<<"home_team">>, R), field(<<"away_team">>, R),
          field(<<"home_goal">>, R), field(<<"away_goal">>, R)).

historical_row(R) ->
    build(field(<<"Data">>, R), field(<<"Ano">>, R), ?U("Brasileirão Série A"),
          <<"Round ", (field(<<"Rodada">>, R))/binary>>,
          field(<<"Equipe_mandante">>, R), field(<<"Equipe_visitante">>, R),
          field(<<"Gols_mandante">>, R), field(<<"Gols_visitante">>, R)).

cup_row(R) ->
    build(field(<<"datetime">>, R), field(<<"season">>, R), <<"Copa do Brasil">>,
          <<"Round ", (field(<<"round">>, R))/binary>>,
          field(<<"home_team">>, R), field(<<"away_team">>, R),
          field(<<"home_goal">>, R), field(<<"away_goal">>, R)).

libertadores_row(R) ->
    build(field(<<"datetime">>, R), field(<<"season">>, R), <<"Copa Libertadores">>,
          field(<<"stage">>, R),
          field(<<"home_team">>, R), field(<<"away_team">>, R),
          field(<<"home_goal">>, R), field(<<"away_goal">>, R)).

%% BR-Football has ISO dates, a "tournament" column (Serie A/B/C, Copa do
%% Brasil, ...) and no season column.
br_football_row(R) ->
    Tournament = field(<<"tournament">>, R),
    build(field(<<"date">>, R), <<>>, bs_text:competition_name(Tournament, Tournament),
          <<>>,
          field(<<"home">>, R), field(<<"away">>, R),
          field(<<"home_goal">>, R), field(<<"away_goal">>, R)).

%% Produces a match with home/away as {Base, State} pairs; keys are assigned
%% later once the whole dataset is known (see team_keys/1).
build(DateBin, SeasonBin, Competition, Round, Home, Away, HomeGoal, AwayGoal) ->
    case {bs_text:parse_date(DateBin), bs_text:parse_int(HomeGoal),
          bs_text:parse_int(AwayGoal)} of
        {{ok, Date}, {ok, HG}, {ok, AG}} ->
            Season = case bs_text:parse_int(SeasonBin) of
                         {ok, S} -> S;
                         error -> binary_to_integer(binary:part(Date, 0, 4))
                     end,
            {ok, #{date => Date, season => Season, competition => Competition,
                   round => Round,
                   home => bs_text:split_team(Home),
                   away => bs_text:split_team(Away),
                   home_goals => HG, away_goals => AG}};
        _ ->
            %% Fixtures without a result or a parseable date are not usable.
            skip
    end.

%% Keeps the first occurrence of each fixture. The same match often appears
%% in several files; the copies agree on teams, score and competition, but
%% BR-Football sometimes dates a match one day later, so dates within a day
%% count as equal. Teams are compared by base name, so a fixture listed with
%% and without a state code still counts once.
dedupe(Matches) ->
    {Kept, _Seen} = lists:foldl(
        fun(M, {Acc, Seen}) ->
                {HB, _} = maps:get(home, M),
                {AB, _} = maps:get(away, M),
                Key = {HB, AB, maps:get(home_goals, M), maps:get(away_goals, M),
                       maps:get(competition, M)},
                Day = day_number(maps:get(date, M)),
                Days = maps:get(Key, Seen, []),
                case lists:any(fun(D) -> abs(D - Day) =< 1 end, Days) of
                    true -> {Acc, Seen};
                    false -> {[M | Acc], Seen#{Key => [Day | Days]}}
                end
        end, {[], #{}}, Matches),
    lists:sort(fun(A, B) -> maps:get(date, A) =< maps:get(date, B) end, lists:reverse(Kept)).

%% Day count for an ISO "YYYY-MM-DD" date, for comparing dates.
day_number(<<Y:4/binary, $-, M:2/binary, $-, D:2/binary>>) ->
    calendar:date_to_gregorian_days(binary_to_integer(Y), binary_to_integer(M),
                                    binary_to_integer(D)).

%% Maps every {Base, State} seen in the data to its team key. A base name
%% shared by several states gets state-qualified keys; otherwise the key is
%% the base name. Returns #{{Base, State} => Key}.
team_keys(Matches) ->
    Pairs = lists:append([[maps:get(home, M), maps:get(away, M)] || M <- Matches]),
    States = lists:foldl(fun({B, S}, Acc) when S =/= none ->
                                 Acc#{B => lists:usort([S | maps:get(B, Acc, [])])};
                            (_, Acc) -> Acc
                         end, #{}, Pairs),
    Ambiguous = maps:filter(fun(_, Ss) -> length(Ss) > 1 end, States),
    maps:from_list([{{B, S}, key(B, S, Ambiguous)} || {B, S} <- lists:usort(Pairs)]).

%% A name written without a state takes its base name's most common state.
fill_states(Matches) ->
    Pairs = lists:append([[maps:get(home, M), maps:get(away, M)] || M <- Matches]),
    Majority = majority_states(Pairs),
    Fill = fun({B, none}) -> {B, maps:get(B, Majority, none)};
              (Pair) -> Pair
           end,
    [M#{home := Fill(maps:get(home, M)), away := Fill(maps:get(away, M))}
     || M <- Matches].

%% #{Base => State} with the most frequent state seen for that base name.
majority_states(Pairs) ->
    Counts = lists:foldl(fun({B, S}, Acc) when S =/= none ->
                                 Acc#{{B, S} => maps:get({B, S}, Acc, 0) + 1};
                            (_, Acc) -> Acc
                         end, #{}, Pairs),
    Best = maps:fold(fun({B, S}, N, Acc) ->
                             case Acc of
                                 #{B := {_, M}} when M >= N -> Acc;
                                 _ -> Acc#{B => {S, N}}
                             end
                     end, #{}, Counts),
    maps:map(fun(_, {S, _}) -> S end, Best).

key(Base, State, Ambiguous) when State =/= none, is_map_key(Base, Ambiguous) ->
    <<Base/binary, "-", State/binary>>;
key(Base, _State, _Ambiguous) ->
    Base.

%% Display names: "Sao Paulo", or "Atletico-MG" for state-qualified keys.
team_names(Keys) ->
    maps:from_list(
      [{Key, name(Base, State, Key)} || {{Base, State}, Key} <- maps:to_list(Keys)]).

name(Base, State, Key) when State =/= none, Key =/= Base ->
    <<(bs_text:title(Base))/binary, "-", (?U(string:uppercase(binary_to_list(State))))/binary>>;
name(Base, _State, _Key) ->
    bs_text:title(Base).

%% Replaces the {Base, State} pairs in a match with team keys and adds names.
resolve(M, Keys, Teams) ->
    Home = maps:get(maps:get(home, M), Keys),
    Away = maps:get(maps:get(away, M), Keys),
    M#{home := Home, away := Away,
       home_name => maps:get(Home, Teams), away_name => maps:get(Away, Teams)}.

%% --- player source ---------------------------------------------------------

player_row(R) ->
    Name = field(<<"Name">>, R),
    Club = field(<<"Club">>, R),
    #{id => int(field(<<"ID">>, R)),
      name => Name,
      name_key => bs_text:fold(Name),
      age => int(field(<<"Age">>, R)),
      nationality => field(<<"Nationality">>, R),
      overall => int(field(<<"Overall">>, R)),
      potential => int(field(<<"Potential">>, R)),
      club => Club,
      club_key => bs_text:normalize_team(Club),
      value => field(<<"Value">>, R),
      wage => field(<<"Wage">>, R),
      position => field(<<"Position">>, R),
      preferred_foot => field(<<"Preferred Foot">>, R),
      height => field(<<"Height">>, R),
      weight => field(<<"Weight">>, R),
      jersey => field(<<"Jersey Number">>, R)}.

%% --- helpers ---------------------------------------------------------------

field(Name, Row) -> maps:get(Name, Row, <<>>).

int(Bin) ->
    case bs_text:parse_int(Bin) of
        {ok, N} -> N;
        error -> 0
    end.
