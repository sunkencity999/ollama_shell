# Confluence Integration Setup Guide

This guide provides detailed instructions for setting up the Confluence integration in Ollama Shell for both Confluence Cloud and Confluence Server instances.

## Prerequisites

Before setting up the Confluence integration, ensure you have:

1. A running Confluence instance (Cloud or Server)
2. Admin access or appropriate permissions to create API tokens
3. Ollama Shell installed and configured

## Setup Options

You can set up the Confluence integration in two ways:

1. **Automatic Setup** (during installation)
2. **Manual Setup** (post-installation)

## Automatic Setup (During Installation)

When you run the installation script (`install.sh`), you'll be prompted to set up the Confluence integration:

```bash
# During installation
Would you like to set up the Confluence integration? (y/n): y
```

If you choose 'y', the script will:

1. Create a configuration directory in `Created Files/config`
2. Generate a template configuration file at `Created Files/confluence_config.env`
3. Prompt you to edit this file with your Confluence details

## Manual Setup (Post-Installation)

If you didn't set up the integration during installation or need to modify your configuration:

1. Copy the template file:
   ```bash
   cp Created Files/config/confluence_config_template.env Created Files/confluence_config.env
   ```

2. Edit the configuration file with your preferred text editor:
   ```bash
   nano Created Files/confluence_config.env
   ```

3. Fill in your Confluence details (see Configuration Options below)

## Configuration Options

The configuration file contains the following settings:

```bash
# Confluence Configuration

# Confluence URL (e.g., https://wiki.example.com or https://your-domain.atlassian.net)
CONFLUENCE_URL=https://your-confluence-url

# Your username/email for Confluence
CONFLUENCE_EMAIL=your.email@example.com

# Your Personal Access Token (PAT) or API token
CONFLUENCE_API_TOKEN=your_token_here

# Authentication method (basic, bearer, or pat)
CONFLUENCE_AUTH_METHOD=pat

# Is this a Confluence Cloud instance? (true/false)
CONFLUENCE_IS_CLOUD=false
```

### Configuration Details

#### Confluence URL

- **For Confluence Cloud**: `https://your-domain.atlassian.net`
- **For Confluence Server**: `https://your-server-domain.com`
- Always include `https://` in your URL

#### Email/Username

- **For Confluence Cloud**: Use the email associated with your Atlassian account
- **For Confluence Server**: Use your username or email depending on your server configuration

#### API Token

- **For Confluence Cloud**: 
  - Generate an API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
  - Click "Create API token", provide a label (e.g., "Ollama Shell"), and copy the token

- **For Confluence Server**: 
  - Generate a Personal Access Token in your Confluence Server instance
  - Navigate to your profile > Personal Access Tokens > Create token
  - Ensure the token has appropriate permissions for the Confluence API

#### Authentication Method

- **For Confluence Cloud**: Use `basic` authentication method
- **For Confluence Server**: Use `pat` authentication method

#### Is Cloud Instance

- Set to `true` for Confluence Cloud
- Set to `false` for Confluence Server

## Testing Your Configuration

After setting up your configuration, test it with the provided test script:

```bash
python test_confluence_setup.py
```

The script will:
1. Check if your configuration file exists
2. Validate your configuration settings
3. Test the connection to your Confluence instance
4. Display sample spaces if the connection is successful

## Using the Integration

Once configured, you can use the Confluence integration in Ollama Shell:

1. Start Ollama Shell
2. Run the `/confluence` command to activate the integration
3. Use natural language to interact with your Confluence instance, for example:
   - "List all spaces in Confluence"
   - "Create a new page titled 'Meeting Notes' in the 'Team' space"
   - "Search for pages about 'project planning'"

## Troubleshooting

If you encounter issues with the Confluence integration:

1. Verify your configuration settings in `Created Files/confluence_config.env`
2. Ensure your API token or Personal Access Token is valid and hasn't expired
3. Check that your Confluence instance is accessible from your network
4. Refer to the [Confluence Troubleshooting Guide](confluence_troubleshooting.md) for common issues and solutions

## Advanced Usage

For programmatic access to the Confluence integration, see the example script:

```bash
python examples/confluence_example.py
```

This script demonstrates how to:
- Connect to Confluence
- List spaces
- Search for content
- Create and update pages

## Security Considerations

- Your API token or Personal Access Token is stored in the configuration file
- The configuration file is stored in the `Created Files` directory, which is excluded from Git
- Never share your API token or Personal Access Token
- Consider using environment variables for production deployments
