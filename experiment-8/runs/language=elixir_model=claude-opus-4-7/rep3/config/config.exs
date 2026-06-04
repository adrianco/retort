import Config

config :book_api,
  ecto_repos: [BookApi.Repo]

config :book_api, BookApi.Repo,
  database: Path.expand("../book_api_#{config_env()}.db", __DIR__),
  pool_size: 5,
  show_sensitive_data_on_connection_error: true

config :book_api,
  port: String.to_integer(System.get_env("PORT") || "4000")

config :logger, level: :info

import_config "#{config_env()}.exs"
