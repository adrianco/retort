import Config

config :books_api, ecto_repos: [BooksApi.Repo]

config :books_api, BooksApi.Repo,
  database: "priv/repo/books_api_#{config_env()}.db",
  journal_mode: :wal,
  pool_size: 5

config :books_api, port: 4000, server: true

import_config "#{config_env()}.exs"
