diesel::table! {
    books (id) {
        id -> Integer,
        title -> Text,
        author -> Text,
        year -> Integer,
        isbn -> Text,
    }
}
