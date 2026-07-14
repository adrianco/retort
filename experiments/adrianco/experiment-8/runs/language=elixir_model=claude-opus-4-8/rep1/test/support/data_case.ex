defmodule BookApi.DataCase do
  @moduledoc """
  Test case template that checks out a sandboxed DB connection per test and
  brings in `Plug.Test` helpers for exercising the router directly.
  """
  use ExUnit.CaseTemplate

  using do
    quote do
      import Plug.Test
      import Plug.Conn
      alias BookApi.Repo
    end
  end

  setup tags do
    pid = Ecto.Adapters.SQL.Sandbox.start_owner!(BookApi.Repo, shared: not tags[:async])
    on_exit(fn -> Ecto.Adapters.SQL.Sandbox.stop_owner(pid) end)
    :ok
  end
end
