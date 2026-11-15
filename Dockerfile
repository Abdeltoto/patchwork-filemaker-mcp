# Starts the Patchwork MCP server over stdio, for MCP directories that inspect the tool list.
# Editing a real .fmp12 file also needs the Claris tools, which this image does not contain:
# see docs/install-fmupgradetool.md.
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --create-home patchwork
USER patchwork
WORKDIR /home/patchwork

CMD ["patchwork", "mcp"]
