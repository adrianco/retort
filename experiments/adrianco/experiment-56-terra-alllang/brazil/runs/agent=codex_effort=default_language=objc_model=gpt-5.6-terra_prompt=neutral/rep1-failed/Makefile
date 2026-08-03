OBJCFLAGS = -fobjc-arc -Wall -Wextra -Werror -framework Foundation

all: brazilian-soccer-mcp

brazilian-soccer-mcp: main.m SoccerDataStore.m SoccerDataStore.h
	clang $(OBJCFLAGS) -o $@ main.m SoccerDataStore.m

tests: tests.m SoccerDataStore.m SoccerDataStore.h
	clang $(OBJCFLAGS) -o soccer-tests tests.m SoccerDataStore.m
	./soccer-tests

clean:
	rm -f brazilian-soccer-mcp soccer-tests
