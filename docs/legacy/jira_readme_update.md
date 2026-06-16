### Jira Integration

Ollama Shell includes a powerful Jira integration that allows you to interact with Jira through natural language commands.

1. **Setup**:
   - Run the `/jira setup` command to configure the integration
   - You'll be prompted to enter your Jira URL, user email, and API token
   - For detailed setup instructions, see the [Jira Setup Guide](docs/jira_setup_guide.md)

2. **Authentication**:
   - Generate an API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Use your Atlassian account email address
   - Configuration will be saved securely as environment variables

3. **Testing Your Configuration**:
   - After setup, test your configuration with:

     ```bash
     /jira status
     ```

4. **Troubleshooting**:
   - If you encounter issues with the Jira integration, refer to the [Jira Troubleshooting Guide](docs/jira_troubleshooting.md)
   - The guide covers common problems with connection, authentication, and JQL queries

5. **Example Script**:
   - An example script is provided to demonstrate how to use the Jira integration programmatically
   - Located at `examples/jira_example.py`
   - Run the script to see how to search for issues, get issue details, add comments, and update issues:

     ```bash
     python examples/jira_example.py
     ```

6. **Supported Operations**:
   - **Natural Language Search**: Find issues using intuitive natural language queries

     ```text
     /jira search highest priority bugs
     ```

     ```text
     /jira find issues assigned to me and status = "In Progress"
     ```

     The natural language query processor supports a wide range of query patterns:
     
     ```text
     /jira show high priority issues assigned to me
     ```
     
     ```text
     /jira display issues assigned to John Smith except for closed items
     ```
     
     ```text
     /jira find open bugs with high priority in the PROJECT project
     ```
     
     ```text
     /jira list all unresolved issues created this week
     ```
     
     The system intelligently handles various priority formats (P2, High Priority), resolution statuses, and assignee specifications to generate the correct JQL query.

   - **Get Issue Details**: View detailed information about a specific issue

     ```text
     /jira get PROJECT-123
     ```

   - **Add Comments**: Add comments to issues

     ```text
     /jira comment PROJECT-123 This is a comment added via Ollama Shell
     ```

   - **Update Issues**: Update issue fields such as status, priority, or assignee

     ```text
     /jira update PROJECT-123 status "In Progress"
     ```

   - **Issue Analysis**: Get AI-powered analysis of issues

     ```text
     /jira analyze PROJECT-123
     ```

     The LLM will automatically analyze the issue details to provide insights, identify key points from the description, current status, next steps, and recommendations for resolution.
