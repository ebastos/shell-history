package buffer

import (
	"encoding/json"
	"os"
	"path/filepath"
	"shell-history-client/internal/models"
)

type BufferManager struct {
	BufferPath string
	Commands   []models.Command
}

func NewBufferManager() (*BufferManager, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, err
	}

	bufferDir := filepath.Join(home, ".history")
	if err := os.MkdirAll(bufferDir, 0755); err != nil {
		return nil, err
	}

	bm := &BufferManager{
		BufferPath: filepath.Join(bufferDir, "buffer.json"),
		Commands:   []models.Command{},
	}

	if err := bm.Load(); err != nil && !os.IsNotExist(err) {
		return nil, err
	}

	return bm, nil
}

func (bm *BufferManager) Load() error {
	data, err := os.ReadFile(bm.BufferPath)
	if err != nil {
		return err
	}

	return json.Unmarshal(data, &bm.Commands)
}

func (bm *BufferManager) Save() error {
	data, err := json.Marshal(bm.Commands)
	if err != nil {
		return err
	}

	return os.WriteFile(bm.BufferPath, data, 0644)
}

func (bm *BufferManager) Add(cmd models.Command) error {
	bm.Commands = append(bm.Commands, cmd)
	return bm.Save()
}

func (bm *BufferManager) Clear() error {
	bm.Commands = []models.Command{}
	return bm.Save()
}
