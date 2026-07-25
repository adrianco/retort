defmodule BrazilianSoccer.CLI do
  @moduledoc """
  Escript entry point.

      brazilian_soccer_mcp                      # run the MCP server on stdio
      brazilian_soccer_mcp --demo               # answer the sample questions
      brazilian_soccer_mcp --tool NAME --args '{"team":"Flamengo"}'
      brazilian_soccer_mcp --list-tools
  """

  alias BrazilianSoccer.{Repo, SampleQuestions}
  alias BrazilianSoccer.MCP.{Stdio, Tools}

  @doc false
  def main(argv) do
    {opts, rest, _} =
      OptionParser.parse(argv,
        strict: [demo: :boolean, tool: :string, args: :string, list_tools: :boolean, help: :boolean]
      )

    ensure_started()

    cond do
      opts[:help] -> IO.puts(@moduledoc)
      opts[:list_tools] -> list_tools()
      opts[:demo] -> demo()
      opts[:tool] -> run_tool(opts[:tool], opts[:args])
      rest == [] -> Stdio.run()
      true -> IO.puts(:standard_error, "unexpected arguments: #{Enum.join(rest, " ")}")
    end
  end

  defp ensure_started do
    {:ok, _} = Application.ensure_all_started(:brazilian_soccer)
    :ok
  end

  defp list_tools do
    Enum.each(Tools.all(), fn tool ->
      IO.puts("#{tool.name}\n    #{tool.description}\n")
    end)
  end

  defp run_tool(name, args) do
    arguments =
      case args do
        nil ->
          %{}

        json ->
          case Jason.decode(json) do
            {:ok, map} when is_map(map) -> map
            _ -> %{}
          end
      end

    case Tools.call(name, arguments) do
      {:ok, %{text: text}} -> IO.puts(text)
      {:error, message} -> IO.puts(:standard_error, message)
    end
  end

  @doc "Answer every sample question and print the results."
  def demo do
    started = System.monotonic_time(:millisecond)
    graph = Repo.graph()

    IO.puts("""
    Brazilian Soccer MCP — sample questions
    #{map_size(graph.matches)} matches, #{map_size(graph.teams)} teams, #{map_size(graph.players)} players
    """)

    SampleQuestions.all()
    |> Enum.with_index(1)
    |> Enum.each(fn {question, index} ->
      IO.puts(String.duplicate("=", 78))
      IO.puts("Q#{index} [#{question.category}] #{question.question}")
      IO.puts("tool: #{question.tool} #{inspect(question.arguments)}")
      IO.puts(String.duplicate("-", 78))

      case SampleQuestions.answer(question) do
        {:ok, text} -> IO.puts(text)
        {:error, message} -> IO.puts("(no answer) " <> message)
      end

      IO.puts("")
    end)

    IO.puts(
      "#{length(SampleQuestions.all())} questions answered in #{System.monotonic_time(:millisecond) - started}ms"
    )
  end
end
