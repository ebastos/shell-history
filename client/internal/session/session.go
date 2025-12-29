package session

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
)

type SessionManager struct {
	SessionID string
}

func NewSessionManager() (*SessionManager, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, err
	}

	sessionDir := filepath.Join(home, ".history")
	if err := os.MkdirAll(sessionDir, 0755); err != nil {
		return nil, err
	}

	sessionFile := filepath.Join(sessionDir, "session_id")
	if _, err := os.Stat(sessionFile); err == nil {
		data, err := os.ReadFile(sessionFile)
		if err == nil {
			id := strings.TrimSpace(string(data))
			if id != "" {
				return &SessionManager{SessionID: id}, nil
			}
		}
	}

	id := uuid.New().String()
	if err := os.WriteFile(sessionFile, []byte(id), 0644); err != nil {
		return nil, err
	}

	return &SessionManager{SessionID: id}, nil
}
