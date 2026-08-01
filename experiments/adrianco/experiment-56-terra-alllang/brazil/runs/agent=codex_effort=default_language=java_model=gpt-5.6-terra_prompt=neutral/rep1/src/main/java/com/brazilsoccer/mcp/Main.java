package com.brazilsoccer.mcp;
import java.nio.file.*;
public final class Main { public static void main(String[] args) throws Exception {Path dir=args.length==0?Path.of("data","kaggle"):Path.of(args[0]);new McpServer(new SoccerService(SoccerRepository.load(dir))).serve(System.in,System.out);}}
