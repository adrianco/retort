import Config
config :books, db_path: System.get_env("BOOKS_DB", "books.db"), port: String.to_integer(System.get_env("PORT", "4000")), server: true
import_config "#{config_env()}.exs"
