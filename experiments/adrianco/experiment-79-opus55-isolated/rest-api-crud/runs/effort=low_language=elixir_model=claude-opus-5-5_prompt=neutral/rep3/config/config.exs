import Config

config :book_api,
  db_path: "books.db",
  port: 4000,
  server: true

if config_env() == :test do
  config :book_api, db_path: ":memory:", server: false
  config :logger, level: :warning
end
