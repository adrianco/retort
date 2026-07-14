Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches by team and season
    Given the match data is loaded
    When I search for "Palmeiras" matches in season 2019
    Then I should receive a list of matches
    And all matches should involve "Palmeiras"

  Scenario: Find matches by competition
    Given the match data is loaded
    When I search for matches in "Copa do Brasil"
    Then I should receive a list of matches
    And all matches should be from "Copa do Brasil"

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2019
    Then I should receive wins, losses, draws, and goals

  Scenario: Get head-to-head comparison
    Given the match data is loaded
    When I compare "Flamengo" and "Corinthians" head to head
    Then I should receive head-to-head statistics
    And the result should include wins for both teams

  Scenario: Get Brasileirao standings
    Given the match data is loaded
    When I request standings for season 2019
    Then I should receive a standings table
    And "Flamengo" should be the champion

  Scenario: Search players by nationality
    Given the match data is loaded
    When I search for players with nationality "Brazil"
    Then I should receive a list of players
    And all players should be Brazilian

  Scenario: Search players by club
    Given the match data is loaded
    When I search for players at club "Santos"
    Then I should receive a list of players

  Scenario: Get competition statistics
    Given the match data is loaded
    When I request statistics for "Brasileirão"
    Then I should receive competition statistics with goals and win rates

  Scenario: Handle team name normalization
    Given the match data is loaded
    When I search for matches for "Palmeiras-SP"
    Then I should receive a list of matches
    And the results should match searching for "Palmeiras"
