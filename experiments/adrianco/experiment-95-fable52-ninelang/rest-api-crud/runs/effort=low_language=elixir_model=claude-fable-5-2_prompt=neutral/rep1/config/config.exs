import Config

config :book_api,
  database: System.get_env("DATABASE_PATH", "books.db"),
  port: String.to_integer(System.get_env("PORT", "4000")),
  server: true

if config_env() == :test do
  config :book_api, database: ":memory:", server: false
  config :logger, level: :warning
end
