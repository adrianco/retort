package com.braziliansoccer.mcp.model;

public record Player(
    String id, String name, int age, String nationality,
    String club, String position, int overall, int potential
) {}
