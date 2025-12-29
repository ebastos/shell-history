package cmd

import (
	"fmt"

	"shell-history-client/internal/redaction"

	"github.com/spf13/cobra"
)

var (
	ruleName        string
	rulePattern     string
	ruleReplacement string
)

var redactionCmd = &cobra.Command{
	Use:   "redaction",
	Short: "Manage redaction rules for sensitive data",
	Long: `Configure regex patterns to redact sensitive data from commands
before they are sent to the server.

Redaction rules are stored in ~/.config/shell-history/config.json`,
}

var redactionListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all configured redaction rules",
	Run: func(cmd *cobra.Command, args []string) {
		if len(cfg.RedactionRules) == 0 {
			fmt.Println("No redaction rules configured.")
			fmt.Println("\nAdd rules with: shell-history redaction add --name \"Rule Name\" --pattern \"regex\" --replacement \"[REDACTED]\"")
			return
		}

		fmt.Printf("Configured redaction rules (%d):\n\n", len(cfg.RedactionRules))
		for i, rule := range cfg.RedactionRules {
			fmt.Printf("%d. %s\n", i+1, rule.Name)
			fmt.Printf("   Pattern:     %s\n", rule.Pattern)
			fmt.Printf("   Replacement: %s\n\n", rule.Replacement)
		}
	},
}

var redactionAddCmd = &cobra.Command{
	Use:   "add",
	Short: "Add a new redaction rule",
	Long: `Add a new regex pattern to redact sensitive data.

Examples:
  # Redact AWS access keys
  shell-history redaction add --name "AWS Keys" --pattern "AKIA[0-9A-Z]{16}" --replacement "[AWS_KEY]"

  # Redact password flags
  shell-history redaction add --name "Passwords" --pattern "--password\s+\S+" --replacement "--password [REDACTED]"

  # Redact Bearer tokens
  shell-history redaction add --name "Tokens" --pattern "Bearer\s+[^\s']+" --replacement "Bearer [TOKEN]"`,
	Run: func(cmd *cobra.Command, args []string) {
		if ruleName == "" || rulePattern == "" {
			fmt.Println("Error: --name and --pattern are required")
			return
		}

		if ruleReplacement == "" {
			ruleReplacement = "[REDACTED]"
		}

		// Check for duplicate name
		for _, rule := range cfg.RedactionRules {
			if rule.Name == ruleName {
				fmt.Printf("Error: A rule named %q already exists\n", ruleName)
				return
			}
		}

		newRule := redaction.Rule{
			Name:        ruleName,
			Pattern:     rulePattern,
			Replacement: ruleReplacement,
		}

		cfg.RedactionRules = append(cfg.RedactionRules, newRule)

		if err := saveConfig(); err != nil {
			fmt.Printf("Error saving config: %v\n", err)
			return
		}

		fmt.Printf("Added redaction rule: %s\n", ruleName)
	},
}

var redactionRemoveCmd = &cobra.Command{
	Use:   "remove [name]",
	Short: "Remove a redaction rule by name",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		nameToRemove := args[0]

		found := false
		newRules := make([]redaction.Rule, 0, len(cfg.RedactionRules))
		for _, rule := range cfg.RedactionRules {
			if rule.Name == nameToRemove {
				found = true
				continue
			}
			newRules = append(newRules, rule)
		}

		if !found {
			fmt.Printf("Error: No rule named %q found\n", nameToRemove)
			return
		}

		cfg.RedactionRules = newRules

		if err := saveConfig(); err != nil {
			fmt.Printf("Error saving config: %v\n", err)
			return
		}

		fmt.Printf("Removed redaction rule: %s\n", nameToRemove)
	},
}

func init() {
	redactionAddCmd.Flags().StringVar(&ruleName, "name", "", "Name for the redaction rule (required)")
	redactionAddCmd.Flags().StringVar(&rulePattern, "pattern", "", "Regex pattern to match (required)")
	redactionAddCmd.Flags().StringVar(&ruleReplacement, "replacement", "[REDACTED]", "Replacement text")

	redactionCmd.AddCommand(redactionListCmd)
	redactionCmd.AddCommand(redactionAddCmd)
	redactionCmd.AddCommand(redactionRemoveCmd)
	rootCmd.AddCommand(redactionCmd)
}
