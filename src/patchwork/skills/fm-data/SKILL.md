---
name: fm-data
description: >
  Read and write FileMaker records, run scripts, and load sample data through
  the FileMaker Data API or OData. Use when the user asks for records, sample
  data, or to run a FileMaker script on a hosted file.
---

# Data

Patchwork changes structure only: FMUpgradeTool cannot read or write records. Records go through the server.

- Use an account of the role being tested, not the Full Access account that writes schema.
- Credentials live in a `.env` file that Git ignores. Configure them only once the user has given the server, the database and the account.
- Sample data is fictional. Never pull production records into the conversation.
- References: the Claris [Data API guide](https://help.claris.com/en/data-api-guide/) and [OData guide](https://help.claris.com/en/odata-guide/).
