defmodule BrazilianSoccer.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      {BrazilianSoccer.Repo, eager: Application.get_env(:brazilian_soccer, :eager_load, false)}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: BrazilianSoccer.Supervisor)
  end
end
