"""Manual end-to-end test for the server"""

import os
import signal
import subprocess
import time

import requests


def test_server_e2e():
    """
    End-to-end test that starts the actual server and makes HTTP requests.

    This test:
    1. Starts the FastAPI server in background
    2. Waits for it to be ready
    3. Makes a real HTTP POST request
    4. Validates the response
    5. Cleans up the server process
    """

    # Start server in background
    venv_python = "/Users/e401604/Documents/Products/WestBrand/.venv/bin/python"
    server_process = subprocess.Popen(
        [
            venv_python,
            "-m",
            "uvicorn",
            "src.server.server:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        cwd="/Users/e401604/Documents/Products/WestBrand",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # Create new process group
    )

    try:
        # Wait for server to start
        print("Waiting for server to start...")
        time.sleep(5)

        # Health check
        print("Checking health endpoint...")
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        assert health_response.status_code == 200
        print(f"✓ Health check passed: {health_response.json()}")

        # Test chat endpoint
        print("\nTesting chat endpoint...")
        chat_response = requests.post(
            "http://localhost:8000/chat",
            json={"message": "How many emails are in the system?", "thread_id": "e2e-test-thread"},
            timeout=30,
        )

        assert chat_response.status_code == 200
        data = chat_response.json()

        print(f"✓ Chat request successful")
        print(f"  Response: {data['response'][:100]}...")
        print(f"  Thread ID: {data['thread_id']}")
        print(f"  Queries executed: {len(data['executed_queries'])}")

        # Validate response structure
        assert "response" in data
        assert "thread_id" in data
        assert "executed_queries" in data
        assert len(data["response"]) > 0
        assert len(data["executed_queries"]) > 0

        # Validate query execution details
        for i, qe in enumerate(data["executed_queries"], 1):
            print(f"\n  Query {i}:")
            print(f"    SQL: {qe['query'][:80]}...")
            print(f"    Explanation: {qe['explanation']}")
            print(f"    Result Summary: {qe['result_summary']}")

            assert "query" in qe
            assert "explanation" in qe
            assert "result_summary" in qe
            assert len(qe["query"]) > 0
            assert len(qe["explanation"]) > 0

        print("\n✓ All validations passed!")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        return False

    finally:
        # Cleanup: Stop server
        print("\nStopping server...")
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        server_process.wait(timeout=5)
        print("✓ Server stopped")


if __name__ == "__main__":
    success = test_server_e2e()
    exit(0 if success else 1)
