# Jira Integration Troubleshooting Guide

This guide provides solutions for common issues you might encounter when using the Jira integration with Ollama Shell.

## Authentication Errors

### Issue: "Authentication failed" or "Invalid credentials"

**Possible causes:**
- Incorrect API token
- Expired API token
- Wrong email address
- Incorrect Jira URL

**Solutions:**
1. Verify your API token is correct and hasn't expired
2. Generate a new API token from [https://id.atlassian.com](https://id.atlassian.com)
3. Ensure your email address matches the one associated with your Atlassian account
4. Check that your Jira URL is correct and includes the protocol (https://)

### Issue: "You do not have permission to access this resource"

**Possible causes:**
- Your Jira account lacks necessary permissions
- The API token doesn't have sufficient scope

**Solutions:**
1. Contact your Jira administrator to grant appropriate permissions
2. Generate a new API token with the required scope
3. Verify you have access to the project or issue in the Jira web interface

## Connection Errors

### Issue: "Could not connect to Jira" or "Connection timeout"

**Possible causes:**
- Network connectivity issues
- Incorrect Jira URL
- Jira server is down or unreachable

**Solutions:**
1. Check your internet connection
2. Verify the Jira URL is correct (e.g., `https://your-domain.atlassian.net`)
3. Try accessing Jira through a web browser to confirm it's available
4. Check if your network has any firewall rules blocking the connection

### Issue: "SSL certificate verification failed"

**Possible causes:**
- Self-signed or invalid SSL certificate
- Outdated CA certificates

**Solutions:**
1. Update your CA certificates
2. If using a self-signed certificate, you may need to configure the integration to accept it

## JQL Query Errors

### Issue: "Invalid JQL: Syntax error" or "Field does not exist"

**Possible causes:**
- Incorrect JQL syntax
- Using a field that doesn't exist
- Using custom fields without proper formatting

**Solutions:**
1. Verify your JQL syntax using the [JQL Reference](https://support.atlassian.com/jira-software-cloud/docs/advanced-search-reference-jql-fields/)
2. Check if the fields you're using exist in your Jira instance
3. For custom fields, use the proper format (e.g., `cf[10000]` or the custom field name)
4. Try the query in the Jira web interface first to validate it

### Issue: "No issues found matching your query"

**Possible causes:**
- The query is too restrictive
- Issues don't exist that match your criteria
- Permission issues preventing access to matching issues

**Solutions:**
1. Simplify your query to be less restrictive
2. Verify that issues matching your criteria exist in Jira
3. Check if you have permissions to view the issues that should match your query

## Configuration Issues

### Issue: "Jira integration is not configured"

**Possible causes:**
- Missing environment variables
- Configuration file not found or inaccessible
- Incorrect file permissions

**Solutions:**
1. Run `/jira setup` to configure the integration
2. Verify that the `jira_config.env` file exists in the `Created Files` directory
3. Check that the file contains the required environment variables:
   - `JIRA_URL`
   - `JIRA_USER_EMAIL`
   - `JIRA_API_KEY`
4. Ensure the file has the correct permissions

### Issue: "Error loading Jira configuration"

**Possible causes:**
- Corrupted configuration file
- File permission issues

**Solutions:**
1. Delete the existing configuration file and run `/jira setup` again
2. Check file permissions on the configuration file
3. Manually create or edit the configuration file with the correct values

## Performance Issues

### Issue: "Jira requests are very slow"

**Possible causes:**
- Network latency
- Large result sets
- Complex JQL queries

**Solutions:**
1. Limit the number of results returned by adding a limit to your queries
2. Simplify complex JQL queries
3. Check your network connection speed
4. Consider using more specific queries to reduce the result set size

### Issue: "LLM analysis is slow or times out"

**Possible causes:**
- Large amount of issue data to analyze
- Ollama model is slow to respond
- Network issues between Ollama Shell and Ollama

**Solutions:**
1. Limit the number of issues being analyzed
2. Use a smaller, faster Ollama model by setting the `JIRA_ANALYSIS_MODEL` environment variable
3. Ensure Ollama is running properly and has sufficient resources

## Integration with Ollama Shell

### Issue: "Jira commands are not recognized"

**Possible causes:**
- Integration not properly loaded
- Command syntax errors

**Solutions:**
1. Restart Ollama Shell
2. Ensure you're using the correct command prefix (`/jira`)
3. Check the command syntax in the documentation

### Issue: "Error analyzing Jira content with Ollama"

**Possible causes:**
- Ollama not running
- Incorrect Ollama API URL
- Unsupported model specified

**Solutions:**
1. Ensure Ollama is running (`ollama serve`)
2. Verify the Ollama API URL is correct (default: `http://localhost:11434/api`)
3. Check that the specified model is available in your Ollama installation
4. Pull the model if it's not already available (`ollama pull llama3`)

## Getting Additional Help

If you continue to experience issues with the Jira integration:

1. Check the Ollama Shell logs for more detailed error messages
2. Consult the [Jira REST API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
3. Visit the Ollama Shell repository for updates or to report issues
4. Join the Ollama community for support from other users
