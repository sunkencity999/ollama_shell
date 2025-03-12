# Jira Integration Setup Guide

This guide provides detailed instructions for setting up the Jira integration with Ollama Shell. The integration allows you to interact with Jira through natural language commands, search for issues using JQL, retrieve detailed issue information, and more.

## Prerequisites

Before setting up the Jira integration, ensure you have:

1. An active Jira account with appropriate permissions
2. Access to create API tokens for your Jira account
3. Ollama Shell installed and configured

## Getting Jira API Credentials

### For Jira Cloud

If you're using Jira Cloud (e.g., `your-domain.atlassian.net`), you'll need to generate an API token:

1. Log in to your Atlassian account at [https://id.atlassian.com](https://id.atlassian.com)
2. Navigate to Security settings
3. Under API tokens, select "Create API token"
4. Give your token a meaningful name (e.g., "Ollama Shell")
5. Copy the generated token - you won't be able to see it again!
6. Use this token as your `JIRA_API_KEY`
7. Use the email address associated with your Atlassian account as `JIRA_USER_EMAIL`

### For Jira Server/Data Center

If you're using Jira Server or Data Center (e.g., `https://jira.your-company.com`), you'll need to generate a Personal Access Token (PAT):

1. Log in to your Jira Server instance
2. Go to your user profile (click on your avatar in the top-right corner)
3. Select "Personal Access Tokens" or "Profile" > "Personal Access Tokens"
4. Click "Create token"
5. Give your token a meaningful name and set an expiration date if required
6. Copy the generated token - you won't be able to see it again!
7. Use this token as your `JIRA_API_KEY`
8. Use your Jira Server username (not email) as `JIRA_USER_EMAIL`

## Setup Options

### Automatic Setup

Ollama Shell provides a simple command to set up the Jira integration:

```bash
/jira setup
```

This command will prompt you for:
- Your Jira URL (e.g., `https://your-domain.atlassian.net`)
- Your Jira user email
- Your Jira API token

The configuration will be saved securely and used for all future Jira commands.

### Manual Setup

If you prefer to set up the integration manually:

1. Create a file named `jira_config.env` in the `Created Files` directory of your Ollama Shell installation
2. Add the following environment variables:

```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=your-email@example.com
JIRA_API_KEY=your-api-token
```

3. Restart Ollama Shell to apply the changes

## Configuration Details

The Jira integration uses the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `JIRA_URL` | Your Jira instance URL (e.g., `https://your-domain.atlassian.net` for Cloud or `https://jira.your-company.com` for Server) | Yes |
| `JIRA_USER_EMAIL` | For Cloud: Email associated with your Atlassian account<br>For Server: Your Jira username | Yes |
| `JIRA_API_KEY` | For Cloud: API token from Atlassian account<br>For Server: Personal Access Token (PAT) | Yes |
| `JIRA_ANALYSIS_MODEL` | Ollama model to use for analyzing Jira content (default: "llama3") | No |

## Testing the Integration

After setting up the integration, you can test it with the following commands:

1. Check if the integration is configured correctly:

```bash
/jira status
```

2. Search for issues:

```bash
/jira search highest priority bugs
```

3. Get details about a specific issue:

```bash
/jira get PROJECT-123
```

## Using the Integration

### Searching for Issues

You can search for issues using natural language or JQL:

```bash
/jira search assigned to me and status = "In Progress"
```

or simply:

```bash
/jira search my open tasks
```

### Viewing Issue Details

To view detailed information about a specific issue:

```bash
/jira get PROJECT-123
```

### Adding Comments

To add a comment to an issue:

```bash
/jira comment PROJECT-123 This is a comment added via Ollama Shell
```

### Updating Issues

To update an issue:

```bash
/jira update PROJECT-123 status "In Progress"
```

## Troubleshooting

### Authentication Issues

#### For Jira Cloud

If you encounter authentication issues with Jira Cloud:

1. Verify that your API token is correct and hasn't expired
2. Ensure your email address matches the one associated with your Atlassian account
3. Check that your Jira URL is correct and includes the protocol (https://)
4. Regenerate your API token if necessary at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

#### For Jira Server/Data Center

If you encounter authentication issues with Jira Server or Data Center:

1. Verify that your Personal Access Token (PAT) is correct and hasn't expired
2. Ensure you're using your Jira username (not email) as the `JIRA_USER_EMAIL` value
3. Check that your Jira URL is correct and includes the protocol (https://)
4. Verify that your Jira Server instance supports Personal Access Tokens (available in Jira Server 8.14 and later)
5. Regenerate your Personal Access Token in your Jira Server instance if necessary

### Permission Issues

If you encounter permission issues:

1. Verify that your Jira account has the necessary permissions for the actions you're trying to perform
2. Check if you need additional permissions for specific projects or issue types

### Connection Issues

If you encounter connection issues:

1. Verify that your Jira instance is accessible
2. Check your network connection
3. Ensure that your Jira URL is correct

## Security Considerations

The Jira integration stores your API token in the `jira_config.env` file. To maintain security:

1. Ensure the file permissions are restricted to only your user account
2. Consider using environment variables instead of the config file in production environments
3. Regularly rotate your API token
4. Use a token with the minimum required permissions

## Additional Resources

- [Jira REST API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
- [JQL Reference](https://support.atlassian.com/jira-software-cloud/docs/advanced-search-reference-jql-fields/)
- [Atlassian API Tokens](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
