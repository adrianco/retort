-module(book_api_http).
-export([start/0, stop/0]).

start() ->
    %% Start inets
    application:start(inets),
    
    %% Start the HTTP server
    case inets:start(httpd, [
        {port, 8080},
        {server_name, "book_api"},
        {document_root, "/tmp/book_api"},
        {directory_index, ["index.html"]},
        {modules, [?MODULE]}
    ]) of
        {ok, ServerId} -> 
            io:format("Server started on port 8080~n"),
            {ok, ServerId};
        {error, Reason} ->
            io:format("Failed to start server: ~p~n", [Reason]),
            {error, Reason}
    end.

stop() ->
    inets:stop(httpd).

%% Request handler for inets HTTP server
handle(_Request, _State) ->
    %% This is called for each request
    {ok, undefined}.
