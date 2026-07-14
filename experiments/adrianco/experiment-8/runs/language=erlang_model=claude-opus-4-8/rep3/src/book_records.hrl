-record(book, {
    id      :: integer(),
    title   :: binary(),
    author  :: binary(),
    year    :: integer() | undefined,
    isbn    :: binary() | undefined
}).

-record(counter, {
    name  :: atom(),
    value :: integer()
}).
