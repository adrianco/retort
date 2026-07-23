%% -*- erlang -*-
%% This file is part of Book API.
%%
%% Book API is free software: you can redistribute it and/or modify
%% it under the terms of the GNU Lesser General Public License as published by
%% the Free Software Foundation, either version 3 of the License, or
%% (at your option) any later version.
%%
%% Book API is distributed in the hope that it will be useful,
%% but WITHOUT ANY WARRANTY; without even the implied warranty of
%% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
%% GNU Lesser General Public License for more details.
%%
%% You should have received a copy of the GNU Lesser General Public License
%% along with Book API. If not, see <http://www.gnu.org/licenses/>.

-module(book_api_routes).

-behaviour(cowboy_http_handler).

-export([start_link/0, init/2, handle/2, terminate/3]).

-include("book_api_db.hrl").

-define(PORT, 8080).

start_link() ->
    {ok, _} = cowboy:start_clear(http, [{port, ?PORT}], #{
        env => #{dispatch => get_routes()}
    }),
    {ok, self()}.

get_routes() ->
    cowboy_router:compile([
        %% Health check
        {'_', [
            {"/health", ?MODULE, []},
            %% Books endpoints
            {"/books", ?MODULE, []},
            {"/books/:id", ?MODULE, []}
        ]}
    ]).

init(_Transport, _Req) ->
    {ok, #{}}.

handle(Req, State) ->
    #{method := Method, path := Path} = Req,
    PathParts = string:tokens(Path, "/"),
    {Result, Req2} = handle_request(Method, PathParts, Req),
    {ok, Req3} = cowboy_req:set_resp_body(
        cowboy_req:set_resp_header(<<"content-type">>, <<"application/json">>, Req2),
        Result
    ),
    {ok, Req3, State}.

handle_request(<<"GET">>, ["health"], Req) ->
    case book_api_db:health_check() of
        ok -> {json_map(#{status => <<"ok">>}), Req};
        Error -> {json_map(#{status => Error}), Req}
    end;

handle_request(<<"POST">>, ["books"], Req) ->
    {ok, Body, Req2} = cowboy_req:body(Req),
    case parse_json(Body) of
        {ok, Params} ->
            case validate_book_params(Params) of
                ok ->
                    case book_api_db:create_book(Params) of
                        {ok, Book} -> {json_map(#{ok => true, data => book_to_map(Book)}), Req2};
                        {error, duplicate_isbn} -> {json_map(#{error => <<"duplicate_isbn">>}), Req2}
                    end;
                {error, ValidationErrors} ->
                    {json_map(#{error => ValidationErrors}), Req2}
            end;
        {error, parse_error} ->
            {json_map(#{error => <<"invalid_json">>}), Req2}
    end;

handle_request(<<"GET">>, ["books"], Req) ->
    QueryParams = cowboy_req:query_params(Req),
    case book_api_db:get_books(QueryParams) of
        {ok, Books} -> {json_map(#{ok => true, data => [book_to_map(B) || B <- Books]}), Req};
        {error, Reason} -> {json_map(#{error => Reason}), Req}
    end;

handle_request(<<"GET">>, ["books", IdStr], Req) ->
    Id = parse_id(IdStr),
    case book_api_db:get_book(Id) of
        {ok, Book} -> {json_map(#{ok => true, data => book_to_map(Book)}), Req};
        {error, not_found} -> {json_map(#{error => <<"not_found">>}), Req};
        {error, Reason} -> {json_map(#{error => Reason}), Req}
    end;

handle_request(<<"PUT">>, ["books", IdStr], Req) ->
    Id = parse_id(IdStr),
    {ok, Body, Req2} = cowboy_req:body(Req),
    case parse_json(Body) of
        {ok, Params} ->
            case book_api_db:update_book(Id, Params) of
                {ok, Book} -> {json_map(#{ok => true, data => book_to_map(Book)}), Req2};
                {error, not_found} -> {json_map(#{error => <<"not_found">>}), Req2};
                {error, Reason} -> {json_map(#{error => Reason}), Req2}
            end;
        {error, parse_error} ->
            {json_map(#{error => <<"invalid_json">>}), Req2}
    end;

handle_request(<<"DELETE">>, ["books", IdStr], Req) ->
    Id = parse_id(IdStr),
    case book_api_db:delete_book(Id) of
        ok -> {json_map(#{ok => true}), Req};
        {error, not_found} -> {json_map(#{error => <<"not_found">>}), Req};
        {error, Reason} -> {json_map(#{error => Reason}), Req}
    end;

handle_request(_Method, _PathParts, Req) ->
    {json_map(#{error => <<"not_found">>}), Req}.

%% Helper functions

parse_id(IdStr) when is_binary(IdStr) ->
    case string:to_integer(binary_to_list(IdStr)) of
        {Id, _} when is_integer(Id) -> Id;
        _ -> undefined
    end;
parse_id(Id) when is_integer(Id) ->
    Id.

validate_book_params(Params) ->
    Title = maps:get(title, Params, undefined),
    Author = maps:get(author, Params, undefined),
    case {Title, Author} of
        {undefined, undefined} -> {error, [<<"title is required">>, <<"author is required">>]};
        {undefined, _} -> {error, [<<"title is required">>]};
        {_, undefined} -> {error, [<<"author is required">>]};
        {_, _} -> ok
    end.

book_to_map(Book) ->
    #book{id=Id, title=Title, author=Author, year=Year, isbn=Isbn} = Book,
    #{id => Id, title => Title, author => Author, year => Year, isbn => Isbn}.

json_map(Map) ->
    jsx:encode(Map).

parse_json(Body) ->
    try
        {ok, jsx:decode(Body, [{return_maps, true}])}
    catch
        _:_ -> {error, parse_error}
    end.

terminate(_Reason, _Req, _State) ->
    ok.
