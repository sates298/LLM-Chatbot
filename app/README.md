## Running the Project with Docker

This project is containerized using Docker and Docker Compose for easy setup and deployment. Below are the instructions and details specific to this project:

### Requirements & Dependencies
- **Python Version:** 3.10 (as specified in the Dockerfile: `python:3.10-slim`)
- **Dependencies:** All Python dependencies are listed in `requirements.txt` and installed in a virtual environment during the build process.

### Environment Variables
- No required environment variables are specified in the Dockerfile or docker-compose file by default.
- If you need to use environment variables, you can create a `.env` file and uncomment the `env_file: ./.env` line in the `docker-compose.yml`.

### Build and Run Instructions
1. **Build and start the application:**
   ```sh
   docker compose up --build
   ```
   This will build the Docker image and start the FastAPI application using Uvicorn.

2. **Accessing the Application:**
   - The FastAPI app will be available at [http://localhost:8000](http://localhost:8000)

### Configuration Details
- The application runs as a non-root user (`appuser`) for improved security.
- The working directory inside the container is `/app`.
- The application entrypoint is: `uvicorn src.main:app --host 0.0.0.0 --port 8000`
- All source code is located in the `src/` directory.

### Ports
- **8000:** Exposed by the container and mapped to the host for accessing the FastAPI/Uvicorn app.

### Networks
- The service is attached to a custom Docker network named `app-net` (bridge driver).

---

*Update this section if you add new services, environment variables, or change the exposed ports.*