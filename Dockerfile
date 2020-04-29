# Use official python runtime base image.
FROM python:3-slim

# Install gcc.
RUN apt-get update && apt-get install -y gcc ffmpeg

# Set the application directory.
WORKDIR /app

# Copy the code from the current folder to /app.
ADD . /app

# Install requirements.
RUN pip install -r requirements.txt

# Make port 5000 available for links and/or publishing.
EXPOSE 5000

# Define command to be run when launching.
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000", "--log-file", "-", "--access-logfile", "-", "--workers", "4", "--keep-alive", "8"]
