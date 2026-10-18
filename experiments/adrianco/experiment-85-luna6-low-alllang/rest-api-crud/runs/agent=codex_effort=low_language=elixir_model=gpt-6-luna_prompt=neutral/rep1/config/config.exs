import Config

config :book_api,
  database: System.get_env("BOOKS_DB", "books.db"),
  port: String.to_integer(System.get_env("PORT", "4000"))
