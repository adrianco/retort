import Config

config :books, Books.Repo,
  database: System.get_env("DATABASE_PATH", "books.db"),
  pool_size: 1

config :books, :port, String.to_integer(System.get_env("PORT", "4000"))
config :books, :start_server, config_env() != :test

import_config "#{config_env()}.exs"
