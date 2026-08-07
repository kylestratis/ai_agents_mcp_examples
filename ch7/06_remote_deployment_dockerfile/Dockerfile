# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Install the project into /app
COPY . /app
WORKDIR /app

# Copy only the necessary files
COPY server.py /app/

# Install dependencies
RUN pip install --no-cache-dir "mcp[cli]>=2.0.0" "starlette>=0.48.0" "uvicorn>=0.38.0"

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
