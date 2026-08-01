import Config

config :book_api,
  database_path: Path.expand("../books.db", __DIR__),
  port: String.to_integer(System.get_env("PORT", "4000"))

import_config "#{config_env()}.exs"
