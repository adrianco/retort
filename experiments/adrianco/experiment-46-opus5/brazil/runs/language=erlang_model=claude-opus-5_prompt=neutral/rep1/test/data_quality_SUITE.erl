%%%-------------------------------------------------------------------
%%% @doc Feature: Data Quality.
%%%
%%% Context: the specification calls out three hazards - team name
%%% variations, three date formats and UTF-8 Portuguese text - and this
%%% suite pins each one down, plus the two hazards the data itself
%%% revealed: names that denote *different* clubs in different states
%%% (Botafogo RJ/SP/PB) and heavy overlap between the source files.
%%% The parsing units (CSV, text, names) are checked here as well, since
%%% they are what make the guarantees above hold.
%%% @end
%%%-------------------------------------------------------------------
-module(data_quality_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2,
                    call_tool/2, call_tool_error/2]).

all() ->
    [csv_parser_handles_the_awkward_cases,
     numbers_and_missing_values,
     three_date_formats,
     accent_folding_and_normalisation,
     state_suffixes_are_understood,
     team_name_variations_resolve_to_one_club,
     ambiguous_names_are_kept_apart,
     sources_are_merged_not_duplicated,
     unknown_scores_are_excluded_from_statistics,
     utf8_survives_the_round_trip].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("Data Quality"),
    Config.

%%--------------------------------------------------------------------

csv_parser_handles_the_awkward_cases(_Config) ->
    scenario("The CSV reader copes with quotes, commas, BOM and short rows"),
    Table = when_("I parse a CSV with every awkward construct", fun() ->
        Csv = <<239, 187, 191,  % UTF-8 BOM
                "a,b,c\r\n"
                "1,\"two, with comma\",3\r\n"
                "\"quoted \"\"inner\"\" quotes\",x,y\n"
                "short,row\n"
                "\n"
                "sao,\"S", 195, 163, "o Paulo\",z\n"/utf8>>,
        bsmcp_csv:parse(Csv)
    end),
    then("the header is read without the byte order mark", fun() ->
        bsmcp_csv:headers(Table) =:= [<<"a">>, <<"b">>, <<"c">>]
    end),
    Rows = bsmcp_csv:rows(Table),
    and_("blank lines are skipped", fun() -> length(Rows) =:= 4 end),
    and_("a quoted field keeps its comma", fun() ->
        bsmcp_csv:field(lists:nth(1, Rows), Table, <<"b">>) =:= <<"two, with comma">>
    end),
    and_("doubled quotes are unescaped", fun() ->
        bsmcp_csv:field(lists:nth(2, Rows), Table, <<"a">>)
            =:= <<"quoted \"inner\" quotes">>
    end),
    and_("a short row is padded instead of shifting columns", fun() ->
        bsmcp_csv:field(lists:nth(3, Rows), Table, <<"c">>) =:= <<>>
    end),
    and_("UTF-8 sequences are never split", fun() ->
        bsmcp_csv:field(lists:nth(4, Rows), Table, <<"b">>) =:= <<"São Paulo"/utf8>>
    end),
    and_("an unknown column reads as empty rather than crashing", fun() ->
        bsmcp_csv:field(lists:nth(1, Rows), Table, <<"nope">>) =:= <<>>
    end).

numbers_and_missing_values(_Config) ->
    scenario("The three ways the sources write a missing number all decode to undefined"),
    then("NA, a dash and an empty cell are undefined", fun() ->
        [undefined, undefined, undefined, undefined]
            =:= [bsmcp_text:to_int(<<"NA">>), bsmcp_text:to_int(<<"-">>),
                 bsmcp_text:to_int(<<>>), bsmcp_text:to_int(<<"n/a">>)]
    end),
    and_("integers and float spellings both decode", fun() ->
        [3, 3, -2, 3] =:= [bsmcp_text:to_int(<<"3">>), bsmcp_text:to_int(<<"3.0">>),
                           bsmcp_text:to_int(<<"-2">>), bsmcp_text:to_int(<<" 3 ">>)]
    end),
    and_("floats keep their fraction", fun() ->
        bsmcp_text:to_number(<<"2.75">>) =:= 2.75
    end).

three_date_formats(_Config) ->
    scenario("ISO, ISO with time and Brazilian dates are all understood"),
    then("all three formats give the same date", fun() ->
        [{2023, 9, 24}, {2012, 5, 19}, {2003, 3, 29}]
            =:= [bsmcp_text:parse_date(<<"2023-09-24">>),
                 bsmcp_text:parse_date(<<"2012-05-19 18:30:00">>),
                 bsmcp_text:parse_date(<<"29/03/2003">>)]
    end),
    and_("a kick-off time is extracted when present", fun() ->
        bsmcp_text:parse_time(<<"2012-05-19 18:30:00">>) =:= <<"18:30">>
    end),
    and_("impossible dates are rejected", fun() ->
        bsmcp_text:parse_date(<<"2019-02-31">>) =:= undefined
            andalso bsmcp_text:parse_date(<<"rubbish">>) =:= undefined
    end),
    and_("dates from every source appear in the graph", fun() ->
        {Old, _} = call_tool(<<"search_matches">>, #{<<"season">> => 2003,
                                                     <<"limit">> => 1}),
        [#{date := D}] = maps:get(matches, Old),
        binary:match(D, <<"2003">>) =/= nomatch
    end).

