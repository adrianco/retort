Feature: Player Queries
  As a user of the Brazilian soccer MCP server
  I want to search for player information
  So that I can find details about soccer players

  Scenario: Search player by name
    Given the player data is loaded
    When I search for player "Neymar"
    Then I should find at least one player
    And the player should have a name containing "Neymar"

  Scenario: Search players by nationality
    Given the player data is loaded
    When I search for players from "Brazil"
    Then I should find at least one player
    And all players should be from "Brazil"

  Scenario: Search players by club
    Given the player data is loaded
    When I search for players at club "Santos"
    Then I should find at least one player

  Scenario: Search players by minimum rating
    Given the player data is loaded
    When I search for players with minimum overall 85
    Then I should find at least one player
    And all players should have overall rating at least 85
