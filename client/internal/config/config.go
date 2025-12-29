package config

import (
	"encoding/json"
	"os"
	"path/filepath"

	"shell-history-client/internal/redaction"
)

// Config holds the client configuration.
type Config struct {
	ServerURL      string
	APIKey         string
	RedactionRules []redaction.Rule
}

type configFile struct {
	ServerURL      string           `json:"server_url"`
	APIKey         string           `json:"api_key"`
	RedactionRules []redaction.Rule `json:"redaction_rules,omitempty"`
}

func configPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	configDir := filepath.Join(home, ".config", "shell-history")
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return "", err
	}
	return filepath.Join(configDir, "config.json"), nil
}

func LoadConfig() Config {
	cfg := Config{
		ServerURL: "http://localhost:3000",
	}

	// Load from environment first (takes precedence)
	if serverURL := os.Getenv("HISTORY_CLIENT_URL"); serverURL != "" {
		cfg.ServerURL = serverURL
	}
	if apiKey := os.Getenv("HISTORY_API_KEY"); apiKey != "" {
		cfg.APIKey = apiKey
	}

	// Load from config file
	configPath, err := configPath()
	if err != nil {
		return cfg
	}

	data, err := os.ReadFile(configPath)
	if err != nil {
		return cfg
	}

	var fileCfg configFile
	if err := json.Unmarshal(data, &fileCfg); err != nil {
		return cfg
	}

	// Only use file values if environment variables are not set
	if cfg.ServerURL == "http://localhost:3000" && fileCfg.ServerURL != "" {
		cfg.ServerURL = fileCfg.ServerURL
	}
	if cfg.APIKey == "" && fileCfg.APIKey != "" {
		cfg.APIKey = fileCfg.APIKey
	}

	// Load redaction rules from config file
	cfg.RedactionRules = fileCfg.RedactionRules

	return cfg
}

func SaveConfig(cfg Config) error {
	configPath, err := configPath()
	if err != nil {
		return err
	}

	fileCfg := configFile{
		ServerURL:      cfg.ServerURL,
		APIKey:         cfg.APIKey,
		RedactionRules: cfg.RedactionRules,
	}

	data, err := json.MarshalIndent(fileCfg, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(configPath, data, 0600)
}
