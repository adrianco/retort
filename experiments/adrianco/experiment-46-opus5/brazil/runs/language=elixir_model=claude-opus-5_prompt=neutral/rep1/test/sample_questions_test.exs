defmodule BrazilianSoccer.SampleQuestionsTest do
  @moduledoc """
  Feature: The questions from the specification

  Scenario: A model asks the documented questions
    Given the MCP tool catalogue
    When every sample question is asked through it
    Then each one is answered from the data, and the answers say what they say
  """

  use BrazilianSoccer.GraphCase, async: true

  alias BrazilianSoccer.MCP.Tools
  alias BrazilianSoccer.SampleQuestions

  describe "Scenario: coverage" do
    test "Given the catalogue Then it holds at least 20 questions across all five categories" do
      questions = SampleQuestions.all()

      assert length(questions) >= 20

      categories = questions |> Enum.map(& &1.category) |> Enum.uniq() |> Enum.sort()

      assert categories == [
               "Competition queries",
               "Match queries",
               "Player queries",
               "Statistical analysis",
               "Team queries"
             ]
    end

    test "Given every question Then it names a tool that exists" do
      for %{tool: tool} <- SampleQuestions.all() do
        assert {:ok, _} = Tools.fetch(tool), "unknown tool #{tool}"
      end
    end

    test "Given every question Then it is answered from the data" do
      for question <- SampleQuestions.all() do
        case SampleQuestions.answer(question) do
          {:ok, text} ->
            assert String.length(text) > 20, "thin answer for: #{question.question}"

          {:error, message} ->
            # the only acceptable "failure" is the documented gap in the FIFA
            # export, and it has to explain itself
            assert message =~ "does not license every Brazilian club",
                   "unanswered question #{question.question}: #{message}"
        end
      end
    end
  end

  describe "Scenario: the answers are right" do
    test "Given the 2019 Brasileirão Then Flamengo is the champion on 90 points" do
      {:ok, %{text: text}} =
        Tools.call("competition_champion", %{"competition" => "Brasileirão", "season" => 2019})

      assert text =~ "Flamengo"
      assert text =~ "90 points"
    end

    test "Given the 2020 Brasileirão Then the relegated clubs are named" do
      {:ok, %{text: text}} = Tools.call("league_standings", %{"season" => 2020})

      for club <- ["Vasco da Gama", "Goiás", "Coritiba", "Botafogo"] do
        assert text =~ club
      end

      relegated =
        text
        |> String.split("\n")
        |> Enum.filter(&String.contains?(&1, "Relegated"))

      assert length(relegated) == 4
    end

    test "Given Flamengo and Corinthians Then the last meeting has a date and a score" do
      {:ok, %{text: text}} =
        Tools.call("last_meeting", %{"team_a" => "Flamengo", "team_b" => "Corinthians"})

      assert text =~ ~r/Most recent meeting: \d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+/
    end

    test "Given the Brasileirão Then the average goals per match is around 2.5" do
      {:ok, %{data: data}} = Tools.call("match_statistics", %{"competition" => "Brasileirão"})

      assert_in_delta data["goals_per_match"], 2.5, 0.3
      assert data["matches"] > 8_000
    end

    test "Given Brazilian players Then the best rated is Neymar" do
      {:ok, %{text: text}} =
        Tools.call("search_players", %{
          "nationality" => "Brazil",
          "sort_by" => "overall",
          "limit" => 1
        })

      assert text =~ "Neymar"
    end

    test "Given a club the FIFA export omits Then the answer explains the gap" do
      assert {:error, message} = Tools.call("club_squad", %{"club" => "Flamengo"})
      assert message =~ "no players in the FIFA dataset"
    end

    test "Given the 2018 Libertadores Then the bracket ends with River Plate" do
      {:ok, %{text: text}} =
        Tools.call("cup_bracket", %{"competition" => "Libertadores", "season" => 2018})

      assert text =~ "FINAL"
      assert text =~ "Winner: River Plate"
    end
  end

  describe "Scenario: the catalogue is documented" do
    test "Given the markdown resource Then every question appears with its tool" do
      markdown = SampleQuestions.markdown()

      for question <- SampleQuestions.all() do
        assert String.contains?(markdown, question.question)
        assert String.contains?(markdown, question.tool)
      end
    end
  end
end
