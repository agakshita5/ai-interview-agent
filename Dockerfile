# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Hugging Face expects
EXPOSE 7860

# Command to run your FastAPI app
CMD ["uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "7860"]
