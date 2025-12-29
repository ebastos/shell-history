package cmd

import (
	"shell-history-client/internal/client"

	"github.com/spf13/cobra"
)

var testCmd = &cobra.Command{
	Use:   "test",
	Short: "Test connection to server",
	Run: func(cmd *cobra.Command, args []string) {
		apiClient := client.NewAPIClient(cfg.ServerURL, cfg.APIKey)
		health, err := apiClient.HealthCheck()
		if err != nil {
			cmd.Printf("✗ Cannot connect to %s\n", cfg.ServerURL)
			cmd.Printf("  Error: %v\n", err)
			return
		}

		cmd.Printf("✓ Connected to %s\n", cfg.ServerURL)
		if status, ok := health["status"]; ok {
			cmd.Printf("  Status: %v\n", status)
		}
	},
}

func init() {
	rootCmd.AddCommand(testCmd)
}
