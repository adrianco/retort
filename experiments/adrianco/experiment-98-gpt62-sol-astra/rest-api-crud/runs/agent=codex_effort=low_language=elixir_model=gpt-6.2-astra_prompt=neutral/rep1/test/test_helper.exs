ExUnit.start()

ExUnit.after_suite(fn _ ->
  Application.stop(:books)
  File.rm!(Application.fetch_env!(:books, :db_path))
end)
