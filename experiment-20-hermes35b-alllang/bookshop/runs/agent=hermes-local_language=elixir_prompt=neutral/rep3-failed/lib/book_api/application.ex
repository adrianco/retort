defmodule BookApi.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      BookApiWeb.Endpoint,
      BookApi.Repo
    ]

    opts = [strategy: :one_for_one, name: BookApi.Supervisor]
    Supervisor.start_link(children, opts)
  end

  @impl true
  def config_change(changed, _new, removed) do
    BookApiWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
