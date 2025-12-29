Feature: Show statistics
  As a user
  I want to see usage statistics
  So that I know how many commands I have captured

  Scenario: Showing server statistics
    Given the server will return these stats:
      | total_commands | active_hosts | storage_used |
      | 1234           | 5            | 10 MB        |
    When I run the command "stats"
    Then the output should contain "Total commands: 1234"
    And the output should contain "Active hosts: 5"
    And the output should contain "Storage used: 10 MB"
