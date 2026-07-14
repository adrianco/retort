import Config

config :book_api,
  ecto_repos: [BookApi.Repo],
  port: 4000

config :book_api, BookApi.Repo,
  database: Path.expand("../book_api_#{config_env()}.db", __DIR__),
  pool_size: 5,
  show_sensitive_data_on_connection_error: true

import_config "#{config_env()}.exs"
