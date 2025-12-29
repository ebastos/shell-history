package cmd

import (
	"shell-history-client/internal/buffer"
	"shell-history-client/internal/client"

	"github.com/spf13/cobra"
)

var statsCmd = &cobra.Command{
	Use:   "stats",
	Short: "Show usage statistics",
	Run: func(cmd *cobra.Command, args []string) {
		apiClient := client.NewAPIClient(cfg.ServerURL, cfg.APIKey)
		stats, err := apiClient.GetStats()
		if err != nil {
			// fallback to local stats
			bm, err := buffer.NewBufferManager()
			if err != nil {
				cmd.Printf("Error getting local stats: %v\n", err)
				return
			}
			cmd.Printf("Buffered commands: %d\n", len(bm.Commands))
			cmd.Printf("Buffer path: %s\n", bm.BufferPath)
			return
		}

		if total, ok := stats["total_commands"]; ok {
			cmd.Printf("Total commands: %v\n", total)
		}
		if hosts, ok := stats["active_hosts"]; ok {
			cmd.Printf("Active hosts: %v\n", hosts)
		}
		if storage, ok := stats["storage_used"]; ok {
			cmd.Printf("Storage used: %v\n", storage)
		}
	},
}

func init() {
	rootCmd.AddCommand(statsCmd)
}