accent_folding_and_normalisation(_Config) ->
    scenario("Portuguese text is folded to a stable search key"),
    then("accents are removed for matching", fun() ->
        [<<"Sao Paulo">>, <<"Gremio">>, <<"Avai">>, <<"Nautico">>]
            =:= [bsmcp_text:fold_accents(<<"São Paulo"/utf8>>),
                 bsmcp_text:fold_accents(<<"Grêmio"/utf8>>),
                 bsmcp_text:fold_accents(<<"Avaí"/utf8>>),
                 bsmcp_text:fold_accents(<<"Náutico"/utf8>>)]
    end),
    and_("normalisation lowercases and drops punctuation", fun() ->
        bsmcp_text:normalize(<<"Atlético - MG"/utf8>>) =:= <<"atletico mg">>
    end),
    and_("initials are joined so A.B.C. equals ABC", fun() ->
        bsmcp_text:normalize(<<"A.b.c. - RN">>) =:= <<"abc rn">>
    end),
    and_("Portuguese stop words are ignored", fun() ->
        bsmcp_text:normalize(<<"Xv de Piracicaba">>) =:= <<"xv piracicaba">>
    end).

state_suffixes_are_understood(_Config) ->
    scenario("Every way of writing a state suffix is peeled off"),
    then("dashes, spaces and parentheses all work", fun() ->
        [{<<"Palmeiras">>, <<"SP">>}, {<<"América"/utf8>>, <<"MG">>},
         {<<"Botafogo">>, <<"RJ">>}, {<<"Nacional">>, <<"URU">>},
         {<<"América FC"/utf8>>, <<"MG">>}]
            =:= [bsmcp_names:split_state(<<"Palmeiras-SP">>),
                 bsmcp_names:split_state(<<"América - MG"/utf8>>),
                 bsmcp_names:split_state(<<"Botafogo RJ">>),
                 bsmcp_names:split_state(<<"Nacional (URU)">>),
                 bsmcp_names:split_state(<<"América FC (Minas Gerais)"/utf8>>)]
    end),
    and_("a trailing word that only looks like a state is left alone", fun() ->
        bsmcp_names:split_state(<<"EC Bahia">>) =:= {<<"EC Bahia">>, undefined}
    end),
    and_("legal form words do not change the identity", fun() ->
        bsmcp_names:key(<<"Esporte Clube Bahia">>) =:= <<"bahia">>
            andalso bsmcp_names:key(<<"CSA">>) =:= <<"csa">>
    end).

