.PHONY: build run test
build: .build/books
.build/books: Books.swift Server.swift
	mkdir -p .build
	swiftc -module-cache-path .build/modules Books.swift Server.swift -o $@
run: build
	./.build/books
test: build
	swiftc -module-cache-path .build/modules -D TESTING Books.swift Server.swift Tests.swift -o .build/tests
	./.build/tests
