import Config

config :books_api, server: false

config :books_api, BooksApi.Repo,
  database: "priv/repo/books_api_test.db",
  pool_size: 1

config :logger, level: :warning
