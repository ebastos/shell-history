package cmd

import (
	"shell-history-client/internal/config"

	"github.com/spf13/cobra"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage configuration",
}

var configShowCmd = &cobra.Command{
	Use:   "show",
	Short: "Show current configuration",
	Run: func(cmd *cobra.Command, args []string) {
		cfg := config.LoadConfig()
		cmd.Printf("Server URL: %s\n", cfg.ServerURL)
		if cfg.APIKey != "" {
			// Only show first 8 chars for security
			masked := cfg.APIKey[:8] + "..." + cfg.APIKey[len(cfg.APIKey)-4:]
			cmd.Printf("API Key: %s\n", masked)
		} else {
			cmd.Println("API Key: (not set)")
		}
	},
}

var configSetAPIKeyCmd = &cobra.Command{
	Use:   "set-api-key [key]",
	Short: "Set API key",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		apiKey := args[0]
		cfg := config.LoadConfig()
		cfg.APIKey = apiKey

		if err := config.SaveConfig(cfg); err != nil {
			cmd.Printf("Error saving configuration: %v\n", err)
			return
		}

		cmd.Println("API key saved successfully")
	},
}

var configSetServerCmd = &cobra.Command{
	Use:   "set-server [url]",
	Short: "Set server URL",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		serverURL := args[0]
		cfg := config.LoadConfig()
		cfg.ServerURL = serverURL

		if err := config.SaveConfig(cfg); err != nil {
			cmd.Printf("Error saving configuration: %v\n", err)
			return
		}

		cmd.Printf("Server URL set to: %s\n", serverURL)
	},
}

func init() {
	configCmd.AddCommand(configShowCmd)
	configCmd.AddCommand(configSetAPIKeyCmd)
	configCmd.AddCommand(configSetServerCmd)
	rootCmd.AddCommand(configCmd)
}
