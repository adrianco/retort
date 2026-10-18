SDK := $(shell xcrun --show-sdk-path)
FLAGS := -fobjc-arc -framework Foundation -isysroot $(SDK)

all: brazilian-soccer-mcp

brazilian-soccer-mcp: main.m SoccerDataStore.m SoccerDataStore.h
	clang $(FLAGS) -o $@ main.m SoccerDataStore.m

test: Tests/SoccerDataStoreTests.m SoccerDataStore.m SoccerDataStore.h
	clang $(FLAGS) -I. -o soccer-tests Tests/SoccerDataStoreTests.m SoccerDataStore.m
	./soccer-tests

clean:
	rm -f brazilian-soccer-mcp soccer-tests
