import Config

config :book_api, port: 4002

config :book_api, BookApi.Repo,
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 5

config :logger, level: :warning