team_name_variations_resolve_to_one_club(_Config) ->
    scenario("The same club written five ways resolves to one club"),
    Variants = [<<"Atletico-MG">>, <<"Atlético - MG"/utf8>>, <<"Atlético Mineiro"/utf8>>,
                <<"Atletico Mineiro">>, <<"Clube Atlético Mineiro"/utf8>>],
    Ids = when_("I resolve every spelling of Atletico Mineiro", fun() ->
        [maps:get(id, bsmcp_data:resolve_team(V)) || V <- Variants]
    end),
    then("they all point at the same club", fun() ->
        length(lists:usort(Ids)) =:= 1
    end),
    and_("the club keeps its accented display name", fun() ->
        maps:get(name, bsmcp_data:resolve_team(<<"Atletico-MG">>))
            =:= <<"Atlético Mineiro"/utf8>>
    end),
    and_("the spellings found in the files are reported", fun() ->
        {Result, _} = call_tool(<<"list_teams">>, #{<<"query">> => <<"Atletico Mineiro">>}),
        [Team | _] = maps:get(teams, Result),
        length(maps:get(name_variants, Team)) >= 3
    end),
    and_("Athletico Paranaense stays a different club", fun() ->
        maps:get(id, bsmcp_data:resolve_team(<<"Athletico-PR">>))
            =/= maps:get(id, bsmcp_data:resolve_team(<<"Atletico-MG">>))
    end),
    and_("São Paulo resolves however it is spelt", fun() ->
        Ids2 = [maps:get(id, bsmcp_data:resolve_team(V))
                || V <- [<<"Sao Paulo">>, <<"São Paulo"/utf8>>, <<"Sao Paulo-SP">>,
                         <<"São Paulo Futebol Clube"/utf8>>]],
        length(lists:usort(Ids2)) =:= 1
    end).

ambiguous_names_are_kept_apart(_Config) ->
    scenario("Clubs that share a name in different states stay separate"),
    {Result, Text} = when_("I list the clubs called Botafogo", fun() ->
        call_tool(<<"list_teams">>, #{<<"query">> => <<"Botafogo">>})
    end),
    Teams = maps:get(teams, Result),
    then("three different Botafogos are known", fun() ->
        length(Teams) >= 3
    end),
    and_("they are distinguished by state", fun() ->
        States = lists:sort([maps:get(state, T) || T <- Teams]),
        States =:= lists:usort(States)
    end),
    and_("the plain name resolves to the club with the most matches", fun() ->
        maps:get(id, bsmcp_data:resolve_team(<<"Botafogo">>)) =:= <<"botafogo|RJ">>
    end),
    and_("a state qualifier picks the other clubs", fun() ->
        maps:get(id, bsmcp_data:resolve_team(<<"Botafogo-SP">>)) =:= <<"botafogo|SP">>
            andalso maps:get(id, bsmcp_data:resolve_team(<<"Botafogo - PB">>))
                    =:= <<"botafogo|PB">>
    end),
    and_("the answer shows the spellings that were merged", fun() ->
        binary:match(Text, <<"spellings in the data">>) =/= nomatch
    end).

sources_are_merged_not_duplicated(_Config) ->
    scenario("Overlapping source files are merged into one fixture each"),
    given("the 2019 Serie A appears in three of the source files", fun() -> ok end),
    Ids = when_("I take the 2019 Serie A fixtures out of the graph", fun() ->
        bsmcp_data:competition_match_ids(serie_a, 2019)
    end),
    Matches = [bsmcp_data:match(Id) || Id <- Ids],
    then("there are exactly 380 fixtures, not 1140", fun() ->
        length(Matches) =:= 380
    end),
    and_("no pairing appears twice", fun() ->
        Pairs = [{maps:get(home_team, M), maps:get(away_team, M)} || M <- Matches],
        length(lists:usort(Pairs)) =:= 380
    end),
    and_("every club played 38 matches", fun() ->
        Counts = lists:foldl(fun(#{home_team := H, away_team := A}, Acc) ->
                                     maps:update_with(H, fun(N) -> N + 1 end, 1,
                                       maps:update_with(A, fun(N) -> N + 1 end, 1, Acc))
                             end, #{}, Matches),
        map_size(Counts) =:= 20
            andalso lists:all(fun(N) -> N =:= 38 end, maps:values(Counts))
    end),
    and_("merged fixtures record which files they came from", fun() ->
        Multi = [M || M <- Matches, length(maps:get(sources, M)) > 1],
        length(Multi) > 300
    end),
    and_("the merge fills in details only one file carries", fun() ->
        WithVenue = [M || M <- Matches, maps:get(venue, M) =/= undefined],
        WithStats = [M || M <- Matches, map_size(maps:get(stats, M, #{})) > 0],
        WithRound = [M || M <- Matches, maps:get(round, M) =/= undefined],
        length(WithVenue) > 300 andalso length(WithStats) > 300
            andalso length(WithRound) > 300
    end).

unknown_scores_are_excluded_from_statistics(_Config) ->
    scenario("Fixtures with an NA score are kept but never counted"),
    Unplayed = when_("I look for fixtures with no recorded score", fun() ->
        bsmcp_data:fold_matches(fun(M, Acc) ->
                                        case maps:get(played, M) of
                                            false -> [M | Acc];
                                            true -> Acc
                                        end
                                end, [])
    end),
    then("such fixtures exist in the sources", fun() -> length(Unplayed) > 0 end),
    and_("they carry no result", fun() ->
        lists:all(fun(#{result := R}) -> R =:= undefined end, Unplayed)
    end),
    and_("statistics only count played matches", fun() ->
        {Stats, _} = call_tool(<<"competition_stats">>, #{}),
        Played = bsmcp_data:fold_matches(fun(M, N) ->
                                                case maps:get(played, M) of
                                                    true -> N + 1;
                                                    false -> N
                                                end
                                        end, 0),
        maps:get(matches, maps:get(overall, Stats)) =:= Played
    end),
    and_("a search can ask for played fixtures only", fun() ->
        {R, _} = call_tool(<<"search_matches">>, #{<<"played_only">> => true,
                                                   <<"limit">> => 50}),
        lists:all(fun(M) -> maps:get(played, M) =:= true end, maps:get(matches, R))
    end).

utf8_survives_the_round_trip(_Config) ->
    scenario("Portuguese club names survive JSON encoding"),
    {Result, Text} = when_("I fetch a club whose name has accents", fun() ->
        call_tool(<<"team_profile">>, #{<<"team">> => <<"Gremio">>})
    end),
    then("the display name keeps its circumflex", fun() ->
        maps:get(name, maps:get(team, Result)) =:= <<"Grêmio"/utf8>>
    end),
    Json = and_("I encode the result as JSON", fun() -> bsmcp_json:encode(Result) end),
    then("the JSON is valid UTF-8", fun() ->
        is_binary(unicode:characters_to_binary(Json, utf8, utf8))
    end),
    and_("decoding gives the accented name back", fun() ->
        {ok, Decoded} = bsmcp_json:decode(Json),
        maps:get(<<"name">>, maps:get(<<"team">>, Decoded)) =:= <<"Grêmio"/utf8>>
    end),
    and_("the rendered text is UTF-8 too", fun() ->
        binary:match(Text, <<"Grêmio"/utf8>>) =/= nomatch
    end).
