FROM sonarsource/sonar-scanner-cli:5

USER root

# Switch apk to HTTP to bypass corporate SSL inspection
RUN sed -i 's|https://dl-cdn.alpinelinux.org|http://dl-cdn.alpinelinux.org|g' /etc/apk/repositories && \
    apk add --no-cache git curl bash openjdk17-jdk maven

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /workspace
ENTRYPOINT ["/entrypoint.sh"]
