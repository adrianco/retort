Feature: Competition Queries
  As a user of the Brazilian soccer MCP server
  I want to query competition standings
  So that I can see league tables and results

  Scenario: Get Brasileirao standings
    Given the match data is loaded
    When I request standings for "Brasileirao" in season 2019
    Then I should receive a standings table
    And the standings should have points and win columns

  Scenario: Get competition statistics
    Given the match data is loaded
    When I request statistics for competition "Brasileirao"
    Then I should receive aggregate statistics
    And the statistics should include average goals per match
