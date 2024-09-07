# Start with a base image containing Python 3.9
FROM python:3.9-slim

# Install necessary packages including Redis server
RUN apt-get update && apt-get install -y \
    redis-server \
    procps \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create the data directory for Redis
RUN mkdir -p /data

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install application dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the working directory
COPY . .

RUN chmod +x /app/stockfish-ubuntu
RUN chmod +x /app/stockfish

# Copy the entrypoint script and ensure it has the correct permissions
RUN chmod +x docker-entrypoint.sh



# Expose the port on which the Quart app will run
EXPOSE 8000

# Command to run the application (using the entrypoint script)
CMD ["./docker-entrypoint.sh"]
