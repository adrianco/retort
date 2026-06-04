defmodule BookApi.DataCase do
  @moduledoc """
  Test case setup that checks out a sandboxed DB connection per test.
  """
  use ExUnit.CaseTemplate

  using do
    quote do
      alias BookApi.Repo
      import BookApi.DataCase
    end
  end

  setup tags do
    pid = Ecto.Adapters.SQL.Sandbox.start_owner!(BookApi.Repo, shared: not tags[:async])
    on_exit(fn -> Ecto.Adapters.SQL.Sandbox.stop_owner(pid) end)
    :ok
  end
end
