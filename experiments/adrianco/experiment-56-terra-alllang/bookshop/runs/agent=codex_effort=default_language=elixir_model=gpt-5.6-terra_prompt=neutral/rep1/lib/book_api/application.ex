defmodule BookApi.Application do
  @moduledoc false
  use Application

  def start(_type, _args) do
    BookApi.Store.setup()

    children = [
      {Task.Supervisor, name: BookApi.TaskSupervisor},
      BookApi.Server
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end
end
