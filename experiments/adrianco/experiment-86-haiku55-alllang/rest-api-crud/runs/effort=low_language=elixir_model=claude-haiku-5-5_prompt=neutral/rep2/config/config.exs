import Config

config :books_api,
  port: String.to_integer(System.get_env("PORT", "4000")),
  database_path: System.get_env("DATABASE_PATH", "books.db")

config :logger, level: :warning

import_config "#{config_env()}.exs"
