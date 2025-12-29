package cmd

import (
	"shell-history-client/internal/buffer"
	"shell-history-client/internal/client"
	"shell-history-client/internal/models"

	"github.com/spf13/cobra"
)

var flushCmd = &cobra.Command{
	Use:   "flush",
	Short: "Flush local command buffer",
	Run: func(cmd *cobra.Command, args []string) {
		bm, err := buffer.NewBufferManager()
		if err != nil {
			cmd.Printf("Error accessing buffer: %v\n", err)
			return
		}

		if len(bm.Commands) == 0 {
			cmd.Println("Buffer is empty")
			return
		}

		apiClient := client.NewAPIClient(cfg.ServerURL, cfg.APIKey)
		sent := 0
		var remaining []models.Command

		for _, cmdModel := range bm.Commands {
			err := apiClient.Capture(cmdModel)
			if err != nil {
				remaining = append(remaining, cmdModel)
			} else {
				sent++
			}
		}

		bm.Commands = remaining
		err = bm.Save()
		if err != nil {
			cmd.Printf("Error saving remaining buffer: %v\n", err)
		}

		cmd.Printf("Sent %d buffered commands\n", sent)
		if len(remaining) > 0 {
			cmd.Printf("%d commands still buffered due to errors\n", len(remaining))
		}
	},
}

func init() {
	rootCmd.AddCommand(flushCmd)
}
