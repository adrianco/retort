package driver

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"sync"
	"time"
)

// mcpClient speaks MCP (JSON-RPC 2.0, one message per line) to a server
// process over its standard input and output.
type mcpClient struct {
	cmd    *exec.Cmd
	stdin  io.WriteCloser
	lines  chan []byte
	stderr *lockedBuffer
	nextID int
}

type rpcResponse struct {
	ID     *int            `json:"id"`
	Result json.RawMessage `json:"result"`
	Error  *struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

type lockedBuffer struct {
	mu  sync.Mutex
	buf bytes.Buffer
}

func (b *lockedBuffer) Write(p []byte) (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.Write(p)
}

func (b *lockedBuffer) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.String()
}

const responseTimeout = 20 * time.Second

func startMCPClient(binary string, args ...string) (*mcpClient, error) {
	cmd := exec.Command(binary, args...)
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, err
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, err
	}
	c := &mcpClient{cmd: cmd, stdin: stdin, lines: make(chan []byte, 16), stderr: &lockedBuffer{}}
	cmd.Stderr = c.stderr
	if err := cmd.Start(); err != nil {
		return nil, err
	}
	go func() {
		scanner := bufio.NewScanner(stdout)
		scanner.Buffer(make([]byte, 1024*1024), 64*1024*1024)
		for scanner.Scan() {
			line := append([]byte(nil), scanner.Bytes()...)
			c.lines <- line
		}
		close(c.lines)
	}()

	_, err = c.request("initialize", map[string]any{
		"protocolVersion": "2025-06-18",
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": "acceptance-tests", "version": "1.0"},
	})
	if err != nil {
		c.close()
		return nil, err
	}
	if err := c.notify("notifications/initialized"); err != nil {
		c.close()
		return nil, err
	}
	return c, nil
}

func (c *mcpClient) notify(method string) error {
	msg, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "method": method})
	_, err := c.stdin.Write(append(msg, '\n'))
	return err
}

func (c *mcpClient) request(method string, params any) (json.RawMessage, error) {
	c.nextID++
	id := c.nextID
	msg, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "id": id, "method": method, "params": params})
	if _, err := c.stdin.Write(append(msg, '\n')); err != nil {
		return nil, fmt.Errorf("could not send %s to the server: %v\n%s", method, err, c.stderr.String())
	}
	timeout := time.After(responseTimeout)
	for {
		select {
		case line, ok := <-c.lines:
			if !ok {
				return nil, fmt.Errorf("server stopped while answering %s\n%s", method, c.stderr.String())
			}
			var resp rpcResponse
			if err := json.Unmarshal(line, &resp); err != nil {
				return nil, fmt.Errorf("server sent something that is not JSON-RPC: %q", line)
			}
			if resp.ID == nil || *resp.ID != id {
				continue // a notification, or a reply to someone else
			}
			if resp.Error != nil {
				return nil, fmt.Errorf("server refused %s: %s", method, resp.Error.Message)
			}
			return resp.Result, nil
		case <-timeout:
			return nil, fmt.Errorf("no answer to %s within %s", method, responseTimeout)
		}
	}
}

func (c *mcpClient) close() {
	_ = c.stdin.Close()
	done := make(chan struct{})
	go func() { _ = c.cmd.Wait(); close(done) }()
	select {
	case <-done:
	case <-time.After(3 * time.Second):
		_ = c.cmd.Process.Kill()
		<-done
	}
}
