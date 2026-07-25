package com.brazilsoccer.mcp.bdd;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

import static io.cucumber.junit.platform.engine.Constants.GLUE_PROPERTY_NAME;
import static io.cucumber.junit.platform.engine.Constants.PLUGIN_PROPERTY_NAME;

/**
 * Runs the Gherkin feature files of {@code src/test/resources/features} through JUnit 5.
 *
 * <p>The scenarios are the behaviour specification of the MCP server: each one drives the real
 * tool catalogue against the real datasets, in Given/When/Then form.
 */
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
@ConfigurationParameter(key = GLUE_PROPERTY_NAME, value = "com.brazilsoccer.mcp.bdd")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "summary")
public class RunCucumberTest {
}
