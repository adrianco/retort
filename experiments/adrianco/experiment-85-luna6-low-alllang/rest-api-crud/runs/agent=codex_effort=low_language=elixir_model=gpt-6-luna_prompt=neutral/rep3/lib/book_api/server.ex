defmodule BookApi.Server do
  use GenServer
  require Logger

  def start_link(opts), do: GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  def init(opts) do
    :ok = BookApi.Store.init()
    port = Keyword.fetch!(opts, :port)
    {:ok, socket} = :gen_tcp.listen(port, [:binary, packet: :raw, active: false, reuseaddr: true])
    Logger.info("Book API listening on port #{port}")
    {:ok, acceptor} = Task.start_link(fn -> accept_loop(socket) end)
    {:ok, %{socket: socket, acceptor: acceptor}}
  end

  def handle(_method, _path, _query, _body) do
    {500, %{"error" => "internal server error"}}
  end

  defp accept_loop(socket) do
    case :gen_tcp.accept(socket) do
      {:ok, client} ->
        Task.start(fn -> serve(client) end)
        accept_loop(socket)
      {:error, :closed} -> :ok
      {:error, reason} -> Logger.error("Accept failed: #{inspect(reason)}")
    end
  end

  defp serve(socket) do
    {status, body} = case read_request(socket) do
      {:ok, request} -> dispatch(request)
      _ -> {400, %{"error" => "bad request"}}
    end
    json = BookApi.JSON.encode(body)
    phrase = %{200 => "OK", 201 => "Created", 204 => "No Content", 400 => "Bad Request", 404 => "Not Found", 422 => "Unprocessable Entity", 500 => "Internal Server Error"}[status]
    :gen_tcp.send(socket, ["HTTP/1.1 ", Integer.to_string(status), " ", phrase, "\r\nContent-Type: application/json\r\nContent-Length: ", Integer.to_string(byte_size(json)), "\r\nConnection: close\r\n\r\n", json])
    :gen_tcp.close(socket)
  rescue
    e -> Logger.error("Request failed: #{Exception.message(e)}"); :gen_tcp.close(socket)
  end

  defp read_request(socket) do
    with {:ok, data} <- recv_headers(socket, ""),
         [head | _] <- String.split(data, "\r\n\r\n"),
         [request_line | headers] <- String.split(head, "\r\n"),
         [method, target, _version] <- String.split(request_line, " "),
         length <- content_length(headers),
         {:ok, body} <- recv_body(socket, String.split(data, "\r\n\r\n", parts: 2) |> Enum.at(1, ""), length) do
      [path | query_parts] = String.split(target, "?", parts: 2)
      {:ok, {method, path, parse_query(List.first(query_parts)), body}}
    else
      _ -> {:error, :bad_request}
    end
  end
  defp recv_headers(socket, acc) do
    if String.contains?(acc, "\r\n\r\n") do
      {:ok, acc}
    else
      case :gen_tcp.recv(socket, 0, 5000) do
        {:ok, part} -> recv_headers(socket, acc <> part)
        other -> other
      end
    end
  end
  defp content_length(headers) do
    headers |> Enum.find_value(0, fn h -> if String.starts_with?(String.downcase(h), "content-length:"), do: h |> String.split(":", parts: 2) |> List.last() |> String.trim() |> String.to_integer() end)
  end
  defp recv_body(_socket, body, length) when byte_size(body) >= length, do: {:ok, binary_part(body, 0, length)}
  defp recv_body(socket, body, length) do
    case :gen_tcp.recv(socket, 0, 5000) do
      {:ok, part} -> recv_body(socket, body <> part, length)
      other -> other
    end
  end

  defp dispatch({method, "/health", _, _}) when method in ["GET", "HEAD"], do: {200, %{"status" => "ok"}}
  defp dispatch({"GET", "/books", query, _}), do: {200, BookApi.Store.list(query["author"])}
  defp dispatch({"POST", "/books", _, body}) do
    with {:ok, params} <- BookApi.JSON.decode(body), :ok <- validate(params) do
      {201, BookApi.Store.create(params)}
    else
      _ -> {422, %{"error" => "title and author are required"}}
    end
  end
  defp dispatch({method, "/books/" <> id, _, body}) when method in ["GET", "PUT", "DELETE"] do
    case Integer.parse(id) do
      {id, ""} when id > 0 -> book_action(method, id, body)
      _ -> {404, %{"error" => "book not found"}}
    end
  end
  defp dispatch(_), do: {404, %{"error" => "not found"}}

  defp book_action("GET", id, _) do
    case BookApi.Store.get(id) do nil -> {404, %{"error" => "book not found"}}; book -> {200, book} end
  end
  defp book_action("DELETE", id, _) do
    if BookApi.Store.delete(id), do: {204, %{}}, else: {404, %{"error" => "book not found"}}
  end
  defp book_action("PUT", id, body) do
    with {:ok, params} <- BookApi.JSON.decode(body), :ok <- validate(params) do
      case BookApi.Store.update(id, params) do nil -> {404, %{"error" => "book not found"}}; book -> {200, book} end
    else
      _ -> {422, %{"error" => "title and author are required"}}
    end
  end
  def validate(params) when is_map(params) do
    if nonempty?(params["title"]) and nonempty?(params["author"]), do: :ok, else: {:error, :validation}
  end
  def validate(_), do: {:error, :validation}
  defp nonempty?(value), do: is_binary(value) and String.trim(value) != ""
  defp parse_query(nil), do: %{}
  defp parse_query(query), do: URI.decode_query(query)
end
