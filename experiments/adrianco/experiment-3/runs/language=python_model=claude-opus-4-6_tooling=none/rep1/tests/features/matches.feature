Feature: Match Queries
  As a user of the Brazilian soccer MCP server
  I want to search for and analyze match data
  So that I can find information about Brazilian soccer matches

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches by team
    Given the match data is loaded
    When I search for matches by team "Palmeiras"
    Then I should receive a list of matches
    And at least one match should involve "Palmeiras"

  Scenario: Find matches by season
    Given the match data is loaded
    When I search for matches in season 2019
    Then I should receive a list of matches
    And all matches should be from season 2019

  Scenario: Find matches by competition
    Given the match data is loaded
    When I search for matches in competition "Copa do Brasil"
    Then I should receive a list of matches
    And all matches should be from competition "Copa do Brasil"

  Scenario: Find matches by date range
    Given the match data is loaded
    When I search for matches from "2019-01-01" to "2019-12-31"
    Then I should receive a list of matches
