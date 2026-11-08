import Config

config :books,
  db_path: System.get_env("BOOKS_DB_PATH", "books.sqlite3"),
  port: String.to_integer(System.get_env("PORT", "4000")),
  server: config_env() != :test

if config_env() == :test do
  config :books, db_path: ":memory:"
end
