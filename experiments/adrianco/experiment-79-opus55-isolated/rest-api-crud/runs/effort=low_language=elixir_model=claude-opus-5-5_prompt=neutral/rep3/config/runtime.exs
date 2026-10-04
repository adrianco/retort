import Config

if config_env() != :test do
  if path = System.get_env("BOOKS_DB_PATH"), do: config(:book_api, db_path: path)
  if port = System.get_env("PORT"), do: config(:book_api, port: String.to_integer(port))
end
