-module(book_api_http).
-export([start/0, stop/0]).

start() ->
    %% Start inets
    application:start(inets),
    
    %% Create the document root directory if it doesn't exist
    file:make_dir("/tmp/book_api"),
    
    %% Start the HTTP server
    case inets:start(httpd, [
        {port, 8080},
        {server_name, "book_api"},
        {server_root, "/tmp/book_api"},
        {document_root, "/tmp/book_api"},
        {directory_index, ["index.html"]},
        {modules, [?MODULE]}
    ]) of
        {ok, ServerId} -> 
            io:format("Server started on port 8080~n", []),
            {ok, ServerId};
        {error, Reason} ->
            io:format("Failed to start server: ~p~n", [Reason]),
            {error, Reason}
    end.

stop() ->
    inets:stop(httpd).
