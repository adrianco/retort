import Config

config :book_api,
  ecto_repos: [BookApi.Repo]

config :book_api, BookApi.Repo,
  database: Path.expand("../priv/book_api_#{config_env()}.db", __DIR__),
  pool_size: 5,
  # SQLite serialises writers; wait rather than failing fast when writers
  # contend. `migration_lock: false` avoids the migrator opening a second,
  # advisory-lock connection that a single-writer database cannot grant.
  busy_timeout: 5_000,
  migration_lock: false

config :book_api, :port, 4000

config :logger, :console, format: "$time $metadata[$level] $message\n"

import_config "#{config_env()}.exs"
