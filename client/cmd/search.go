package cmd

import (
	"fmt"
	"shell-history-client/internal/client"
	"strings"

	"github.com/spf13/cobra"
)

var (
	searchHostname string
	searchUser     string
	searchLimit    int
)

var searchCmd = &cobra.Command{
	Use:   "search [query]",
	Short: "Search command history",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		query := args[0]
		apiClient := client.NewAPIClient(cfg.ServerURL, cfg.APIKey)

		results, err := apiClient.Search(query, searchHostname, searchUser, searchLimit)
		if err != nil {
			cmd.Printf("Error searching: %v\n", err)
			return
		}

		for _, cmdRes := range results {
			timestamp := cmdRes.Timestamp
			if len(timestamp) > 19 {
				timestamp = timestamp[:19]
			}
			timestamp = strings.Replace(timestamp, "T", " ", 1)
			exitStatus := ""
			if cmdRes.ExitCode != nil {
				exitStatus = fmt.Sprintf(" (exit: %d)", *cmdRes.ExitCode)
			}
			cmd.Printf("[%s] %s: %s%s\n", timestamp, cmdRes.Hostname, cmdRes.Command, exitStatus)
		}
	},
}

func init() {
	searchCmd.Flags().StringVar(&searchHostname, "hostname", "", "Filter by hostname")
	searchCmd.Flags().StringVar(&searchUser, "user", "", "Filter by username")
	searchCmd.Flags().IntVar(&searchLimit, "limit", 50, "Max results")
	rootCmd.AddCommand(searchCmd)
}
