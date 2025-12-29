// Package redaction provides client-side command redaction functionality.
// Users can configure custom regex patterns to redact sensitive data
// before commands are sent to the server.
package redaction

import (
	"regexp"
)

// Rule defines a redaction pattern with its replacement string.
type Rule struct {
	Name        string `json:"name"`
	Pattern     string `json:"pattern"`
	Replacement string `json:"replacement"`
}

// compiledRule holds a pre-compiled regex pattern with its replacement.
type compiledRule struct {
	pattern     *regexp.Regexp
	replacement string
}

// Redactor applies redaction rules to command strings.
type Redactor struct {
	rules []compiledRule
}

// NewRedactor creates a new Redactor with the given rules.
// Invalid regex patterns are silently skipped.
func NewRedactor(rules []Rule) *Redactor {
	r := &Redactor{
		rules: make([]compiledRule, 0, len(rules)),
	}

	for _, rule := range rules {
		// Compile with case-insensitive flag
		pattern, err := regexp.Compile("(?i)" + rule.Pattern)
		if err != nil {
			// Skip invalid patterns
			continue
		}
		r.rules = append(r.rules, compiledRule{
			pattern:     pattern,
			replacement: rule.Replacement,
		})
	}

	return r
}

// Redact applies all redaction rules to the command string.
// Returns the redacted command and a boolean indicating if any redaction occurred.
func (r *Redactor) Redact(command string) (string, bool) {
	if len(r.rules) == 0 {
		return command, false
	}

	result := command
	wasRedacted := false

	for _, rule := range r.rules {
		if rule.pattern.MatchString(result) {
			wasRedacted = true
			result = rule.pattern.ReplaceAllString(result, rule.replacement)
		}
	}

	return result, wasRedacted
}
