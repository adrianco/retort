%%%-------------------------------------------------------------------
%%% @doc The MCP tool catalogue.
%%%
%%% Each entry couples a JSON Schema (what an LLM may send) with the
%%% {@link br_query} function that answers it and the {@link br_format}
%%% renderer that turns the result into prose.  `tools/call' therefore
%%% returns both `structuredContent' (the raw map) and a text block.
%%% @end
%%%-------------------------------------------------------------------
-module(br_mcp_tools).

-export([list/0,
         definitions/0,
         names/0,
         find/1,
         invoke/2,
         render/2]).

%%--------------------------------------------------------------------
%% @doc Tool descriptors as sent in a `tools/list' response.
-spec list() -> [map()].
list() ->
    [#{name => Name,
       title => Title,
       description => Description,
       inputSchema => Schema}
     || #{name := Name, title := Title, description := Description,
          schema := Schema} <- definitions()].

-spec names() -> [binary()].
names() -> [maps:get(name, D) || D <- definitions()].

-spec find(binary()) -> {ok, map()} | error.
find(Name) ->
    case [D || D <- definitions(), maps:get(name, D) =:= Name] of
        [D | _] -> {ok, D};
        [] -> error
    end.

%%--------------------------------------------------------------------
%% @doc Run a tool by name.
-spec invoke(binary(), map()) -> {ok, map()} | {error, map()}.
invoke(Name, Args) when is_map(Args) ->
    case find(Name) of
        error ->
            {error, #{code => unknown_tool,
                      message => <<"unknown tool: ", Name/binary>>,
                      suggestions => names()}};
        {ok, #{handler := Handler}} ->
            try Handler(Args)
            catch
                Class:Reason:Stack ->
                    logger:error("tool ~s failed: ~p:~p~n~p", [Name, Class, Reason, Stack]),
                    {error, #{code => tool_failed,
                              message => iolist_to_binary(
                                           io_lib:format("~s failed: ~p", [Name, Reason])),
                              suggestions => []}}
            end
    end;
invoke(Name, _Args) ->
    invoke(Name, #{}).

%%--------------------------------------------------------------------
%% @doc Render a tool result as text.
-spec render(binary(), map()) -> binary().
render(Name, Result) ->
    case find(Name) of
        {ok, #{renderer := Renderer}} -> Renderer(Result);
        error -> br_format:render(Name, Result)
    end.

%%====================================================================
%% Catalogue
%%====================================================================

-spec definitions() -> [map()].
definitions() ->
    [tool(<<"ask">>, <<"Ask a question">>,
          <<"Answer a natural language question about Brazilian soccer. Routes the "
            "question to the most appropriate query and returns a written answer. "
            "Use this when you do not want to pick a specific tool yourself.">>,
          object(#{question => string(<<"Question, e.g. \"Who won the 2019 Brasileirao?\"">>)},
                 [question]),
          fun(Args) -> ask(Args) end,
          fun(R) -> maps:get(answer, R, <<>>) end),

     tool(<<"search_matches">>, <<"Search matches">>,
          <<"Find matches by team, opponent, competition, season or date range. "
            "Team names are matched loosely: \"Flamengo\", \"Flamengo-RJ\" and "
            "\"CR Flamengo\" all work.">>,
          object(#{team => string(<<"Team that played in the match (home or away)">>),
                   opponent => string(<<"Opponent of `team`">>),
                   home_team => string(<<"Team playing at home">>),
                   away_team => string(<<"Team playing away">>),
                   competition => competition_schema(),
                   season => integer(<<"Season year, e.g. 2019">>),
                   season_from => integer(<<"Earliest season">>),
                   season_to => integer(<<"Latest season">>),
                   date_from => string(<<"Earliest date, YYYY-MM-DD">>),
                   date_to => string(<<"Latest date, YYYY-MM-DD">>),
                   sort => enum(<<"Sort order">>,
                                [<<"date_desc">>, <<"date_asc">>, <<"goals_desc">>]),
                   limit => integer(<<"Maximum matches to return (default 20)">>)},
                 []),
          fun br_query:find_matches/1,
          fun(R) -> br_format:render(find_matches, R) end),

     tool(<<"head_to_head">>, <<"Head to head">>,
          <<"Complete head-to-head record between two teams: wins, draws, goals and "
            "the matches themselves. Recognises the traditional derbies.">>,
          object(#{team_a => string(<<"First team">>),
                   team_b => string(<<"Second team">>),
                   competition => competition_schema(),
                   season => integer(<<"Restrict to one season">>),
                   limit => integer(<<"Maximum matches to list (default 20)">>)},
                 [team_a, team_b]),
          fun br_query:head_to_head/1,
          fun(R) -> br_format:render(head_to_head, R) end),

     tool(<<"team_stats">>, <<"Team statistics">>,
          <<"Wins, draws, losses, goals, points and win rate for a team, optionally "
            "for one season, one competition or only home/away matches.">>,
          object(#{team => string(<<"Team name">>),
                   season => integer(<<"Season year">>),
                   competition => competition_schema(),
                   venue => enum(<<"Which matches to count">>,
                                 [<<"any">>, <<"home">>, <<"away">>])},
                 [team]),
          fun br_query:team_stats/1,
          fun(R) -> br_format:render(team_stats, R) end),

     tool(<<"team_profile">>, <<"Team profile">>,
          <<"Everything the knowledge graph holds about a club: record per "
            "competition and per season, derbies, and its FIFA squad if the club is "
            "present in the player data.">>,
          object(#{team => string(<<"Team name">>)}, [team]),
          fun br_query:team_profile/1,
          fun(R) -> br_format:render(team_profile, R) end),

     tool(<<"standings">>, <<"League standings">>,
          <<"League table for a season, calculated from the match results "
            "(3 points for a win). Marks the champion and the relegated teams when "
            "the season is complete.">>,
          object(#{competition => competition_schema(),
                   season => integer(<<"Season year, e.g. 2019">>),
                   limit => integer(<<"Maximum rows">>)},
                 [season]),
          fun br_query:standings/1,
          fun(R) -> br_format:render(standings, R) end),

     tool(<<"team_rankings">>, <<"Rank teams">>,
          <<"Rank teams by points, wins, win rate, goals scored or goals conceded, "
            "optionally counting only home or only away matches. Answers questions "
            "like \"which team has the best away record?\".">>,
          object(#{competition => competition_schema(),
                   season => integer(<<"Season year">>),
                   venue => enum(<<"Which matches to count">>,
                                 [<<"any">>, <<"home">>, <<"away">>]),
                   metric => enum(<<"Ranking metric">>,
                                  [<<"points">>, <<"wins">>, <<"win_rate">>,
                                   <<"goals_for">>, <<"goals_against">>,
                                   <<"goal_difference">>, <<"points_per_game">>]),
                   min_matches => integer(<<"Ignore teams with fewer matches">>),
                   limit => integer(<<"How many teams (default 10)">>)},
                 []),
          fun br_query:team_rankings/1,
          fun(R) -> br_format:render(team_rankings, R) end),

     tool(<<"competition_stats">>, <<"Competition statistics">>,
          <<"Aggregate statistics for a competition and optionally one season: "
            "goals per match, home/draw/away rates, biggest win, top scoring teams.">>,
          object(#{competition => competition_schema(),
                   season => integer(<<"Season year">>)},
                 []),
          fun br_query:competition_stats/1,
          fun(R) -> br_format:render(competition_stats, R) end),

     tool(<<"compare_seasons">>, <<"Compare seasons">>,
          <<"Compare two seasons of the same competition side by side.">>,
          object(#{competition => competition_schema(),
                   season_a => integer(<<"First season">>),
                   season_b => integer(<<"Second season">>)},
                 [season_a, season_b]),
          fun br_query:compare_seasons/1,
          fun(R) -> br_format:render(compare_seasons, R) end),

     tool(<<"biggest_wins">>, <<"Biggest wins">>,
          <<"Matches with the largest winning margin, optionally filtered by "
            "competition, season or team.">>,
          object(#{competition => competition_schema(),
                   season => integer(<<"Season year">>),
                   team => string(<<"Restrict to one team">>),
                   limit => integer(<<"How many matches (default 20)">>)},
                 []),
          fun br_query:biggest_wins/1,
          fun(R) -> br_format:render(biggest_wins, R) end),

     tool(<<"search_players">>, <<"Search players">>,
          <<"Search the FIFA player data by name, nationality, club, position or "
            "rating. Position accepts FIFA codes (ST, CB, GK) or words "
            "(forward, midfielder, defender, goalkeeper).">>,
          object(#{name => string(<<"Part of the player name">>),
                   nationality => string(<<"Nationality, e.g. Brazil">>),
                   club => string(<<"Club name">>),
                   position => string(<<"Position code or word">>),
                   min_overall => integer(<<"Minimum FIFA overall rating">>),
                   min_age => integer(<<"Minimum age">>),
                   max_age => integer(<<"Maximum age">>),
                   sort => enum(<<"Sort order">>,
                                [<<"overall_desc">>, <<"potential_desc">>,
                                 <<"age_asc">>, <<"age_desc">>, <<"name">>]),
                   limit => integer(<<"How many players (default 20)">>)},
                 []),
          fun br_query:search_players/1,
          fun(R) -> br_format:render(search_players, R) end),

     tool(<<"player_profile">>, <<"Player profile">>,
          <<"Full profile of one player: ratings, attributes, club, and whether "
            "that club appears in the match data sets.">>,
          object(#{name => string(<<"Player name, e.g. \"Neymar\"">>),
                   player_id => integer(<<"FIFA player id">>)},
                 []),
          fun br_query:player_profile/1,
          fun(R) -> br_format:render(player_profile, R) end),

     tool(<<"club_squad">>, <<"Club squad">>,
          <<"Players registered at a club in the FIFA data, best rated first. "
            "Note that FIFA 19 did not license every Brazilian club, so some clubs "
            "have match data but no squad.">>,
          object(#{club => string(<<"Club name">>),
                   limit => integer(<<"How many players (default 40)">>)},
                 [club]),
          fun br_query:club_squad/1,
          fun(R) -> br_format:render(club_squad, R) end),

     tool(<<"players_by_club">>, <<"Players grouped by club">>,
          <<"Group players by club with counts and average rating - e.g. Brazilian "
            "players at each club.">>,
          object(#{nationality => string(<<"Restrict to one nationality">>),
                   only_clubs_in_match_data =>
                       boolean(<<"Only clubs that also appear in the match data">>),
                   limit => integer(<<"How many clubs (default 25)">>)},
                 []),
          fun br_query:player_club_summary/1,
          fun(R) -> br_format:render(player_club_summary, R) end),

     tool(<<"derbies">>, <<"Derbies">>,
          <<"The traditional derbies (Fla-Flu, Derby Paulista, Gre-Nal, ...) and "
            "the matches between those rivals, optionally in one season.">>,
          object(#{season => integer(<<"Season year">>),
                   competition => competition_schema()},
                 []),
          fun br_query:derbies/1,
          fun(R) -> br_format:render(derbies, R) end),

     tool(<<"list_teams">>, <<"List teams">>,
          <<"List the teams in the knowledge graph, optionally filtered by "
            "competition, season, Brazilian state or a search string.">>,
          object(#{query => string(<<"Search string">>),
                   competition => competition_schema(),
                   season => integer(<<"Season year">>),
                   state => string(<<"Brazilian state code, e.g. SP">>),
                   limit => integer(<<"How many teams (default 50)">>)},
                 []),
          fun br_query:list_teams/1,
          fun(R) -> br_format:render(list_teams, R) end),

     tool(<<"list_competitions">>, <<"List competitions">>,
          <<"The competitions in the data with their season coverage.">>,
          object(#{}, []),
          fun br_query:list_competitions/1,
          fun(R) -> br_format:render(list_competitions, R) end),

     tool(<<"dataset_summary">>, <<"Data set summary">>,
          <<"What is loaded: files, match/team/player counts, graph size.">>,
          object(#{}, []),
          fun br_query:dataset_summary/1,
          fun(R) -> br_format:render(dataset_summary, R) end),

     tool(<<"graph_neighbors">>, <<"Graph neighbours">>,
          <<"Explore the knowledge graph: the neighbours of a node. Node ids look "
            "like \"team:flamengo\", \"player:158023\", \"competition:libertadores\", "
            "\"season:2019\". Relations: home_team, away_team, in_competition, "
            "in_season, at_venue, played_in, plays_for, nationality, based_in.">>,
          object(#{node => string(<<"Node id, e.g. \"team:santos\"">>),
                   type => string(<<"Node type when resolving by name">>),
                   name => string(<<"Node name when resolving by type+name">>),
                   relation => string(<<"Only follow this relation">>),
                   limit => integer(<<"How many neighbours (default 50)">>)},
                 []),
          fun br_query:graph_neighbors/1,
          fun(R) -> br_format:render(graph_neighbors, R) end),

     tool(<<"graph_path">>, <<"Graph path">>,
          <<"Shortest path between two nodes of the knowledge graph, e.g. from a "
            "player to a competition via his club.">>,
          object(#{from => string(<<"Start node id">>),
                   to => string(<<"End node id">>),
                   max_depth => integer(<<"Maximum hops (default 6)">>)},
                 [from, to]),
          fun br_query:graph_path/1,
          fun(R) -> br_format:render(graph_path, R) end)].

%%====================================================================
%% Internal
%%====================================================================

ask(Args) ->
    case br_query:opt(question, Args, undefined) of
        undefined ->
            {error, #{code => missing_argument, message => <<"question is required">>,
                      suggestions => []}};
        Question ->
            case br_nl:answer(Question) of
                {ok, Answer} -> {ok, Answer};
                {error, E} ->
                    Message = br_format:error_text(E),
                    {ok, #{question => br_text:to_binary(Question),
                           tool => maps:get(tool, E, <<"none">>),
                           arguments => maps:get(arguments, E, #{}),
                           interpretation => <<"failed">>,
                           answer => <<"I could not answer that: ", Message/binary>>,
                           data => #{}}}
            end
    end.

tool(Name, Title, Description, Schema, Handler, Renderer) ->
    #{name => Name,
      title => Title,
      description => Description,
      schema => Schema,
      handler => Handler,
      renderer => Renderer}.

object(Properties, Required) ->
    #{type => <<"object">>,
      properties => Properties,
      required => [atom_to_binary(R, utf8) || R <- Required],
      additionalProperties => false}.

string(Description) -> #{type => <<"string">>, description => Description}.

integer(Description) -> #{type => <<"integer">>, description => Description}.

boolean(Description) -> #{type => <<"boolean">>, description => Description}.

enum(Description, Values) ->
    #{type => <<"string">>, description => Description, enum => Values}.

competition_schema() ->
    #{type => <<"string">>,
      description => <<"Competition: brasileirao_serie_a, brasileirao_serie_b, "
                       "brasileirao_serie_c, copa_do_brasil or libertadores "
                       "(common names such as \"Brasileirao\" or \"Serie A\" work too)">>}.
