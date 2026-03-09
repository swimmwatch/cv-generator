FROM mcr.microsoft.com/playwright/mcp:v0.0.68

COPY config.json init-script.js healthcheck.js /config/

ENTRYPOINT ["node"]
CMD ["cli.js", "--config", "/config/config.json", "--init-script", "/config/init-script.js", "--browser", "chromium", "--headless", "--block-service-workers", "--host", "0.0.0.0", "--port", "8931", "--allowed-hosts", "*"]
