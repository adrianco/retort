import Config

config :book_api,
  port: 4000,
  db_path: "books.db"

if config_env() == :test do
  config :book_api,
    port: 4002,
    db_path: "books_test.db"
end
