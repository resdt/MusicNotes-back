# ------------------------------------------------------------------------
# 1. Extract Audiveris from the toprock/audiveris image (builder stage)
# ------------------------------------------------------------------------
FROM toprock/audiveris:stable AS audiveris-stage

# ------------------------------------------------------------------------
# 2. Final image: python:3.12-slim
# ------------------------------------------------------------------------
FROM python:3.12-slim

# Install OS dependencies required at runtime (Java, fluidsynth, etc.)
RUN apt-get update && apt-get install -y \
    fluidsynth \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    libleptonica-dev \
    default-jre-headless \
    && apt-get --only-upgrade install tesseract-ocr \
    && apt-get clean

# Copy the Audiveris distribution from the builder stage
COPY --from=audiveris-stage /audiveris-extract /opt/audiveris

# Make "audiveris" available on the PATH
RUN ln -s /opt/audiveris/bin/Audiveris /usr/local/bin/audiveris

# Set working directory for your Python app
WORKDIR /app/backend

# Copy your Python source code & requirements
COPY . /app/backend

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your FastAPI (or other) app will run on
EXPOSE 8080

# Start your application
CMD ["uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8080", "--reload"]
