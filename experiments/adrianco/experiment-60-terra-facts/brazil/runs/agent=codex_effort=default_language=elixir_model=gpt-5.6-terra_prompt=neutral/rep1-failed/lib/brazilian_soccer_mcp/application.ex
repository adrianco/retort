defmodule BrazilianSoccerMcp.Application do
  @moduledoc false
  use Application

  def start(_type, _args) do
    children = [{BrazilianSoccerMcp.Store, []}]
    Supervisor.start_link(children, strategy: :one_for_one, name: BrazilianSoccerMcp.Supervisor)
  end
end
