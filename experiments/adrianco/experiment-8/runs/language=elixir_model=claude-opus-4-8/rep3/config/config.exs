import Config

config :book_api,
  ecto_repos: [BookApi.Repo]

config :book_api, BookApi.Repo,
  database: Path.expand("../priv/book_api_#{config_env()}.db", __DIR__),
  pool_size: 5

config :book_api,
  port: 4000

import_config "#{config_env()}.exs"
