defmodule BookApi.Application do
  @moduledoc false

  use Application
  require Logger

  @impl true
  def start(_type, _args) do
    ensure_storage!()

    children = [BookApi.Repo] ++ server_children()

    opts = [strategy: :one_for_one, name: BookApi.Supervisor]
    Supervisor.start_link(children, opts)
  end

  # SQLite is embedded, so the app can create its own database file rather than
  # requiring a separate provisioning step. Doing it here, over a single
  # connection, also settles the journal mode before the pool opens: several
  # connections initialising a brand-new file at once contend for the exclusive
  # lock that `PRAGMA journal_mode=WAL` needs.
  defp ensure_storage! do
    config = BookApi.Repo.config()

    # Any other return raises a CaseClauseError, failing the boot loudly rather
    # than leaving the app running against a database it could not create.
    case BookApi.Repo.__adapter__().storage_up(config) do
      :ok -> Logger.info("Created database at #{config[:database]}")
      {:error, :already_up} -> :ok
    end
  end

  defp server_children do
    if Application.get_env(:book_api, :start_server, true) do
      port = port()
      Logger.info("Starting BookApi on port #{port}")
      [{Bandit, plug: BookApi.Router, scheme: :http, port: port}]
    else
      []
    end
  end

  defp port do
    case System.get_env("PORT") do
      nil -> Application.get_env(:book_api, :port, 4000)
      value -> String.to_integer(value)
    end
  end
end
