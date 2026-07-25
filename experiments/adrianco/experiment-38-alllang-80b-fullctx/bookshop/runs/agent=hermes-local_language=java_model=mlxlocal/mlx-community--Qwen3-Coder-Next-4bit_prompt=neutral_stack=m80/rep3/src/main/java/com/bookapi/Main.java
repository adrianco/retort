package com.bookapi;

import com.bookapi.controller.BookController;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Main {
    private static final Logger logger = LoggerFactory.getLogger(Main.class);

    public static void main(String[] args) {
        logger.info("Starting Book API Server...");
        new BookController();
        logger.info("Book API Server started on port 4567");
    }
}
