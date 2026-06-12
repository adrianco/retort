defmodule BrSoccer.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      BrSoccer.Repo
    ]

    opts = [strategy: :one_for_one, name: BrSoccer.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
