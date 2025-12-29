package cmd

import (
	"io"
	"os"
	"shell-history-client/internal/config"

	"github.com/spf13/cobra"
)

var (
	cfg       config.Config
	serverURL string
)

var rootCmd = &cobra.Command{
	Use:   "shell-history",
	Short: "Shell History CLI - Search and manage your shell history",
	PersistentPreRun: func(cmd *cobra.Command, args []string) {
		cfg = config.LoadConfig()
		if serverURL != "" {
			cfg.ServerURL = serverURL
		}
	},
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	rootCmd.PersistentFlags().StringVar(&serverURL, "server", "", "Server URL")
}

func SetArgs(args []string) {
	rootCmd.SetArgs(args)
}

func SetOut(w io.Writer) {
	rootCmd.SetOut(w)
}

// saveConfig saves the current configuration to disk.
func saveConfig() error {
	return config.SaveConfig(cfg)
}
