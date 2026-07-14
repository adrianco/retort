defmodule BookApi.Application do
  @moduledoc false

  use Application
  require Logger

  @impl true
  def start(_type, _args) do
    port = Application.get_env(:book_api, :port, 4000)

    children = [
      BookApi.Repo,
      {Plug.Cowboy, scheme: :http, plug: BookApi.Web.Router, options: [port: port]}
    ]

    opts = [strategy: :one_for_one, name: BookApi.Supervisor]

    with {:ok, pid} <- Supervisor.start_link(children, opts) do
      maybe_migrate()
      Logger.info("BookApi listening on http://localhost:#{port}")
      {:ok, pid}
    end
  end

  # Auto-run migrations everywhere except the test env, where the test helper
  # manages the schema against the sandbox pool.
  defp maybe_migrate do
    unless Application.get_env(:book_api, :env) == :test do
      BookApi.Release.migrate()
    end
  end
end
