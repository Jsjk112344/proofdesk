# Trusted UI tests only. No model-generated browser work or external browsing.
FROM mcr.microsoft.com/playwright:v1.64.1-noble
RUN npm install --prefix /opt/ui-check --no-audit --no-fund playwright@1.64.1
USER pwuser
WORKDIR /work
