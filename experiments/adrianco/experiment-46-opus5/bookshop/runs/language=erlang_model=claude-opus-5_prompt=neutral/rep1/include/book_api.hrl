-ifndef(BOOK_API_HRL).
-define(BOOK_API_HRL, true).

%% Persisted shape of a book. `id' is the Mnesia key.
-record(book, {id         :: pos_integer() | '_',
               title      :: binary() | '_',
               author     :: binary() | '_',
               year       :: integer() | null | '_',
               isbn       :: binary() | null | '_',
               created_at :: integer() | '_',   %% erlang system time, seconds
               updated_at :: integer() | '_'}). %% erlang system time, seconds

-endif.
