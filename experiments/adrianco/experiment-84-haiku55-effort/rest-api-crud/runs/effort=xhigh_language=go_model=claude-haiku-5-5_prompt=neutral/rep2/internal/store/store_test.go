package store

import (
	"context"
	"errors"
	"path/filepath"
	"reflect"
	"testing"

	"bookapi/internal/book"
)

func intPtr(v int) *int       { return &v }
func strPtr(v string) *string { return &v }

func openTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open() error = %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestCreateAndGetRoundTrip(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	in := book.Input{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("9780441013593")}
	created, err := s.Create(ctx, in)
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create() returned ID 0")
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get() error = %v", err)
	}
	if !reflect.DeepEqual(got, created) {
		t.Errorf("Get() = %+v, want %+v", got, created)
	}
}

func TestOptionalFieldsStoredAsNull(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	created, err := s.Create(ctx, book.Input{Title: "Untitled Notes", Author: "Anon"})
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get() error = %v", err)
	}
	if got.Year != nil || got.ISBN != nil {
		t.Errorf("Get() year=%v isbn=%v, want both nil", got.Year, got.ISBN)
	}
}

func TestGetMissingReturnsErrNotFound(t *testing.T) {
	s := openTestStore(t)

	_, err := s.Get(context.Background(), 404)
	if !errors.Is(err, ErrNotFound) {
		t.Errorf("Get() error = %v, want ErrNotFound", err)
	}
}

func TestListOrdersByIDAndFiltersByAuthor(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	inputs := []book.Input{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Children of Dune", Author: "frank herbert"},
	}
	for _, in := range inputs {
		if _, err := s.Create(ctx, in); err != nil {
			t.Fatalf("Create(%q) error = %v", in.Title, err)
		}
	}

	all, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List(all) error = %v", err)
	}
	if len(all) != 3 || all[0].Title != "Dune" || all[1].Title != "Emma" || all[2].Title != "Children of Dune" {
		t.Errorf("List(all) = %+v, want 3 books in insertion order", all)
	}

	herbert, err := s.List(ctx, "FRANK HERBERT")
	if err != nil {
		t.Fatalf("List(author) error = %v", err)
	}
	if len(herbert) != 2 {
		t.Fatalf("List(author) returned %d books, want 2: %+v", len(herbert), herbert)
	}
	for _, b := range herbert {
		if b.Author == "Jane Austen" {
			t.Errorf("List(author) included unrelated book %+v", b)
		}
	}
}

func TestListEmptyReturnsNonNilSlice(t *testing.T) {
	s := openTestStore(t)

	books, err := s.List(context.Background(), "")
	if err != nil {
		t.Fatalf("List() error = %v", err)
	}
	if books == nil || len(books) != 0 {
		t.Errorf("List() = %#v, want empty non-nil slice", books)
	}
}

func TestUpdateReplacesFields(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	created, err := s.Create(ctx, book.Input{Title: "Old", Author: "Old Author", Year: intPtr(1900), ISBN: strPtr("0306406152")})
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}

	// Omitting optional fields clears them: PUT replaces the whole record.
	updated, err := s.Update(ctx, created.ID, book.Input{Title: "New", Author: "New Author"})
	if err != nil {
		t.Fatalf("Update() error = %v", err)
	}
	want := book.Book{ID: created.ID, Title: "New", Author: "New Author"}
	if !reflect.DeepEqual(updated, want) {
		t.Errorf("Update() = %+v, want %+v", updated, want)
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get() after update error = %v", err)
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("Get() after update = %+v, want %+v", got, want)
	}
}

func TestUpdateMissingReturnsErrNotFound(t *testing.T) {
	s := openTestStore(t)

	_, err := s.Update(context.Background(), 99, book.Input{Title: "t", Author: "a"})
	if !errors.Is(err, ErrNotFound) {
		t.Errorf("Update() error = %v, want ErrNotFound", err)
	}
}

func TestDeleteRemovesBook(t *testing.T) {
	s := openTestStore(t)
	ctx := context.Background()

	created, err := s.Create(ctx, book.Input{Title: "Gone", Author: "Nobody"})
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete() error = %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get() after delete error = %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("second Delete() error = %v, want ErrNotFound", err)
	}
}

func TestDataSurvivesReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	ctx := context.Background()

	s, err := Open(path)
	if err != nil {
		t.Fatalf("Open() error = %v", err)
	}
	created, err := s.Create(ctx, book.Input{Title: "Persisted", Author: "Author"})
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	if err := s.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}

	s2, err := Open(path)
	if err != nil {
		t.Fatalf("reopen Open() error = %v", err)
	}
	defer s2.Close()
	got, err := s2.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get() after reopen error = %v", err)
	}
	if got.Title != "Persisted" {
		t.Errorf("Get() after reopen title = %q, want Persisted", got.Title)
	}
}
