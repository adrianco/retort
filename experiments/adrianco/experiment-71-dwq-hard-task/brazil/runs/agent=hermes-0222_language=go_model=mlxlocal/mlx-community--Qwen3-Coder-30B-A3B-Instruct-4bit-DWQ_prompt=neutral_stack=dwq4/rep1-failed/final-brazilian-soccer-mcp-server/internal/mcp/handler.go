package mcp

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"

	"final-brazilian-soccer-mcp-server/internal/data"
)

type MCPHandler struct {
	dataLoader *data.DataLoader
}

func NewMCPHandler() *MCPHandler {
	return &MCPHandler{
		dataLoader: data.NewDataLoader(),
	}
}

func (m *MCPHandler) HandleMCP(w http.ResponseWriter, r *http.Request) {
	// Read request body
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Error reading request body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// Parse the MCP request
	var mcpRequest MCPRequest
	if err := json.Unmarshal(body, &mcpRequest); err != nil {
		http.Error(w, "Error parsing MCP request", http.StatusBadRequest)
		return
	}

	// Process the request based on method
	var response MCPResponse
	switch mcpRequest.Method {
	case "query":
		response = m.handleQuery(mcpRequest.Params)
	default:
		response = MCPResponse{
			Id:      mcpRequest.Id,
			Result:  nil,
			Error:   &MCPError{Code: "method_not_found", Message: "Method not supported"},
			IsError: true,
		}
	}

	// Send response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func (m *MCPHandler) handleQuery(params MCPQueryParams) MCPResponse {
	// Parse the query string
	query := params.Query
	if query == "" {
		return MCPResponse{
			Id:      params.Id,
			Result:  nil,
			Error:   &MCPError{Code: "invalid_query", Message: "Query cannot be empty"},
			IsError: true,
		}
	}

	// Process query and return results
	result, err := m.dataLoader.ProcessQuery(query)
	if err != nil {
		return MCPResponse{
			Id:      params.Id,
			Result:  nil,
			Error:   &MCPError{Code: "processing_error", Message: err.Error()},
			IsError: true,
		}
	}

	return MCPResponse{
		Id:      params.Id,
		Result:  result,
		Error:   nil,
		IsError: false,
	}
}

type MCPRequest struct {
	Id      string      `json:"id"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params"`
}

type MCPQueryParams struct {
	Id      string `json:"id"`
	Query   string `json:"query"`
}

type MCPResponse struct {
	Id      string      `json:"id"`
	Result  interface{} `json:"result,omitempty"`
	Error   *MCPError   `json:"error,omitempty"`
	IsError bool        `json:"isError,omitempty"`
}

type MCPError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}
