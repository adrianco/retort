-module(book).
-export([validate/1, to_json/1, parse_json/1, validate_required/1]).

validate(Book) when is_map(Book) ->
    case validate_required(Book) of
        ok ->
            %% Validate types
            case validate_types(Book) of
                ok ->
                    {ok, Book};
                {error, Reason} ->
                    {error, Reason}
            end;
        {error, Reason} ->
            {error, Reason}
    end;
validate(_) ->
    {error, invalid_data}.

validate_required(Book) ->
    case maps:is_key(title, Book) andalso maps:is_key(author, Book) of
        true ->
            case maps:get(title, Book) of
                undefined -> {error, title_required};
                "" -> {error, title_required};
                Title when is_binary(Title) orelse is_atom(Title) ->
                    case maps:get(author, Book) of
                        undefined -> {error, author_required};
                        "" -> {error, author_required};
                        Author when is_binary(Author) orelse is_atom(Author) ->
                            ok
                    end
            end;
        false ->
            {error, missing_required_fields}
    end.

validate_types(Book) ->
    Title = maps:get(title, Book),
    Author = maps:get(author, Book),
    Year = maps:get(year, Book, null),
    ISBN = maps:get(isbn, Book, null),
    
    case is_binary(Title) andalso is_binary(Author) of
        true ->
            case Year of
                null -> ok;
                _ when is_integer(Year) -> ok;
                _ -> {error, year_must_be_integer}
            end;
        false ->
            {error, title_and_author_must_be_strings}
    end.

to_json(Book) when is_map(Book) ->
    maps:from_list([
        {<<"id">>, maps:get(id, Book, null)},
        {<<"title">>, maps:get(title, Book)},
        {<<"author">>, maps:get(author, Book)},
        {<<"year">>, maps:get(year, Book, null)},
        {<<"isbn">>, maps:get(isbn, Book, null)}
    ]).

parse_json(Json) when is_map(Json) ->
    Id = maps:get(<<"id">>, Json, null),
    Title = maps:get(<<"title">>, Json),
    Author = maps:get(<<"author">>, Json),
    Year = maps:get(<<"year">>, Json, null),
    ISBN = maps:get(<<"isbn">>, Json, null),
    
    Book = #{
        id => case Id of
            null -> undefined;
            _ -> Id
        end,
        title => Title,
        author => Author,
        year => case Year of
            null -> undefined;
            _ -> Year
        end,
        isbn => case ISBN of
            null -> undefined;
            _ -> ISBN
        end
    },
    validate(Book).
