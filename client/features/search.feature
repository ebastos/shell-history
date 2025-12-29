Feature: Search commands
  As a user
  I want to search my shell history
  So that I can find previous commands

  Scenario: Searching for a command
    Given the server will return these commands for query "ls":
      | command | hostname | user | timestamp           |
      | ls -la  | macbook  | main | 2023-10-27T10:00:00Z |
      | ls /tmp | macbook  | main | 2023-10-27T10:05:00Z |
    When I run the command "search ls"
    Then the output should contain "ls -la"
    And the output should contain "ls /tmp"
    And the output should contain "macbook"
