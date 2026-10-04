package drivers

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sync"
	"time"
)

// Connection talks to one running instance of the system through its public
// interface: the Model Context Protocol over stdio (JSON-RPC 2.0, one message
// per line).
type Connection struct {
	stderr bytes.Buffer // the system's diagnostics, reported if it fails
	mu     sync.Mutex
	cmd    *exec.Cmd
	stdin  io.WriteCloser
	out    *bufio.Reader
	nextID int
}

// ToolResult is what came back from asking the system one question.
type ToolResult struct {
	Text       string
	Structured map[string]any
	IsError    bool
	Duration   time.Duration
}

// StartConnection launches the system with the given data directory and
// performs the MCP initialisation handshake.
func StartConnection(dataDir string) (*Connection, error) {
	bin, err := systemBinary()
	if err != nil {
		return nil, err
	}
	cmd := exec.Command(bin, "-data", dataDir)
	c := &Connection{cmd: cmd}
	cmd.Stderr = &c.stderr
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, err
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, err
	}
	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("starting the soccer knowledge system: %w", err)
	}
	c.stdin, c.out = stdin, bufio.NewReaderSize(stdout, 1<<20)

	var init struct {
		ProtocolVersion string `json:"protocolVersion"`
		ServerInfo      struct {
			Name string `json:"name"`
		} `json:"serverInfo"`
		Capabilities struct {
			Tools any `json:"tools"`
		} `json:"capabilities"`
	}
	if err := c.request("initialize", map[string]any{
		"protocolVersion": "2025-06-18",
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": "acceptance-tests", "version": "1"},
	}, &init); err != nil {
		c.Close()
		return nil, fmt.Errorf("MCP initialize failed: %w", err)
	}
	if init.Capabilities.Tools == nil {
		c.Close()
		return nil, fmt.Errorf("the system does not offer any tools")
	}
	if err := c.notify("notifications/initialized"); err != nil {
		c.Close()
		return nil, err
	}
	return c, nil
}

// CallTool invokes one MCP tool and returns its answer.
func (c *Connection) CallTool(name string, args map[string]any) (ToolResult, error) {
	var raw struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		StructuredContent map[string]any `json:"structuredContent"`
		IsError           bool           `json:"isError"`
	}
	start := time.Now()
	err := c.request("tools/call", map[string]any{"name": name, "arguments": args}, &raw)
	res := ToolResult{Duration: time.Since(start), Structured: raw.StructuredContent, IsError: raw.IsError}
	for _, ct := range raw.Content {
		if ct.Type == "text" {
			res.Text += ct.Text
		}
	}
	return res, err
}

// ListTools returns the names of the tools the system offers.
func (c *Connection) ListTools() ([]string, error) {
	var raw struct {
		Tools []struct {
			Name string `json:"name"`
		} `json:"tools"`
	}
	if err := c.request("tools/list", map[string]any{}, &raw); err != nil {
		return nil, err
	}
	names := make([]string, 0, len(raw.Tools))
	for _, t := range raw.Tools {
		names = append(names, t.Name)
	}
	return names, nil
}

func (c *Connection) Close() {
	c.stdin.Close()
	done := make(chan struct{})
	go func() { c.cmd.Wait(); close(done) }()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		c.cmd.Process.Kill()
	}
}

func (c *Connection) notify(method string) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.write(map[string]any{"jsonrpc": "2.0", "method": method})
}

func (c *Connection) request(method string, params any, result any) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.nextID++
	id := c.nextID
	if err := c.write(map[string]any{"jsonrpc": "2.0", "id": id, "method": method, "params": params}); err != nil {
		return err
	}
	for {
		line, err := c.out.ReadBytes('\n')
		if err != nil {
			return fmt.Errorf("reading answer to %s: %w\n%s", method, err, c.stderr.String())
		}
		var resp struct {
			ID     *int            `json:"id"`
			Result json.RawMessage `json:"result"`
			Error  *struct {
				Code    int    `json:"code"`
				Message string `json:"message"`
			} `json:"error"`
		}
		if err := json.Unmarshal(line, &resp); err != nil {
			return fmt.Errorf("the system sent something that is not JSON-RPC: %q", line)
		}
		if resp.ID == nil || *resp.ID != id {
			continue // a notification or a stray message
		}
		if resp.Error != nil {
			return fmt.Errorf("%s failed: %s (%d)", method, resp.Error.Message, resp.Error.Code)
		}
		return json.Unmarshal(resp.Result, result)
	}
}

func (c *Connection) write(msg any) error {
	b, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	_, err = c.stdin.Write(append(b, '\n'))
	return err
}

var (
	buildOnce sync.Once
	builtPath string
	buildErr  error
)

// systemBinary returns the release candidate to test. A pipeline can supply
// one with SOCCER_SYSTEM_BINARY; otherwise it is built once per test run.
func systemBinary() (string, error) {
	if bin := os.Getenv("SOCCER_SYSTEM_BINARY"); bin != "" {
		return bin, nil
	}
	buildOnce.Do(func() {
		dir, err := os.MkdirTemp("", "brsoccer-build")
		if err != nil {
			buildErr = err
			return
		}
		builtPath = filepath.Join(dir, "brsoccer")
		cmd := exec.Command("go", "build", "-o", builtPath, ".")
		cmd.Dir = ModuleRoot()
		if out, err := cmd.CombinedOutput(); err != nil {
			buildErr = fmt.Errorf("building the system: %v\n%s", err, out)
		}
	})
	return builtPath, buildErr
}

// ModuleRoot is the directory holding the system's source and the provided
// datasets.
func ModuleRoot() string {
	_, file, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(file), "..", "..")
}
