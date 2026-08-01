defmodule BookApi.Server do
  @moduledoc false
  use GenServer
  require Logger

  def start_link(_), do: GenServer.start_link(__MODULE__, [], name: __MODULE__)
  def init(_) do
    port = Application.get_env(:book_api, :port, 4000)
    {:ok, socket} = :gen_tcp.listen(port, [:binary, active: false, reuseaddr: true, packet: :raw])
    {:ok, actual_port} = :inet.port(socket)
    if actual_port != 0, do: Logger.info("Book API listening on http://localhost:#{actual_port}")
    Task.Supervisor.start_child(BookApi.TaskSupervisor, fn -> accept(socket) end)
    {:ok, socket}
  end

  defp accept(listener) do
    {:ok, socket} = :gen_tcp.accept(listener)
    Task.Supervisor.start_child(BookApi.TaskSupervisor, fn -> serve(socket) end)
    accept(listener)
  end
  defp serve(socket) do
    case read_request(socket) do
      {:ok, method, target, body} ->
        {path, query} = split_target(target)
        {status, response} = BookApi.Router.route(method, path, query, body)
        send_response(socket, status, response)
      _ -> send_response(socket, 400, %{error: "bad request"})
    end
    :gen_tcp.close(socket)
  end
  defp read_request(socket) do
    with {:ok, data} <- :gen_tcp.recv(socket, 0),
         [headers, initial_body] <- :binary.split(data, "\r\n\r\n"),
         [request | header_lines] <- String.split(headers, "\r\n"),
         [method, target, _version] <- String.split(request, " ") do
      length = header_lines |> Enum.find_value(0, fn line ->
        case String.split(line, ":", parts: 2) do
          [key, value] -> if String.downcase(key) == "content-length", do: String.to_integer(String.trim(value))
          _ -> nil
        end
      end)
      remaining = length - byte_size(initial_body)
      extra = if remaining > 0, do: elem(:gen_tcp.recv(socket, remaining), 1), else: ""
      {:ok, method, target, initial_body <> extra}
    else
      _ -> :error
    end
  end
  defp split_target(target) do
    case String.split(target, "?", parts: 2) do
      [path] -> {path, %{}}
      [path, query] -> {path, URI.decode_query(query)}
    end
  end
  defp send_response(socket, status, nil), do: :gen_tcp.send(socket, "HTTP/1.1 #{status} #{reason(status)}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
  defp send_response(socket, status, payload) do
    body = BookApi.JSON.encode(payload)
    :gen_tcp.send(socket, "HTTP/1.1 #{status} #{reason(status)}\r\nContent-Type: application/json\r\nContent-Length: #{byte_size(body)}\r\nConnection: close\r\n\r\n#{body}")
  end
  defp reason(200), do: "OK"
  defp reason(201), do: "Created"
  defp reason(204), do: "No Content"
  defp reason(400), do: "Bad Request"
  defp reason(404), do: "Not Found"
  defp reason(422), do: "Unprocessable Content"
end
