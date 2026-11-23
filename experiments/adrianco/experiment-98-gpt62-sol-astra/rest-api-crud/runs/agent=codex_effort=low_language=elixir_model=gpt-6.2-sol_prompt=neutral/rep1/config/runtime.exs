import Config

if config_env() != :test do
  config :book_collection,
    database: System.get_env("BOOK_DB_PATH", "book_collection.sqlite3"),
    port: String.to_integer(System.get_env("PORT", "4000"))
end
