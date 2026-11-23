import Config

if config_env() == :test do
  config :books,
         :db_path,
         Path.join(System.tmp_dir!(), "books-#{System.pid()}-#{System.system_time()}.dets")
else
  config :books, :db_path, System.get_env("BOOKS_DB", "books.dets")
end
