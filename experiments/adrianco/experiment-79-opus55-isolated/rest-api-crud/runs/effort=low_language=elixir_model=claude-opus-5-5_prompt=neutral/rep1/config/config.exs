import Config

config :book_api,
  database: "books.db",
  port: 4000,
  server: true

if config_env() == :test do
  # In-memory database and no HTTP listener: tests call the router directly.
  config :book_api, database: ":memory:", server: false
  config :logger, level: :warning
end
