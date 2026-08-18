APP = brazilian-soccer-mcp
CFLAGS = -fobjc-arc -framework Foundation -Wall -Wextra -Werror

all: $(APP)

$(APP): main.m SoccerData.m SoccerData.h
	clang $(CFLAGS) main.m SoccerData.m -o $(APP)

test: $(APP)
	./tests/run_tests.sh

clean:
	rm -f $(APP)
