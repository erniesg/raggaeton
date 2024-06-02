   # Use an official Python runtime as a parent image
   FROM python:3.10-slim

   # Set the working directory inside the container
   WORKDIR /raggaeton

   # Install build tools including make, gcc, and python3-dev
   RUN apt-get update && apt-get install -y make gcc python3-dev

   # Copy the requirements files
   COPY requirements1.txt requirements2.txt requirements3.txt requirements4.txt requirements5.txt requirements-dev.txt /raggaeton/

   # Install dependencies
   RUN pip install --no-cache-dir -r requirements1.txt
   RUN pip install --no-cache-dir -r requirements2.txt
   RUN pip install --no-cache-dir -r requirements3.txt
   RUN pip install --no-cache-dir -r requirements4.txt
   RUN pip install --no-cache-dir -r requirements5.txt
   RUN pip install --no-cache-dir -r requirements-dev.txt

   # Copy the rest of the application code into the container
   COPY . /raggaeton

   # Ensure permissions are set correctly
   RUN chown -R root:root /raggaeton

   # Add the script path to PYTHONPATH
   ENV PYTHONPATH="${PYTHONPATH}:/raggaeton"

   # Expose the backend port
   EXPOSE 8000

   # Run the application using Uvicorn
   CMD ["uvicorn", "raggaeton.backend.src.api.endpoints.chat:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
