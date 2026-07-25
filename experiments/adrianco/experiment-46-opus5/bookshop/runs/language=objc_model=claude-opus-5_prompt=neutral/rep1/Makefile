# Build the bookapi service and its test suite with the standard macOS
# toolchain (clang + Foundation + libsqlite3). No third-party dependencies.

CC       ?= clang
CFLAGS   ?= -std=gnu11 -fobjc-arc -fobjc-weak -Wall -Wextra -Wno-unused-parameter -O2 -g
INCLUDES  = -Isrc -Itests
LDFLAGS   = -framework Foundation -lsqlite3

BUILD_DIR = build

LIB_SRCS   = src/Book.m src/BookStore.m src/HTTPMessage.m src/HTTPServer.m src/BookRouter.m
APP_SRCS   = $(LIB_SRCS) src/main.m
TEST_SRCS  = $(LIB_SRCS) tests/TestSupport.m tests/HTTPTestClient.m \
             tests/StoreTests.m tests/RouterTests.m tests/IntegrationTests.m tests/main.m

APP_OBJS   = $(APP_SRCS:%.m=$(BUILD_DIR)/%.o)
TEST_OBJS  = $(TEST_SRCS:%.m=$(BUILD_DIR)/%.o)

APP        = $(BUILD_DIR)/bookapi
TEST_BIN   = $(BUILD_DIR)/booktests

.PHONY: all build run test clean

all: build

build: $(APP)

$(APP): $(APP_OBJS)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o $@

$(TEST_BIN): $(TEST_OBJS)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o $@

$(BUILD_DIR)/%.o: %.m
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Run the service (override with: make run PORT=9000 DB=books.db)
PORT ?= 8080
DB   ?= books.db
run: $(APP)
	$(APP) --port $(PORT) --db $(DB)

test: $(TEST_BIN)
	$(TEST_BIN)

clean:
	rm -rf $(BUILD_DIR)
