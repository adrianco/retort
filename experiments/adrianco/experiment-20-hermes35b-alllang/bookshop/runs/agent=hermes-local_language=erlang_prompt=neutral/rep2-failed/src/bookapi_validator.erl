-module(bookapi_validator).

-export([validate_create/1, validate_update/2]).

validate_create(Data) ->
    Title = maps:get(title, Data, ""),
    case string:trim(Title) of
        "" ->
            {error, missing_field};
        _ ->
            Author = maps:get(author, Data, ""),
            case string:trim(Author) of
                "" ->
                    {error, missing_field};
                _ ->
                    {ok, #{title => Title,
                           author => Author,
                           year => maps:get(year, Data),
                           isbn => maps:get(isbn, Data)}}
            end
    end.

validate_update(_Data, NumFields) when NumFields =< 0 ->
    {error, no_fields_to_update};
validate_update(_Data, _NumFields) ->
    {ok, _Data}.
