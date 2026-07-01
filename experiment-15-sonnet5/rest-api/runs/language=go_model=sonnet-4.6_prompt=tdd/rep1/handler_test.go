package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := newSQLiteStore(":memory:")
	if err != nil {
		t.Fatalf("failed to create store: %v", err)
	}
	t.Cleanup(func() { store.close() })
	return httptest.NewServer(newRouter(store))
}

func TestHealthCheck(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestCreateBook(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	body := `{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`
	resp, err := http.Post(srv.URL+"/books", "application/json", bytes.NewBufferString(body))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		t.Errorf("expected 201, got %d", resp.StatusCode)
	}

	var book Book
	if err := json.NewDecoder(resp.Body).Decode(&book); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title %q, got %q", "The Go Programming Language", book.Title)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	tests := []struct {
		name string
		body string
	}{
		{"missing title", `{"author":"Someone","year":2020}`},
		{"missing author", `{"title":"A Book","year":2020}`},
		{"empty title", `{"title":"","author":"Someone"}`},
		{"empty author", `{"title":"A Book","author":""}`},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			resp, err := http.Post(srv.URL+"/books", "application/json", bytes.NewBufferString(tc.body))
			if err != nil {
				t.Fatalf("POST /books: %v", err)
			}
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusBadRequest {
				t.Errorf("expected 400, got %d", resp.StatusCode)
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	books := []string{
		`{"title":"Book One","author":"Alice","year":2020}`,
		`{"title":"Book Two","author":"Bob","year":2021}`,
		`{"title":"Book Three","author":"Alice","year":2022}`,
	}
	for _, b := range books {
		resp, err := http.Post(srv.URL+"/books", "application/json", bytes.NewBufferString(b))
		if err != nil {
			t.Fatalf("POST /books: %v", err)
		}
		resp.Body.Close()
	}

	resp, err := http.Get(srv.URL + "/books")
	if err != nil {
		t.Fatalf("GET /books: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var result []Book
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if len(result) != 3 {
		t.Errorf("expected 3 books, got %d", len(result))
	}
}

func TestListBooksAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	books := []string{
		`{"title":"Book One","author":"Alice","year":2020}`,
		`{"title":"Book Two","author":"Bob","year":2021}`,
		`{"title":"Book Three","author":"Alice","year":2022}`,
	}
	for _, b := range books {
		resp, _ := http.Post(srv.URL+"/books", "application/json", bytes.NewBufferString(b))
		resp.Body.Close()
	}

	resp, err := http.Get(srv.URL + "/books?author=Alice")
	if err != nil {
		t.Fatalf("GET /books?author=Alice: %v", err)
	}
	defer resp.Body.Close()

	var result []Book
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if len(result) != 2 {
		t.Errorf("expected 2 books by Alice, got %d", len(result))
	}
	for _, b := range result {
		if b.Author != "Alice" {
			t.Errorf("expected author Alice, got %q", b.Author)
		}
	}
}

func TestGetBook(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	body := `{"title":"Clean Code","author":"Robert Martin","year":2008}`
	resp, _ := http.Post(srv.URL+"/books", "application/json", bytes.NewBufferString(body))
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	resp.Body.Close()

	resp, err := http.Get(fmt.Sprintf("%s/books/%d", srv.URL, created.ID))
	if err != nil {
		t.Fatalf("GET /books/%d: %v", created.ID, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var got Book
	json.NewDecoder(resp.Body).Decode(&got)
	if got.ID != created.ID {
		t.Errorf("expected ID %d, got %d", created.ID, got.ID)
	}
	if got.Title != "Clean Code" {
		t.Errorf("expected title %q, got %q", "Clean Code", got.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/books/99999")
	if err != nil {
		t.Fatalf("GET /books/99999: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.StatusCode)
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	body := `{"title":"Original Title","author":"Author","year":2020}`
	resp, _ := http.Post(srv.URL+"/books", "application/json", bytes.NewBufferString(body))
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	resp.Body.Close()

	update := `{"title":"Updated Title","author":"Author","year":2021}`
	req, _ := http.NewRequest(http.MethodPut,
		fmt.Sprintf("%s/books/%d", srv.URL, created.ID),
		bytes.NewBufferString(update))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("PUT /books/%d: %v", created.ID, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var updated Book
	json.NewDecoder(resp.Body).Decode(&updated)
	if updated.Title != "Updated Title" {
		t.Errorf("expected updated title, got %q", updated.Title)
	}
	if updated.Year != 2021 {
		t.Errorf("expected year 2021, got %d", updated.Year)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	defer srv.Close()

	body := `{"title":"To Delete","author":"Author","year":2020}`
	resp, _ := http.Post(srv.URL+"/books", "application/json", bytes.NewBufferString(body))
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	resp.Body.Close()

	req, _ := http.NewRequest(http.MethodDelete,
		fmt.Sprintf("%s/books/%d", srv.URL, created.ID), nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("DELETE /books/%d: %v", created.ID, err)
	}
	resp.Body.Close()

	if resp.StatusCode != http.StatusNoContent {
		t.Errorf("expected 204, got %d", resp.StatusCode)
	}

	// verify it's gone
	resp, _ = http.Get(fmt.Sprintf("%s/books/%d", srv.URL, created.ID))
	resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", resp.StatusCode)
	}
}
