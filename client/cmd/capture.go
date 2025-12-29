package cmd

import (
	"os"
	"shell-history-client/internal/buffer"
	"shell-history-client/internal/client"
	"shell-history-client/internal/models"
	"shell-history-client/internal/redaction"
	"shell-history-client/internal/session"
	"time"

	"github.com/spf13/cobra"
)

var (
	exitCode int
	cwd      string
)

var captureCmd = &cobra.Command{
	Use:   "capture [command]",
	Short: "Capture a shell command",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		commandText := args[0]

		sm, err := session.NewSessionManager()
		if err != nil {
			return // Silent fail for capture
		}

		bm, err := buffer.NewBufferManager()
		if err != nil {
			return
		}

		// Apply client-side redaction if rules are configured
		redactor := redaction.NewRedactor(cfg.RedactionRules)
		redactedCommand, wasRedacted := redactor.Redact(commandText)

		hostname, _ := os.Hostname()
		user := os.Getenv("USER")
		if user == "" {
			user = "unknown"
		}

		if cwd == "" {
			cwd, _ = os.Getwd()
		}

		cmdModel := models.Command{
			Command:     redactedCommand,
			Hostname:    hostname,
			Username:    user,
			AltUsername: os.Getenv("SUDO_USER"),
			CWD:         cwd,
			ExitCode:    &exitCode,
			SessionID:   sm.SessionID,
			Redacted:    wasRedacted,
		}

		apiClient := client.NewAPIClient(cfg.ServerURL, cfg.APIKey)
		err = apiClient.Capture(cmdModel)
		if err != nil {
			// Fallback to buffer
			cmdModel.Timestamp = time.Now().UTC().Format("2006-01-02T15:04:05.000000Z")
			bm.Add(cmdModel)
		}
	},
}

func init() {
	captureCmd.Flags().IntVar(&exitCode, "exit-code", 0, "Command exit code")
	captureCmd.Flags().StringVar(&cwd, "cwd", "", "Current working directory")
	rootCmd.AddCommand(captureCmd)
}
