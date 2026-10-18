import Config

config :book_api,
  database_path: "data/book_api.db",
  start_server: true,
  port: String.to_integer(System.get_env("PORT", "4000"))

if config_env() == :test do
  config :book_api,
    database_path: "data/book_api_test.db",
    start_server: false
end
