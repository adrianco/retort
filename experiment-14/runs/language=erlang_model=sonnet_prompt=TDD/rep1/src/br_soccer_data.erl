-module(br_soccer_data).
-export([load_brasileirao/1, load_copa_brasil/1, load_libertadores/1,
         load_br_football/1, load_historical/1, load_players/1,
         load_all/1, all_matches/1]).

load_csv(Path) ->
    {ok, Bin} = file:read_file(Path),
    %% Strip UTF-8 BOM if present
    Data = case Bin of
        <<16#EF, 16#BB, 16#BF, Rest/binary>> -> Rest;
        Other -> Other
    end,
    br_soccer_csv:parse_string(Data).

load_brasileirao(Dir) ->
    load_csv(filename:join(Dir, "Brasileirao_Matches.csv")).

load_copa_brasil(Dir) ->
    load_csv(filename:join(Dir, "Brazilian_Cup_Matches.csv")).

load_libertadores(Dir) ->
    load_csv(filename:join(Dir, "Libertadores_Matches.csv")).

load_br_football(Dir) ->
    load_csv(filename:join(Dir, "BR-Football-Dataset.csv")).

load_historical(Dir) ->
    load_csv(filename:join(Dir, "novo_campeonato_brasileiro.csv")).

load_players(Dir) ->
    load_csv(filename:join(Dir, "fifa_data.csv")).

load_all(Dir) ->
    #{
        brasileirao  => load_brasileirao(Dir),
        copa_brasil  => load_copa_brasil(Dir),
        libertadores => load_libertadores(Dir),
        br_football  => load_br_football(Dir),
        historical   => load_historical(Dir),
        players      => load_players(Dir)
    }.

%% Return a unified match list with a `competition` key added.
all_matches(All) ->
    Tag = fun(Comp, Rows) -> [M#{competition => Comp} || M <- Rows] end,
    lists:concat([
        Tag(brasileirao,  maps:get(brasileirao, All, [])),
        Tag(copa_brasil,  maps:get(copa_brasil, All, [])),
        Tag(libertadores, maps:get(libertadores, All, [])),
        Tag(br_football,  maps:get(br_football, All, [])),
        Tag(historical,   maps:get(historical, All, []))
    ]).
