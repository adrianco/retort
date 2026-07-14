defmodule BrazilianSoccer.Test.MCPClient do
  @moduledoc """
  A test-only client that exercises the System Under Test exclusively through
  the public MCP (JSON-RPC 2.0) protocol boundary — the same boundary a real
  MCP host/LLM would use. There is no back-door access to internal modules:
  every request is encoded as a JSON-RPC message string, handed to the server's
  public `handle_json/1` entry point, and the JSON response is decoded.
  """

  alias BrazilianSoccer.MCP.Server

  @doc "Send a raw JSON-RPC request map and return the decoded response map."
  def request(req) do
    req
    |> Jason.encode!()
    |> Server.handle_json()
    |> Jason.decode!()
  end

  @doc "Perform the MCP initialize handshake."
  def initialize do
    request(%{
      "jsonrpc" => "2.0",
      "id" => next_id(),
      "method" => "initialize",
      "params" => %{
        "protocolVersion" => "2024-11-05",
        "capabilities" => %{},
        "clientInfo" => %{"name" => "acceptance-test", "version" => "1.0"}
      }
    })
  end

  @doc "List the tools the server advertises."
  def list_tools do
    resp =
      request(%{
        "jsonrpc" => "2.0",
        "id" => next_id(),
        "method" => "tools/list",
        "params" => %{}
      })

    get_in(resp, ["result", "tools"])
  end

  @doc """
  Call a tool by name with the given arguments and return its full decoded
  JSON-RPC response (including result/error).
  """
  def call_raw(name, arguments \\ %{}) do
    request(%{
      "jsonrpc" => "2.0",
      "id" => next_id(),
      "method" => "tools/call",
      "params" => %{"name" => name, "arguments" => arguments}
    })
  end

  @doc """
  Call a tool and return its `structuredContent` payload (the machine-readable
  answer), raising if the tool reported an error.
  """
  def call(name, arguments \\ %{}) do
    resp = call_raw(name, arguments)

    case resp do
      %{"result" => %{"isError" => true} = result} ->
        raise "tool #{name} returned error: #{inspect(result)}"

      %{"result" => %{"structuredContent" => structured}} ->
        structured

      %{"error" => error} ->
        raise "JSON-RPC error for #{name}: #{inspect(error)}"
    end
  end

  @doc "Call a tool and return the human-readable text content block."
  def call_text(name, arguments \\ %{}) do
    resp = call_raw(name, arguments)
    get_in(resp, ["result", "content"]) |> hd() |> Map.get("text")
  end

  defp next_id, do: System.unique_integer([:positive])
end
