# Use Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Expose the port the app runs on
EXPOSE 8501

# Command to run the app
CMD ["streamlit", "run", "app.py"]
