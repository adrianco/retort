import Config

if config_env() != :test do
  if path = System.get_env("DATABASE_PATH"), do: config(:book_api, database: path)
  if port = System.get_env("PORT"), do: config(:book_api, port: String.to_integer(port))
end
