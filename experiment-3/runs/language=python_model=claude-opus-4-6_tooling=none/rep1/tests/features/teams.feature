Feature: Team Queries
  As a user of the Brazilian soccer MCP server
  I want to query team statistics
  So that I can analyze team performance

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2019
    Then I should receive wins, losses, draws, and goals

  Scenario: Get team home record
    Given the match data is loaded
    When I request home statistics for "Corinthians"
    Then I should receive wins, losses, draws, and goals
    And the statistics should only count home matches

  Scenario: Compare teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head to head
    Then I should receive win counts for both teams
    And I should receive a draw count
