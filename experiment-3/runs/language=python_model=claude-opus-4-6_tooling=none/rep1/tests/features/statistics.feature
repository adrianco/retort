Feature: Statistical Analysis
  As a user of the Brazilian soccer MCP server
  I want to calculate aggregate statistics
  So that I can analyze trends in Brazilian soccer

  Scenario: Calculate overall match statistics
    Given the match data is loaded
    When I request overall match statistics
    Then I should receive total matches count
    And I should receive average goals per match
    And I should receive home and away win rates

  Scenario: Calculate team-specific statistics
    Given the match data is loaded
    When I request match statistics for team "Flamengo"
    Then I should receive total matches count
    And I should receive the biggest win

  Scenario: Find biggest wins in dataset
    Given the match data is loaded
    When I request overall match statistics
    Then I should receive the biggest win
