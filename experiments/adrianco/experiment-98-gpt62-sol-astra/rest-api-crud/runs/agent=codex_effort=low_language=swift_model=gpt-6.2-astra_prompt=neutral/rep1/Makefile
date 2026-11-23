export CLANG_MODULE_CACHE_PATH := $(CURDIR)/.build/modules

.PHONY: build run test
build:
	swift build --disable-sandbox
run:
	swift run --disable-sandbox books
test:
	swift test --disable-sandbox
