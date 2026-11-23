-module(books).
-export([start/2, stop/1, run/0, do/1]).
-include_lib("inets/include/httpd.hrl").

run() ->
    {ok, _} = start(list_to_integer(os:getenv("PORT", "8080")),
                    os:getenv("BOOKS_DB", "books.dets")),
    receive stop -> ok end.

start(Port, File) ->
    {ok, _} = application:ensure_all_started(inets),
    case dets:open_file(books_db, [{file, File}, {type, set}]) of
        {ok, books_db} ->
            case inets:start(httpd, [{port, Port}, {bind_address, "127.0.0.1"},
                    {server_name, "books"}, {server_root, "."}, {document_root, "."},
                    {max_body_size, 1048576}, {modules, [?MODULE]}]) of
                {ok, _} = Service -> Service;
                Error -> dets:close(books_db), Error
            end;
        Error -> Error
    end.

stop(Pid) ->
    inets:stop(httpd, Pid),
    dets:close(books_db).

do(#mod{request_uri = URI, method = Method, entity_body = Body, data = Data}) ->
    {Status, Value, Extra} = try
        Parsed = uri_string:parse(list_to_binary(URI)),
        route(Method, maps:get(path, Parsed), maps:get(query, Parsed, <<>>), Body)
    catch
        throw:{invalid, Message} -> {400, #{error => Message}, []};
        Class:Reason ->
            logger:error("Book request failed: ~p ~p", [Class, Reason]),
            {500, #{error => <<"Internal server error">>}, []}
    end,
    Json = iolist_to_binary(json:encode(Value)),
    Headers = [{code, Status}, {content_type, "application/json"},
               {content_length, integer_to_list(byte_size(Json))} | Extra],
    {proceed, [{response, {response, Headers, Json}} | Data]}.

route("GET", <<"/health">>, _, _) -> {200, #{status => <<"ok">>}, []};
route("GET", <<"/books">>, Query, _) ->
    Params = uri_string:dissect_query(Query),
    is_list(Params) orelse invalid(<<"Invalid query">>),
    Author = proplists:get_value(<<"author">>, Params),
    Books = dets:foldl(fun({_, Book}, Acc) ->
        case Author =:= undefined orelse Author =:= maps:get(<<"author">>, Book) of
            true -> [Book | Acc];
            false -> Acc
        end
    end, [], books_db),
    {200, Books, []};
route("POST", <<"/books">>, _, Body) ->
    Fields = fields(Body),
    Id = binary:encode_hex(crypto:strong_rand_bytes(16), lowercase),
    Book = Fields#{<<"id">> => Id},
    true = dets:insert_new(books_db, {Id, Book}),
    ok = dets:sync(books_db),
    {201, Book, [{location, "/books/" ++ binary_to_list(Id)}]};
route(Method, <<"/books/", Id/binary>>, _, Body) when byte_size(Id) > 0 ->
    case binary:match(Id, <<"/">>) of
        nomatch -> global:trans({{books_db, Id}, self()},
                                fun() -> item(Method, Id, Body) end, [node()]);
        _ -> missing()
    end;
route(_, <<"/books">>, _, _) -> method_error("GET, POST");
route(_, <<"/health">>, _, _) -> method_error("GET");
route(_, _, _, _) -> missing().

item("GET", Id, _) ->
    case dets:lookup(books_db, Id) of
        [{Id, Book}] -> {200, Book, []};
        [] -> missing()
    end;
item("PUT", Id, Body) ->
    Book = (fields(Body))#{<<"id">> => Id},
    case dets:member(books_db, Id) of
        true -> ok = dets:insert(books_db, {Id, Book}),
                ok = dets:sync(books_db), {200, Book, []};
        false -> missing()
    end;
item("DELETE", Id, _) ->
    case dets:select_delete(books_db, [{{Id, '_'}, [], [true]}]) of
        1 -> ok = dets:sync(books_db), {200, #{deleted => Id}, []};
        0 -> missing()
    end;
item(_, _, _) -> method_error("GET, PUT, DELETE").

missing() -> {404, #{error => <<"Not found">>}, []}.
method_error(Allow) -> {405, #{error => <<"Method not allowed">>}, [{allow, Allow}]}.
invalid(Message) -> throw({invalid, Message}).

fields(Body) ->
    Map = try json:decode(iolist_to_binary(Body))
          catch error:_ -> invalid(<<"Invalid JSON">>) end,
    is_map(Map) orelse invalid(<<"Expected a JSON object">>),
    lists:foreach(fun(Key) ->
        Value = maps:get(Key, Map, undefined),
        (is_binary(Value) andalso string:trim(Value) =/= <<>>)
            orelse invalid(<<Key/binary, " must be a nonblank string">>)
    end, [<<"title">>, <<"author">>]),
    is_integer(maps:get(<<"year">>, Map, 0)) orelse invalid(<<"year must be an integer">>),
    is_binary(maps:get(<<"isbn">>, Map, <<>>)) orelse invalid(<<"isbn must be a string">>),
    maps:with([<<"title">>, <<"author">>, <<"year">>, <<"isbn">>], Map).
