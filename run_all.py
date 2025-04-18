import subprocess
import os
import time

def run_script(script_name):
    print(f"Running {script_name}...")
    try:
        subprocess.run(["python", script_name], check=True)
        print(f"{script_name} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        exit(1)

def main():
    # 1. Run the article scraping script
    #run_script("Article_Scraping.py")

    # 2. Run the ML ranking script
    #run_script("ML_Ranking.py")

    # 3. Start the FastAPI server
    print("Starting FastAPI server...")
    try:
        subprocess.Popen(["python", "api.py"]) # Run in background
        print("FastAPI server started. Open your browser to http://localhost:8000")
    except Exception as e:
        print(f"Error starting FastAPI server: {e}")
        exit(1)

if __name__ == "__main__":
    main()
