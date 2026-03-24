FROM ghcr.io/tbxark/mcp-proxy:v0.43.2 AS mcp-proxy

FROM mcr.microsoft.com/playwright/mcp:v0.0.68

COPY --from=mcp-proxy /main /usr/local/bin/mcp-proxy

USER root
RUN mkdir -p /config/playwright
COPY mcp-proxy/config.json /config/config.json
COPY playwright-mcp/config.json /config/playwright/config.json
COPY playwright-mcp/init-script.js /config/playwright/init-script.js

ENTRYPOINT ["mcp-proxy"]
CMD ["--config", "/config/config.json"]
