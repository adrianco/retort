defmodule BrazilianSoccer.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      BrazilianSoccer.DataStore
    ]

    opts = [strategy: :one_for_one, name: BrazilianSoccer.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
