package redaction

import (
	"testing"
)

func TestRedactor_NoRules(t *testing.T) {
	r := NewRedactor(nil)
	result, wasRedacted := r.Redact("echo hello world")

	if wasRedacted {
		t.Error("expected wasRedacted to be false with no rules")
	}
	if result != "echo hello world" {
		t.Errorf("expected command unchanged, got %q", result)
	}
}

func TestRedactor_AWSKey(t *testing.T) {
	rules := []Rule{
		{Name: "AWS Keys", Pattern: `AKIA[0-9A-Z]{16}`, Replacement: "[AWS_KEY]"},
	}
	r := NewRedactor(rules)

	result, wasRedacted := r.Redact("export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")

	if !wasRedacted {
		t.Error("expected wasRedacted to be true")
	}
	if result != "export AWS_ACCESS_KEY_ID=[AWS_KEY]" {
		t.Errorf("unexpected result: %q", result)
	}
}

func TestRedactor_PasswordFlag(t *testing.T) {
	rules := []Rule{
		{Name: "Passwords", Pattern: `--password\s+\S+`, Replacement: "--password [REDACTED]"},
	}
	r := NewRedactor(rules)

	result, wasRedacted := r.Redact("mysql -u root --password super_secret_123")

	if !wasRedacted {
		t.Error("expected wasRedacted to be true")
	}
	if result != "mysql -u root --password [REDACTED]" {
		t.Errorf("unexpected result: %q", result)
	}
}

func TestRedactor_BearerToken(t *testing.T) {
	rules := []Rule{
		{Name: "Tokens", Pattern: `Bearer\s+[^\s']+`, Replacement: "Bearer [TOKEN]"},
	}
	r := NewRedactor(rules)

	result, wasRedacted := r.Redact("curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9' https://api.example.com")

	if !wasRedacted {
		t.Error("expected wasRedacted to be true")
	}
	if result != "curl -H 'Authorization: Bearer [TOKEN]' https://api.example.com" {
		t.Errorf("unexpected result: %q", result)
	}
}

func TestRedactor_APIKey(t *testing.T) {
	rules := []Rule{
		{Name: "API Keys", Pattern: `api[_-]?key\s*[=:]\s*[^\s']+`, Replacement: "api_key=[REDACTED]"},
	}
	r := NewRedactor(rules)

	result, wasRedacted := r.Redact("curl -H 'api_key=sk-1234567890abcdef' https://api.example.com")

	if !wasRedacted {
		t.Error("expected wasRedacted to be true")
	}
	if result != "curl -H 'api_key=[REDACTED]' https://api.example.com" {
		t.Errorf("unexpected result: %q", result)
	}
}

func TestRedactor_MultipleRules(t *testing.T) {
	rules := []Rule{
		{Name: "AWS Keys", Pattern: `AKIA[0-9A-Z]{16}`, Replacement: "[AWS_KEY]"},
		{Name: "Passwords", Pattern: `--password\s+\S+`, Replacement: "--password [REDACTED]"},
	}
	r := NewRedactor(rules)

	result, wasRedacted := r.Redact("aws configure --password secret123 AKIAIOSFODNN7EXAMPLE")

	if !wasRedacted {
		t.Error("expected wasRedacted to be true")
	}
	// Both patterns should be applied
	if result != "aws configure --password [REDACTED] [AWS_KEY]" {
		t.Errorf("unexpected result: %q", result)
	}
}

func TestRedactor_NoMatch(t *testing.T) {
	rules := []Rule{
		{Name: "AWS Keys", Pattern: `AKIA[0-9A-Z]{16}`, Replacement: "[AWS_KEY]"},
	}
	r := NewRedactor(rules)

	result, wasRedacted := r.Redact("ls -la")

	if wasRedacted {
		t.Error("expected wasRedacted to be false")
	}
	if result != "ls -la" {
		t.Errorf("expected command unchanged, got %q", result)
	}
}

func TestRedactor_CaseInsensitive(t *testing.T) {
	rules := []Rule{
		{Name: "Tokens", Pattern: `bearer\s+[^\s']+`, Replacement: "Bearer [TOKEN]"},
	}
	r := NewRedactor(rules)

	result, wasRedacted := r.Redact("curl -H 'Authorization: BEARER abc123' https://api.example.com")

	if !wasRedacted {
		t.Error("expected wasRedacted to be true (case insensitive)")
	}
	if result != "curl -H 'Authorization: Bearer [TOKEN]' https://api.example.com" {
		t.Errorf("unexpected result: %q", result)
	}
}

func TestRedactor_InvalidRegex(t *testing.T) {
	rules := []Rule{
		{Name: "Invalid", Pattern: `[invalid(regex`, Replacement: "[REDACTED]"},
		{Name: "Valid", Pattern: `secret`, Replacement: "[REDACTED]"},
	}
	r := NewRedactor(rules)

	// Should skip invalid regex and still apply valid ones
	result, wasRedacted := r.Redact("my secret password")

	if !wasRedacted {
		t.Error("expected wasRedacted to be true")
	}
	if result != "my [REDACTED] password" {
		t.Errorf("unexpected result: %q", result)
	}
}
