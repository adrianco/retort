import Config

config :book_collection, BookCollection.Repo,
  database: System.get_env("DATABASE_PATH") || "books_#{config_env()}.db",
  pool_size: 1

config :book_collection, :start_server, config_env() != :test
config :book_collection, :port, String.to_integer(System.get_env("PORT") || "4000")
