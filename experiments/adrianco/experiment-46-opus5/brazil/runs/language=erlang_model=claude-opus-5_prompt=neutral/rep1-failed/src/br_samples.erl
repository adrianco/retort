%%%-------------------------------------------------------------------
%%% @doc The sample questions from the specification.
%%%
%%% They are used three ways: as an MCP resource (so a model can see
%%% what the server is good at), by `br_soccer_mcp demo', and by the
%%% `sample_questions_SUITE' acceptance test, which asserts that every
%%% one of them produces a real answer.
%%% @end
%%%-------------------------------------------------------------------
-module(br_samples).

-export([questions/0, count/0]).

-spec questions() -> [binary()].
questions() ->
    [%% Simple lookups
     <<"When did Flamengo last play Corinthians?">>,
     <<"Show me all Flamengo vs Fluminense matches">>,
     <<"What matches did Palmeiras play in 2023?">>,
     <<"Who is Gabriel Barbosa?">>,
     <<"Who is Neymar?">>,
     %% Team queries
     <<"What is Corinthians' home record in 2022?">>,
     <<"Compare Palmeiras and Santos head to head">>,
     <<"What competitions has Palmeiras played in?">>,
     <<"How did Gremio do in 2017?">>,
     <<"What is Santos' away record?">>,
     %% Competition queries
     <<"Who won the 2019 Brasileirao?">>,
     <<"Which teams were relegated in 2020?">>,
     <<"Show the standings for Serie B in 2021">>,
     <<"What are the Copa do Brasil results in 2019?">>,
     <<"Which teams played in the Libertadores in 2020?">>,
     %% Statistical analysis
     <<"What's the average goals per match in the Brasileirao?">>,
     <<"Which team has the best away record?">>,
     <<"Which team has the best home record in 2019?">>,
     <<"Which team scored the most goals in Serie A 2023?">>,
     <<"Show me the biggest wins in the dataset">>,
     <<"Compare the 2018 and 2019 seasons">>,
     %% Player queries
     <<"Find all Brazilian players in the dataset">>,
     <<"Who are the highest rated players at Gremio?">>,
     <<"Show me all forwards from Santos">>,
     <<"Which players play for Cruzeiro?">>,
     <<"Show Brazilian players by club">>,
     %% Relationship / graph queries
     <<"Show me all derbies in 2023">>,
     <<"What data sets are loaded?">>].

-spec count() -> non_neg_integer().
count() -> length(questions()).
