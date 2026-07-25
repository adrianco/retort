defmodule BookApi.DataCase do
  @moduledoc """
  This module defines the setup for tests requiring
  access to the application's data layer.

  You may define functions here to be used as helpers in
  your tests.

  Finally, if the test case interacts with the database,
  we enable the SQL sandbox, so changes done to the database
  are reverted at the end of every test. If you are using
  PostgreSQL, you can even run database tests asynchronously
  by setting `use BookApi.DataCase, async: true`, although
  this option is not recommended for other databases.
  """

  use ExUnit.CaseTemplate

  using do
    quote do
      alias BookApi.Repo

      import Ecto
      import Ecto.Changeset
      import Ecto.Query
      import BookApi.DataCase
    end
  end

  setup tags do
    :ok = Ecto.Adapters.SQL.Sandbox.checkout(BookApi.Repo)

    unless tags[:async] do
      Ecto.Adapters.SQL.Sandbox.mode(BookApi.Repo, :manual)
    end

    :ok
  end

  @doc """
  A helper that transforms changeset errors into a map of messages.

      assert {:error, changeset} = Book.create_book(%{field: "invalid value"})
      assert "can't be blank" in errors_on(changeset, :field)

  """
  def errors_on(changeset, field) do
    Ecto.Changeset.traverse_errors(changeset, fn {message, opts} ->
      Regex.replace(~r"%{(\w+)}", message, fn _key, word ->
        opts
        |> Keyword.get(String.to_atom(word), word)
        |> to_string()
      end)
    end)
    |> Map.new()
  end
end
