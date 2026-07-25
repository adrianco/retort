defmodule BookApi.ApiCase do
  @moduledoc """
  Test case template for exercising `BookApi.Router` end to end.

  Each test runs inside a database sandbox transaction, and gets helpers for
  issuing JSON requests and decoding JSON responses.
  """

  use ExUnit.CaseTemplate

  using do
    quote do
      import Plug.Conn
      import Plug.Test
      import BookApi.ApiCase

      alias BookApi.Books
      alias BookApi.Repo
    end
  end

  setup tags do
    pid = Ecto.Adapters.SQL.Sandbox.start_owner!(BookApi.Repo, shared: not tags[:async])
    on_exit(fn -> Ecto.Adapters.SQL.Sandbox.stop_owner(pid) end)
    :ok
  end

  @doc "Issues a request against the router; `body` is encoded as JSON when given."
  def request(method, path, body \\ nil) do
    conn =
      case body do
        nil ->
          Plug.Test.conn(method, path)

        raw when is_binary(raw) ->
          method
          |> Plug.Test.conn(path, raw)
          |> Plug.Conn.put_req_header("content-type", "application/json")

        map ->
          method
          |> Plug.Test.conn(path, Jason.encode!(map))
          |> Plug.Conn.put_req_header("content-type", "application/json")
      end

    BookApi.Router.call(conn, BookApi.Router.init([]))
  end

  @doc "Decodes a response body as JSON."
  def json_body(conn), do: Jason.decode!(conn.resp_body)

  @doc "Inserts a book directly, bypassing HTTP. Raises on invalid attributes."
  def insert_book(attrs \\ %{}) do
    defaults = %{"title" => "A Title", "author" => "An Author", "year" => 2000}

    {:ok, book} = BookApi.Books.create_book(Map.merge(defaults, Map.new(attrs)))
    book
  end
end
