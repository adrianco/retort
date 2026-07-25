defmodule BrazilianSoccer.RepoTest do
  @moduledoc """
  Feature: Loading and caching the graph

  Building the graph from 24k CSV rows takes a couple of seconds, so the result
  is cached on disk and keyed by the size and mtime of the source files.
  """

  use ExUnit.Case, async: false

  alias BrazilianSoccer.{Config, Repo}
  alias BrazilianSoccer.Data.Graph

  describe "Scenario: the graph is available to callers" do
    test "Given the application is started Then the graph loads on first use" do
      assert %Graph{} = graph = Repo.graph()
      assert Repo.loaded?()
      assert map_size(graph.matches) > 15_000
    end

    test "Given a second call Then the same graph comes back without rebuilding" do
      first = Repo.graph()
      {microseconds, second} = :timer.tc(&Repo.graph/0)

      assert first.meta == second.meta
      assert div(microseconds, 1000) < 50
    end
  end

  describe "Scenario: on-disk cache" do
    test "Given a warm cache Then a fresh VM loads the graph without re-parsing the CSVs" do
      assert File.exists?(Config.cache_file())

      script = """
      started = System.monotonic_time(:millisecond)
      graph = BrazilianSoccer.Repo.graph()
      IO.puts("#{"#"}{map_size(graph.matches)} #{"#"}{System.monotonic_time(:millisecond) - started}")
      """

      {output, 0} = System.cmd("mix", ["run", "-e", script], env: [{"MIX_ENV", "test"}])

      [matches, elapsed] =
        output |> String.trim() |> String.split() |> Enum.map(&String.to_integer/1)

      assert matches > 15_000
      assert elapsed < 1_500, "cold start took #{elapsed}ms, cache probably missed"
    end
  end

  describe "Scenario: graph metadata" do
    test "Given the loaded graph Then it reports the files it read" do
      files = Repo.graph().meta.files

      assert length(files) == 6
      assert Enum.all?(files, &(&1.rows > 0))
      assert Enum.all?(files, &String.ends_with?(&1.file, ".csv"))
    end
  end
end
