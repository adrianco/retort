-module(book_api).

-export([start/2, stop/1, run/0, do/1]).

-include_lib("inets/include/httpd.hrl").

start(Port, Database) ->
    {ok, _} = application:ensure_all_started(inets),
    case book_store:start_link(Database) of
        {ok, _} ->
            {ok, Root} = file:get_cwd(),
            Config = [{port, Port}, {server_name, "book-api"},
                      {server_root, Root}, {document_root, Root},
                      {modules, [?MODULE]}, {max_body_size, 1048576}],
            case inets:start(httpd, Config) of
                {ok, _} = Started -> Started;
                {error, _} = Error ->
                    book_store:stop(),
                    Error
            end;
        {error, _} = Error -> Error
    end.

stop(Server) ->
    ok = inets:stop(httpd, Server),
    book_store:stop().

run() ->
    Port = list_to_integer(os:getenv("PORT", "8080")),
    Database = os:getenv("BOOKS_DB", "books.dets"),
    {ok, Server} = start(Port, Database),
    io:format("Book API listening on port ~B~n", [proplists:get_value(port, httpd:info(Server))]),
    receive
        stop -> stop(Server)
    end.

do(#mod{method = Method, request_uri = Uri, entity_body = Body, data = Data}) ->
    {Status, ExtraHeaders, Payload} =
        try dispatch(Method, Uri, Body)
        catch
            Class:Reason:Stack ->
                logger:error("Book API request failed: ~p:~p ~p", [Class, Reason, Stack]),
                error_response(500, <<"Internal server error">>)
        end,
    {Headers, Encoded} = case Status of
        204 -> {ExtraHeaders, <<>>};
        _ -> {[{content_type, "application/json"} | ExtraHeaders],
              iolist_to_binary(json:encode(Payload))}
    end,
    Response = {response, [{code, Status}, {content_length, integer_to_list(byte_size(Encoded))}
                           | Headers], Encoded},
    {proceed, [{response, Response} | Data]}.

dispatch(Method, Uri, Body) ->
    case string:split(Uri, "?") of
        [Path] -> route(Method, Path, "", Body);
        [Path, Query] -> route(Method, Path, Query, Body)
    end.

route("GET", "/health", _Query, _Body) ->
    ok = book_store:request(health),
    response(200, #{<<"status">> => <<"ok">>});
route(_, "/health", _Query, _Body) ->
    method_not_allowed("GET");
route("GET", "/books", Query, _Body) ->
    case author_filter(Query) of
        {ok, Author} -> book_result(200, book_store:request({list, Author}));
        error -> error_response(400, <<"Invalid query string">>)
    end;
route("POST", "/books", _Query, Body) ->
    with_book(Body, fun(Fields) ->
        {ok, #{<<"id">> := Id} = Book} = book_store:request({create, Fields}),
        {201, [{"location", "/books/" ++ integer_to_list(Id)}], Book}
    end);
route(_, "/books", _Query, _Body) ->
    method_not_allowed("GET, POST");
route(Method, "/books/" ++ IdText, _Query, Body) ->
    case string:to_integer(IdText) of
        {Id, []} when Id > 0 -> book_route(Method, Id, Body);
        _ -> error_response(404, <<"Book not found">>)
    end;
route(_, _, _, _) ->
    error_response(404, <<"Route not found">>).

book_route("GET", Id, _Body) ->
    book_result(200, book_store:request({get, Id}));
book_route("PUT", Id, Body) ->
    with_book(Body, fun(Fields) ->
        book_result(200, book_store:request({update, Id, Fields}))
    end);
book_route("DELETE", Id, _Body) ->
    case book_store:request({delete, Id}) of
        ok -> response(204, null);
        not_found -> error_response(404, <<"Book not found">>)
    end;
book_route(_, _, _) ->
    method_not_allowed("GET, PUT, DELETE").

author_filter(Query) ->
    case uri_string:dissect_query(list_to_binary(Query)) of
        Pairs when is_list(Pairs) ->
            case proplists:get_value(<<"author">>, Pairs, all) of
                Author when is_binary(Author); Author =:= all -> {ok, Author};
                _ -> error
            end;
        _ -> error
    end.

with_book(Body, Action) ->
    case decode(Body) of
        {ok, Book} when is_map(Book) ->
            Title = maps:get(<<"title">>, Book, null),
            Author = maps:get(<<"author">>, Book, null),
            Year = maps:get(<<"year">>, Book, null),
            Isbn = maps:get(<<"isbn">>, Book, null),
            case nonblank(Title) andalso nonblank(Author) of
                false -> error_response(400, <<"Title and author must be nonblank strings">>);
                true when (is_integer(Year) orelse Year =:= null),
                          (is_binary(Isbn) orelse Isbn =:= null) ->
                    Action(#{<<"title">> => Title, <<"author">> => Author,
                             <<"year">> => Year, <<"isbn">> => Isbn});
                true -> error_response(400, <<"Year must be an integer and ISBN a string">>)
            end;
        _ -> error_response(400, <<"Expected a JSON object">>)
    end.

decode(Body) ->
    try {ok, json:decode(iolist_to_binary(Body))}
    catch error:_ -> error
    end.

nonblank(Value) ->
    is_binary(Value) andalso string:trim(Value) =/= <<>>.

book_result(Status, {ok, Payload}) -> response(Status, Payload);
book_result(_, not_found) -> error_response(404, <<"Book not found">>).

response(Status, Payload) -> {Status, [], Payload}.

error_response(Status, Message) -> response(Status, #{<<"error">> => Message}).

method_not_allowed(Methods) ->
    {405, [{"allow", Methods}], #{<<"error">> => <<"Method not allowed">>}}.
