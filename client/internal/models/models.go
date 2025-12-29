package models

type Command struct {
	Command     string `json:"command"`
	Hostname    string `json:"hostname"`
	Username    string `json:"username"`
	AltUsername string `json:"alt_username,omitempty"`
	CWD         string `json:"cwd"`
	ExitCode    *int   `json:"exit_code"`
	SessionID   string `json:"session_id"`
	Timestamp   string `json:"timestamp,omitempty"`
	Redacted    bool   `json:"redacted,omitempty"`
}

type StatsResponse struct {
	TotalCommands int    `json:"total_commands"`
	ActiveHosts   int    `json:"active_hosts"`
	StorageUsed   string `json:"storage_used"`
}

type SearchResponse struct {
	Items []Command `json:"items"`
}
