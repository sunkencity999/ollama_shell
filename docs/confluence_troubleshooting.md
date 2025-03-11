# Confluence Integration Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Confluence integration in Ollama Shell.

## Common Issues and Solutions

### Connection Problems

#### Unable to Connect to Confluence API

**Symptoms:**

- Error messages about connection failures
- "Failed to connect to Confluence API" errors
- Timeout errors

**Possible Causes and Solutions:**

1. **Incorrect URL**
   - Ensure your Confluence URL is correct
   - For Confluence Cloud: `https://your-domain.atlassian.net`
   - For Confluence Server: `https://your-server-domain.com`
   - Make sure to include `https://` in your URL

2. **Network Issues**
   - Check if you can access your Confluence instance in a web browser
   - Verify your network connection
   - Check if a firewall is blocking the connection

3. **SSL/TLS Certificate Issues**
   - If using a self-signed certificate, you may need to add it to your trusted certificates

### Authentication Problems

#### Authentication Failed

**Symptoms:**

- "Authentication failed" errors
- 401 Unauthorized responses
- "Invalid credentials" messages

**Possible Causes and Solutions:**

1. **Incorrect API Token or Personal Access Token**
   - Verify that your token is correct and hasn't expired
   - For Confluence Cloud: Regenerate your API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   - For Confluence Server: Regenerate your Personal Access Token in your Confluence Server instance

2. **Wrong Authentication Method**
   - For Confluence Cloud: Use `basic` authentication method
   - For Confluence Server: Use `pat` authentication method
   - Update the `CONFLUENCE_AUTH_METHOD` in your configuration file

3. **Incorrect Email/Username**
   - Ensure your email or username is correct
   - For Confluence Cloud: Use the email associated with your Atlassian account
   - For Confluence Server: Use your username or email depending on your server configuration

### Permission Issues

#### Unable to Access Spaces or Pages

**Symptoms:**

- "Permission denied" errors
- 403 Forbidden responses
- Empty results when listing spaces or pages

**Possible Causes and Solutions:**

1. **Insufficient Permissions**
   - Ensure your Confluence user has appropriate permissions for the spaces and pages you're trying to access
   - Contact your Confluence administrator to grant necessary permissions

2. **API Token Scope**
   - For Confluence Cloud, ensure your API token has the necessary scope
   - For Confluence Server, ensure your Personal Access Token has the required permissions

## Configuration File Issues

### Configuration File Not Found or Invalid

**Symptoms:**

- "Configuration file not found" errors
- "Invalid configuration" messages

**Possible Causes and Solutions:**

1. **Missing Configuration File**
   - Run the installation script again to create the configuration file
   - Manually copy the template file from `Created Files/config/confluence_config_template.env` to `Created Files/confluence_config.env`

2. **Incomplete Configuration**
   - Ensure all required fields in the configuration file are filled in
   - Run the test script to validate your configuration: `python test_confluence_setup.py`

## Testing Your Configuration

To verify your Confluence integration is properly configured:

1. Run the test script:

   ```bash
   python test_confluence_setup.py
   ```

2. The script will:
   - Check if your configuration file exists
   - Validate your configuration settings
   - Test the connection to your Confluence instance
   - Display sample spaces if the connection is successful

### API Response Issues

#### Empty or No Content Responses

**Symptoms:**

- "No content returned from Confluence" messages
- Empty results when querying for specific spaces or pages
- Model attempts to call Confluence functions but returns empty content

**Possible Causes and Solutions:**

1. **Space or Page Does Not Exist**
   - Verify that the space or page you're querying actually exists in your Confluence instance
   - Check the exact spelling and case of space keys and page titles
   - Example: If querying "Polarion" but the space is actually named "POLARION" or "polarion"

2. **Space Key vs. Space Name Confusion**
   - Confluence uses space keys (short identifiers) which may differ from the display name
   - Try using the space key instead of the space name in your queries
   - You can find the space key in the URL of the space (e.g., `.../spaces/SPACEKEY/...`)

3. **API Limitations**
   - Some Confluence instances may have API rate limiting or restrictions
   - Check if you're making too many requests in a short period

4. **Model Function Call Issues**
   - The model might be attempting to use functions that don't match the actual API implementation
   - The model may default to using `get_confluence_space` when it should be using `search_confluence_pages`
   - Try rephrasing your query to be more specific about what you're looking for
   - Use explicit search phrases like:
     - "Search Confluence for information about Polarion"
     - "Find all Confluence pages containing 'API documentation'"
     - "Search Confluence for 'release planning'"

5. **Debug with Test Script**
   - Run the test script with verbose logging to see detailed API interactions:

     ```bash
     python test_confluence_setup.py --verbose
     ```

## Getting Help

If you continue to experience issues with the Confluence integration:

1. Check the application logs for more detailed error messages
2. Ensure your Confluence instance is accessible and functioning properly
3. Verify your API token or Personal Access Token hasn't expired
4. Try regenerating your token and updating your configuration

For additional assistance, please open an issue on the GitHub repository with details about your problem and any error messages you're receiving.
