package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func setupTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	db, err := openDB(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return httptest.NewServer(newRouter(db))
}

func TestHealth(t *testing.T) {
	srv := setupTestServer(t)
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/health")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := setupTestServer(t)
	defer srv.Close()

	body, _ := json.Marshal(map[string]any{
		"title":  "The Go Programming Language",
		"author": "Alan Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	resp, err := http.Post(srv.URL+"/books", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d", resp.StatusCode)
	}

	var created Book
	if err := json.NewDecoder(resp.Body).Decode(&created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 {
		t.Error("expected non-zero ID")
	}
	if created.Title != "The Go Programming Language" {
		t.Errorf("unexpected title: %s", created.Title)
	}

	// Get by ID
	resp2, err := http.Get(srv.URL + "/books/" + itoa(created.ID))
	if err != nil {
		t.Fatal(err)
	}
	defer resp2.Body.Close()
	if resp2.StatusCode != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", resp2.StatusCode)
	}
	var got Book
	json.NewDecoder(resp2.Body).Decode(&got)
	if got.ID != created.ID {
		t.Errorf("id mismatch: %d vs %d", got.ID, created.ID)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := setupTestServer(t)
	defer srv.Close()

	// Missing author
	body, _ := json.Marshal(map[string]any{"title": "Only Title"})
	resp, err := http.Post(srv.URL+"/books", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400 for missing author, got %d", resp.StatusCode)
	}

	// Missing title
	body, _ = json.Marshal(map[string]any{"author": "Only Author"})
	resp, err = http.Post(srv.URL+"/books", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400 for missing title, got %d", resp.StatusCode)
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := setupTestServer(t)
	defer srv.Close()

	for _, b := range []map[string]any{
		{"title": "Book A", "author": "Alice"},
		{"title": "Book B", "author": "Bob"},
		{"title": "Book C", "author": "Alice"},
	} {
		body, _ := json.Marshal(b)
		http.Post(srv.URL+"/books", "application/json", bytes.NewReader(body))
	}

	resp, err := http.Get(srv.URL + "/books?author=Alice")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if len(books) != 2 {
		t.Errorf("expected 2 books for Alice, got %d", len(books))
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	srv := setupTestServer(t)
	defer srv.Close()

	body, _ := json.Marshal(map[string]any{"title": "Original", "author": "Author"})
	resp, _ := http.Post(srv.URL+"/books", "application/json", bytes.NewReader(body))
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	resp.Body.Close()

	// Update
	upd, _ := json.Marshal(map[string]any{"title": "Updated", "author": "Author"})
	req, _ := http.NewRequest(http.MethodPut, srv.URL+"/books/"+itoa(created.ID), bytes.NewReader(upd))
	req.Header.Set("Content-Type", "application/json")
	resp2, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp2.Body.Close()
	if resp2.StatusCode != http.StatusOK {
		t.Errorf("update: expected 200, got %d", resp2.StatusCode)
	}

	// Delete
	req, _ = http.NewRequest(http.MethodDelete, srv.URL+"/books/"+itoa(created.ID), nil)
	resp3, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp3.Body.Close()
	if resp3.StatusCode != http.StatusNoContent {
		t.Errorf("delete: expected 204, got %d", resp3.StatusCode)
	}

	// Confirm gone
	resp4, _ := http.Get(srv.URL + "/books/" + itoa(created.ID))
	resp4.Body.Close()
	if resp4.StatusCode != http.StatusNotFound {
		t.Errorf("after delete: expected 404, got %d", resp4.StatusCode)
	}
}

func itoa(id int64) string {
	return strconv.FormatInt(id, 10)
}
