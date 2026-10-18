defmodule BookApi.Server do
  use GenServer
  @max_body 1_000_000

  def start_link(port), do: GenServer.start_link(__MODULE__, port, name: __MODULE__)

  def init(port) do
    {:ok, socket} = :gen_tcp.listen(port, [:binary, packet: :raw, active: false, reuseaddr: true])
    acceptor = spawn_link(fn -> accept_loop(socket) end)
    {:ok, %{socket: socket, acceptor: acceptor}}
  end

  defp accept_loop(socket) do
    case :gen_tcp.accept(socket) do
      {:ok, client} ->
        spawn(fn -> serve(client) end)
        accept_loop(socket)

      {:error, :closed} ->
        :ok

      {:error, _} ->
        accept_loop(socket)
    end
  end

  defp serve(client) do
    result = with {:ok, request} <- read_request(client), do: route(request)

    case result do
      {status, body} -> send_response(client, status, body)
      _ -> send_response(client, 400, BookApi.JSON.encode(%{error: "Malformed request"}))
    end

    :gen_tcp.close(client)
  end

  defp read_request(socket), do: read_headers(socket, <<>>)

  defp read_headers(socket, data) do
    case :binary.match(data, "\r\n\r\n") do
      {index, 4} ->
        header = binary_part(data, 0, index)
        body_start = binary_part(data, index + 4, byte_size(data) - index - 4)
        [request_line | headers] = String.split(header, "\r\n")

        case String.split(request_line, " ") do
          [method, target, _version] ->
            length =
              Enum.find_value(headers, 0, fn line ->
                case String.split(line, ":", parts: 2) do
                  [key, value] ->
                    if String.downcase(key) == "content-length",
                      do: String.trim(value) |> String.to_integer()

                  _ ->
                    nil
                end
              end)

            if length > @max_body,
              do: {:error, :too_large},
              else: read_body(socket, method, target, body_start, length)

          _ ->
            {:error, :bad_request_line}
        end

      :nomatch ->
        if byte_size(data) > 16_384,
          do: {:error, :headers_too_large},
          else: receive_more(socket, data, &read_headers/2)
    end
  end

  defp read_body(_socket, method, target, body, length) when byte_size(body) >= length,
    do: {:ok, {method, target, binary_part(body, 0, length)}}

  defp read_body(socket, method, target, body, length) do
    case :gen_tcp.recv(socket, 0, 5_000) do
      {:ok, chunk} -> read_body(socket, method, target, body <> chunk, length)
      error -> error
    end
  end

  defp receive_more(socket, data, fun) do
    case :gen_tcp.recv(socket, 0, 5_000) do
      {:ok, chunk} -> fun.(socket, data <> chunk)
      error -> error
    end
  end

  defp route({method, target, body}) do
    [path | query] = String.split(target, "?", parts: 2)

    params =
      case query do
        [raw] -> URI.decode_query(raw)
        _ -> %{}
      end

    BookApi.Router.dispatch(method, path, body, params)
  end

  defp send_response(socket, status, body) do
    reason =
      %{
        200 => "OK",
        201 => "Created",
        204 => "No Content",
        400 => "Bad Request",
        404 => "Not Found",
        422 => "Unprocessable Entity"
      }[status]

    body = IO.iodata_to_binary(body)

    headers = [
      "HTTP/1.1 #{status} #{reason}\r\n",
      "content-type: application/json; charset=utf-8\r\n",
      "content-length: #{byte_size(body)}\r\n",
      "connection: close\r\n\r\n"
    ]

    :gen_tcp.send(socket, [headers, body])
  end
end
