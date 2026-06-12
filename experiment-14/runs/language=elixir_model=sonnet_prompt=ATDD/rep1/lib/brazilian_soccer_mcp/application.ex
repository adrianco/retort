defmodule BrazilianSoccerMcp.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      BrazilianSoccerMcp.DataStore
    ]

    opts = [strategy: :one_for_one, name: BrazilianSoccerMcp.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
