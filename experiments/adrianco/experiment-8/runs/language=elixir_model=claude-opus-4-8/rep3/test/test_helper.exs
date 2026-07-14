ExUnit.start()

# Ensure the database exists and migrations are applied for the test env.
Mix.Task.run("ecto.create", ["--quiet"])
Mix.Task.run("ecto.migrate", ["--quiet"])

Ecto.Adapters.SQL.Sandbox.mode(BookApi.Repo, :manual)
