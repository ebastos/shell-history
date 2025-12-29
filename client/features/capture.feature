Feature: Capture commands
  As a user
  I want my shell commands to be captured automatically
  So that I can search them later

  Scenario: Capturing a command
    Given the server is running
    When I run the command "capture ls -la"
    Then the server should have received a request for "/api/v1/commands/"
