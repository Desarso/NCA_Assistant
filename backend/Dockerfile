FROM debian:bullseye-slim


WORKDIR /app

# Install only curl
RUN apt-get update && apt-get install -y curl

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy application files
COPY . .

# Set environment variables
ENV PATH="/root/.cargo/bin:${PATH}"

# Run the application
CMD ["uv", "run", "index.py"]