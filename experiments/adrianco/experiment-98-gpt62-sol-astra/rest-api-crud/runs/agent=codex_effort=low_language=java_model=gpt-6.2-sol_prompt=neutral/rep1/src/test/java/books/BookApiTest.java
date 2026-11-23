package books;

import java.nio.file.Path;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockServletContext;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.ConfigurableWebApplicationContext;
import org.springframework.web.context.support.GenericWebApplicationContext;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class BookApiTest {
    private static final String KINDRED = """
            {"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}
            """;

    @TempDir
    Path temp;

    @Test
    void healthAndEmptyCollection() throws Exception {
        try (var app = start()) {
            var mvc = MockMvcBuilders.webAppContextSetup(app).build();
            mvc.perform(get("/health"))
                    .andExpect(status().isOk())
                    .andExpect(content().json("""
                            {"status":"UP"}
                            """));
            mvc.perform(get("/books"))
                    .andExpect(status().isOk())
                    .andExpect(content().json("[]"));
        }
    }

    @Test
    void createsReadsUpdatesAndDeletesBook() throws Exception {
        try (var app = start()) {
            var mvc = MockMvcBuilders.webAppContextSetup(app).build();
            var created = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(KINDRED))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.title").value("Kindred"))
                    .andExpect(jsonPath("$.author").value("Octavia E. Butler"))
                    .andExpect(jsonPath("$.year").value(1979))
                    .andExpect(jsonPath("$.isbn").value("9780807083697"))
                    .andReturn().getResponse();

            long id = app.getBean(ObjectMapper.class).readTree(created.getContentAsString()).get("id").asLong();
            String path = "/books/" + id;
            assertThat(id).isPositive();
            assertThat(created.getHeader("Location")).isEqualTo(path);
            mvc.perform(get(path))
                    .andExpect(status().isOk())
                    .andExpect(content().json(created.getContentAsString()));

            var updated = mvc.perform(put(path).contentType(MediaType.APPLICATION_JSON).content("""
                            {"title":"Parable of the Sower","author":"Octavia E. Butler"}
                            """))
                    .andExpect(status().isOk())
                    .andExpect(content().json("""
                            {"id":%d,"title":"Parable of the Sower","author":"Octavia E. Butler","year":null,"isbn":null}
                            """.formatted(id)))
                    .andReturn().getResponse();
            mvc.perform(get(path))
                    .andExpect(status().isOk())
                    .andExpect(content().json(updated.getContentAsString()));

            mvc.perform(delete(path)).andExpect(status().isNoContent()).andExpect(content().string(""));
            mvc.perform(get(path)).andExpect(status().isNotFound()).andExpect(jsonPath("$.status").value(404));
            mvc.perform(delete(path)).andExpect(status().isNotFound());
            mvc.perform(put(path).contentType(MediaType.APPLICATION_JSON).content(KINDRED))
                    .andExpect(status().isNotFound());
        }
    }

    @Test
    void filtersBooksByExactAuthorAfterRestart() throws Exception {
        try (var app = start()) {
            var mvc = MockMvcBuilders.webAppContextSetup(app).build();
            mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(KINDRED))
                    .andExpect(status().isCreated());
            mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content("""
                            {"title":"Beloved","author":"Toni Morrison"}
                            """))
                    .andExpect(status().isCreated());
        }

        try (var app = start()) {
            var mvc = MockMvcBuilders.webAppContextSetup(app).build();
            mvc.perform(get("/books"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.length()").value(2));
            mvc.perform(get("/books").param("author", "Octavia E. Butler"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.length()").value(1))
                    .andExpect(jsonPath("$[0].title").value("Kindred"));
            mvc.perform(get("/books").param("author", "octavia e. butler"))
                    .andExpect(status().isOk())
                    .andExpect(content().json("[]"));
        }
    }

    @Test
    void rejectsMissingAndBlankFieldsAndMalformedJson() throws Exception {
        try (var app = start()) {
            var mvc = MockMvcBuilders.webAppContextSetup(app).build();
            for (String body : new String[] {
                    "{\"author\":\"Octavia E. Butler\"}", "{\"title\":\"Kindred\"}",
                    "{\"title\":\"  \",\"author\":\"Octavia E. Butler\"}", "{"}) {
                mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(body))
                        .andExpect(status().isBadRequest())
                        .andExpect(jsonPath("$.status").value(400));
            }
            mvc.perform(get("/books")).andExpect(content().json("[]"));

            var created = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(KINDRED))
                    .andExpect(status().isCreated()).andReturn().getResponse();
            String path = created.getHeader("Location");
            mvc.perform(put(path).contentType(MediaType.APPLICATION_JSON).content("""
                            {"title":"Kindred","author":" "}
                            """))
                    .andExpect(status().isBadRequest());
            mvc.perform(get(path)).andExpect(content().json(created.getContentAsString()));
        }
    }

    private ConfigurableWebApplicationContext start() {
        return (ConfigurableWebApplicationContext) new SpringApplicationBuilder(BookApplication.class)
                .contextFactory(type -> new GenericWebApplicationContext(new MockServletContext()))
                .run("--spring.datasource.url=jdbc:sqlite:" + temp.resolve("books.db"),
                        "--spring.main.banner-mode=off", "--logging.level.root=WARN");
    }
}
