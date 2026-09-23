-module(books_SUITE).
-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").
-compile([export_all, nowarn_export_all]).

all() -> [health, validation, crud, author_filter, not_found, validate_unit].

init_per_suite(Config) ->
    File = filename:join(?config(priv_dir, Config), "test.dets"),
    application:load(books),
    application:set_env(books, port, 18080),
    application:set_env(books, db_file, File),
    {ok, _} = application:ensure_all_started(books),
    {ok, _} = application:ensure_all_started(inets),
    Config.

end_per_suite(_) -> application:stop(books), ok.

url(P) -> "http://localhost:18080" ++ P.

req(Method, Path) -> req(Method, Path, undefined).
req(Method, Path, Body) ->
    R = case Body of
            undefined -> {url(Path), []};
            _ -> {url(Path), [], "application/json", iolist_to_binary(json:encode(Body))}
        end,
    {ok, {{_, Code, _}, _, RB}} = httpc:request(Method, R, [], [{body_format, binary}]),
    {Code, case RB of <<>> -> none; _ -> json:decode(RB) end}.

health(_) -> ?assertEqual({200, #{<<"status">> => <<"ok">>}}, req(get, "/health")).

validation(_) ->
    {400, #{<<"details">> := D}} = req(post, "/books", #{year => 2000}),
    ?assertEqual(2, length(D)),
    {400, _} = req(post, "/books", #{title => <<"T">>, author => <<"">>}),
    {400, _} = req(post, "/books", #{title => <<"T">>, author => <<"A">>, year => <<"x">>}).

crud(_) ->
    {201, #{<<"id">> := Id} = B} = req(post, "/books",
        #{title => <<"Dune">>, author => <<"Herbert">>, year => 1965, isbn => <<"123">>}),
    ?assertEqual(<<"Dune">>, maps:get(<<"title">>, B)),
    P = "/books/" ++ integer_to_list(Id),
    {200, B} = req(get, P),
    {200, #{<<"year">> := 1966}} = req(put, P, #{title => <<"Dune">>, author => <<"Herbert">>, year => 1966}),
    {400, _} = req(put, P, #{title => <<"Dune">>}),
    {204, none} = req(delete, P),
    {404, _} = req(get, P),
    {404, _} = req(delete, P).

author_filter(_) ->
    {201, _} = req(post, "/books", #{title => <<"A1">>, author => <<"Le Guin">>}),
    {201, _} = req(post, "/books", #{title => <<"B1">>, author => <<"Banks">>}),
    {200, L} = req(get, "/books?author=Le%20Guin"),
    ?assertEqual([<<"A1">>], [maps:get(<<"title">>, X) || X <- L]),
    {200, All} = req(get, "/books"),
    ?assert(length(All) >= 2).

not_found(_) ->
    {404, _} = req(get, "/books/99999"),
    {404, _} = req(get, "/books/abc"),
    {404, _} = req(put, "/books/99999", #{title => <<"x">>, author => <<"y">>}).

validate_unit(_) ->
    {ok, #{<<"title">> := <<"t">>}} = books_http:validate(#{<<"title">> => <<"t">>, <<"author">> => <<"a">>, <<"junk">> => 1}),
    {error, [_]} = books_http:validate(#{<<"title">> => <<"t">>}).
