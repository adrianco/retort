defmodule BookApiWeb.ConnCase do
  @moduledoc """
  This module defines the test case to be used by
  tests that require setting up a connection.

  Such tests rely on `Phoenix.ConnTest` and other
  tooling, such as changing in the config file,
  to solve the problem.
  """

  use ExUnit.CaseTemplate

  using do
    quote do
      # Import conveniences for testing with connections
      use Phoenix.ConnTest
      alias BookApiWeb.Router.Helpers, as: routes

      # The default endpoint for testing
      @endpoint BookApiWeb.Endpoint
    end
  end

  setup tags do
    :ok = Ecto.Adapters.SQL.Sandbox.checkout(BookApi.Repo)

    unless tags[:async] do
      Ecto.Adapters.SQL.Sandbox.mode(BookApi.Repo, :manual)
    end

    {:ok, conn: Phoenix.ConnTest.build_conn()}
  end
end
