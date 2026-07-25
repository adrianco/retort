defmodule BookApi.Plugs.JsonBody do
  @moduledoc """
  Parses JSON request bodies, turning parser failures into JSON error responses.

  `Plug.Parsers` signals bad input by raising, and `Plug.ErrorHandler` re-raises
  after responding so the failure still reaches the logger. For malformed client
  input that is the wrong trade-off: it is an expected 4xx, not a crash. This
  plug catches those two cases and halts with a JSON body instead.
  """

  @behaviour Plug

  import Plug.Conn

  @impl true
  def init(opts), do: Plug.Parsers.init(opts)

  @impl true
  def call(conn, opts) do
    Plug.Parsers.call(conn, opts)
  rescue
    Plug.Parsers.ParseError ->
      error(conn, 400, "Malformed JSON body")

    Plug.Parsers.UnsupportedMediaTypeError ->
      error(conn, 415, "Content-Type must be application/json")

    Plug.Parsers.RequestTooLargeError ->
      error(conn, 413, "Request body too large")
  end

  defp error(conn, status, message) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(%{error: message}))
    |> halt()
  end
end
