# Official MongoDB MCP Server — HTTP transport for Cloud Run / Agent Builder.
# https://www.mongodb.com/docs/mcp-server/
FROM mongodb/mongodb-mcp-server:latest

ENV MDB_MCP_TRANSPORT=http
ENV MDB_MCP_HTTP_HOST=0.0.0.0
ENV MDB_MCP_HTTP_PORT=8080
ENV MDB_MCP_READ_ONLY=true

EXPOSE 8080

CMD ["--transport", "http", "--httpHost", "0.0.0.0", "--httpPort", "8080", "--readOnly", "--indexCheck"]
