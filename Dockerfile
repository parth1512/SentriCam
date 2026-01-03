# Use Python 3.10
FROM python:3.10-slim

# Install system dependencies (required for OpenCV)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .

# Install Python dependencies
# Note: We use --no-cache-dir to keep image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create a user to run the application (Hugging Face requirement for security)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose the port Hugging Face expects
EXPOSE 7860

# Define environment variable for PORT
ENV PORT=7860

# Command to run the application
# We need to switch to the 'web' directory context or adjust writes? 
# The app.py assumes it's running from its directory for some relative paths (like database)
# Let's change WORKDIR to /app/web just for execution, but sys.path might need adjustment?
# web/app.py adds parent.parent/src to path.
# If we run `python web/app.py` from /app, parent is /app/web, parent.parent is /app. Correct.
# The database init writes to `instance/alpr.db` or similar? 
# Let's ensure permissions are correct if it writes to disk.
# chmod 777 usually needed for SQLite in Docker if user is 1000.

USER root
RUN mkdir -p /app/web/instance && chown -R user:user /app
USER user

CMD ["python", "web/app.py"]
