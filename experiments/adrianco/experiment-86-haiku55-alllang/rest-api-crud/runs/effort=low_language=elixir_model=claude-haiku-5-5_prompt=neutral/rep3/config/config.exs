import Config

config :book_api, ecto_repos: [BookApi.Repo]

config :book_api, BookApi.Repo,
  database: Path.expand("../book_api_#{config_env()}.db", __DIR__),
  pool_size: 5

config :book_api, :http_port, 4000
config :book_api, :start_server, true

import_config "#{config_env()}.exs"
