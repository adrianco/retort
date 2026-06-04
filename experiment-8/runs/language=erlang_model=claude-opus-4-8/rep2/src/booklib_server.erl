%%% @doc Minimal HTTP/1.1 server built on `gen_tcp'. Owns the listen socket
%%% and a small pool of acceptor processes; each accepted connection is handled
%%% by `booklib_http' in its own process.
-module(booklib_server).
-behaviour(gen_server).

-export([start_link/0, port/0]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

-define(ACCEPTORS, 5).

%%====================================================================
%% API
%%====================================================================

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

%% @doc Return the TCP port the server is actually listening on. Useful when
%% the configured port is 0 (an OS-assigned ephemeral port), e.g. in tests.
-spec port() -> inet:port_number().
port() ->
    gen_server:call(?MODULE, port).

%%====================================================================
%% gen_server callbacks
%%====================================================================

init([]) ->
    process_flag(trap_exit, true),
    Port = application:get_env(booklib, port, 8080),
    Opts = [binary, {active, false}, {reuseaddr, true}, {backlog, 128}, {packet, 0}],
    {ok, Listen} = gen_tcp:listen(Port, Opts),
    {ok, ActualPort} = inet:port(Listen),
    Acceptors = [spawn_link(fun() -> acceptor_loop(Listen) end)
                 || _ <- lists:seq(1, ?ACCEPTORS)],
    error_logger:info_msg("booklib listening on port ~p~n", [ActualPort]),
    {ok, #{listen => Listen, port => ActualPort, acceptors => Acceptors}}.

handle_call(port, _From, State = #{port := Port}) ->
    {reply, Port, State};
handle_call(_Request, _From, State) ->
    {reply, {error, unknown_request}, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

%% An acceptor died (e.g. listen socket closed during shutdown); respawn it
%% while the listen socket is still open.
handle_info({'EXIT', _Pid, _Reason}, State = #{listen := Listen}) ->
    case erlang:port_info(Listen) of
        undefined ->
            {noreply, State};
        _ ->
            _New = spawn_link(fun() -> acceptor_loop(Listen) end),
            {noreply, State}
    end;
handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, #{listen := Listen}) ->
    gen_tcp:close(Listen),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

%%====================================================================
%% Internal
%%====================================================================

acceptor_loop(Listen) ->
    case gen_tcp:accept(Listen) of
        {ok, Socket} ->
            spawn(fun() -> booklib_http:handle_connection(Socket) end),
            acceptor_loop(Listen);
        {error, closed} ->
            ok;
        {error, _Reason} ->
            acceptor_loop(Listen)
    end.
