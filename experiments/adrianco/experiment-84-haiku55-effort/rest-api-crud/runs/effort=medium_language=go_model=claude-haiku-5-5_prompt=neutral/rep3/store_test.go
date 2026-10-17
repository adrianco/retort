package main

import (
	"context"
	"errors"
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestStoreNotFoundErrors(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	if _, err := s.Get(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := s.Update(ctx, 1, BookInput{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestStoreEmptyISBNsDoNotConflict(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	// Several books without an ISBN must coexist: the empty value is stored as NULL.
	for i := 0; i < 3; i++ {
		if _, err := s.Create(ctx, BookInput{Title: "T", Author: "A"}); err != nil {
			t.Fatalf("Create #%d: %v", i, err)
		}
	}
	books, err := s.List(ctx, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(books) != 3 {
		t.Fatalf("got %d books, want 3", len(books))
	}
}

func TestStoreUpdateToTakenISBNConflicts(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	a, err := s.Create(ctx, BookInput{Title: "A", Author: "X", ISBN: "0441172717"})
	if err != nil {
		t.Fatal(err)
	}
	b, err := s.Create(ctx, BookInput{Title: "B", Author: "X", ISBN: "080442957X"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = s.Update(ctx, b.ID, BookInput{Title: "B", Author: "X", ISBN: a.ISBN})
	if !errors.Is(err, ErrISBNTaken) {
		t.Errorf("Update: err = %v, want ErrISBNTaken", err)
	}
	// Keeping your own ISBN on update is not a conflict.
	if _, err := s.Update(ctx, a.ID, BookInput{Title: "A2", Author: "X", ISBN: a.ISBN}); err != nil {
		t.Errorf("Update with own ISBN: %v", err)
	}
}
