package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"shell-history-client/cmd"
	"shell-history-client/internal/models"
	"strings"
	"testing"

	msgs "github.com/cucumber/messages/go/v28"
	"github.com/go-bdd/gobdd"
)

func TestBDD(t *testing.T) {
	featuresPath := "/Users/main/src/shell-history/client/features/*.feature"
	suite := gobdd.NewSuite(t,
		gobdd.WithFeaturesPath(featuresPath),
		gobdd.WithBeforeScenario(func(ctx gobdd.Context) {
			lastOutput = ""
			mockResponses = make(map[string]interface{})
			mockStats = make(map[string]interface{})
			receivedRequests = nil
		}),
	)

	suite.AddStep(`the server is running`, givenServerIsRunning)
	suite.AddStep(`the server will return these commands for query "(.*)":`, givenServerReturnsCommands)
	suite.AddStep(`the server will return these stats:`, givenServerReturnsStats)
	suite.AddStep(`I run the command "(.*)"`, whenIRunCommand)
	suite.AddStep(`the output should contain "(.*)"`, thenOutputShouldContain)
	suite.AddStep(`the server should have received a request for "(.*)"`, thenServerReceivedRequest)

	suite.Run()
}

var (
	lastOutput       string
	mockServer       *httptest.Server
	mockResponses    map[string]interface{}
	mockStats        map[string]interface{}
	receivedRequests []string
)

func givenServerIsRunning(t gobdd.StepTest, ctx gobdd.Context) {
	ensureMockServer()
}

func givenServerReturnsStats(t gobdd.StepTest, ctx gobdd.Context, table msgs.DataTable) {
	if mockStats == nil {
		mockStats = make(map[string]interface{})
	}

	// Assuming the table has one data row
	if len(table.Rows) > 1 {
		row := table.Rows[1]
		mockStats["total_commands"] = row.Cells[0].Value
		mockStats["active_hosts"] = row.Cells[1].Value
		mockStats["storage_used"] = row.Cells[2].Value
	}

	ensureMockServer()
}

func ensureMockServer() {
	if mockServer == nil {
		mockServer = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			receivedRequests = append(receivedRequests, r.URL.Path)
			if strings.Contains(r.URL.Path, "/api/v1/stats/") {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(mockStats)
				return
			}

			q := r.URL.Query().Get("q")
			if resp, ok := mockResponses[q]; ok {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(resp)
			} else {
				w.WriteHeader(http.StatusNotFound)
			}
		}))
	}
}

func givenServerReturnsCommands(t gobdd.StepTest, ctx gobdd.Context, query string, table msgs.DataTable) {
	if mockResponses == nil {
		mockResponses = make(map[string]interface{})
	}

	var commands []models.Command
	// Skip header row
	for i := 1; i < len(table.Rows); i++ {
		row := table.Rows[i]
		cmdStr := row.Cells[0].Value
		hostname := row.Cells[1].Value
		user := row.Cells[2].Value
		timestamp := row.Cells[3].Value

		commands = append(commands, models.Command{
			Command:   cmdStr,
			Hostname:  hostname,
			Username:  user,
			Timestamp: timestamp,
		})
	}

	mockResponses[query] = models.SearchResponse{
		Items: commands,
	}

	ensureMockServer()
}

func whenIRunCommand(t gobdd.StepTest, ctx gobdd.Context, commandLine string) {
	var args []string
	if strings.HasPrefix(commandLine, "capture ") {
		args = []string{"capture", strings.TrimPrefix(commandLine, "capture ")}
	} else {
		args = strings.Split(commandLine, " ")
	}

	// Add server flag if mockServer is running
	if mockServer != nil {
		args = append(args, "--server", mockServer.URL)
	}

	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetArgs(args)

	// We need to be careful with Execute() because it might call os.Exit
	// For testing, we might want to call the command Run function directly if possible,
	// but using Execute() is more realistic for integration test.
	// Since we are running in a test, let's hope it doesn't exit.
	cmd.Execute()

	lastOutput = buf.String()
}

func thenOutputShouldContain(t gobdd.StepTest, ctx gobdd.Context, expected string) {
	if !strings.Contains(lastOutput, expected) {
		t.Errorf("expected output to contain %q, but got %q", expected, lastOutput)
	}
}

func thenServerReceivedRequest(t gobdd.StepTest, ctx gobdd.Context, expectedPath string) {
	found := false
	t.Logf("Received requests: %v", receivedRequests)
	for _, path := range receivedRequests {
		if path == expectedPath {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected server to have received request for %q, but it didn't. Received: %v", expectedPath, receivedRequests)
	}
}
