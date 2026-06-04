defmodule BookApi.DataCase do
  @moduledoc """
  Test case template that sets up the Ecto sandbox.
  """

  use ExUnit.CaseTemplate

  using do
    quote do
      import Plug.Test
      import Plug.Conn
    end
  end

  setup tags do
    pid = Ecto.Adapters.SQL.Sandbox.start_owner!(BookApi.Repo, shared: not tags[:async])
    on_exit(fn -> Ecto.Adapters.SQL.Sandbox.stop_owner(pid) end)
    :ok
  end
end
