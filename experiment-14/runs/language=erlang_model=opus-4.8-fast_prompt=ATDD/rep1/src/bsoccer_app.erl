%%% ===================================================================
%%% Brazilian Soccer MCP Server - OTP application callback
%%%
%%% Context: Entry point for the `bsoccer' OTP application. Starting the
%%% application launches the supervision tree (`bsoccer_sup'), which in
%%% turn starts `bsoccer_data' - the worker that loads the Kaggle CSV
%%% datasets (matches and FIFA players) into ETS and answers the
%%% read-only queries that back the MCP tools.
%%%
%%% The directory holding the CSV files is taken from the application
%%% environment key `data_dir' (default "data/kaggle").
%%% ===================================================================
-module(bsoccer_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    DataDir = application:get_env(bsoccer, data_dir, "data/kaggle"),
    bsoccer_sup:start_link(DataDir).

stop(_State) ->
    ok.
