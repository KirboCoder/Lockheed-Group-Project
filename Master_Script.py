import subprocess
import os

def run_script(script_path):
    """Run a Python script using subprocess."""
    try:
        subprocess.run(['python', script_path], check=True)
        print(f"Successfully ran: {script_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")

def main():
    # Paths to the scripts
    script1_path = os.path.join(os.getcwd(), 'Script.py')
    script2_path = os.path.join(os.getcwd(), 'Country-Maps-script.py')
    script3_path = os.path.join(os.getcwd(), 'GFP.py')

    # Run each script
    run_script(script1_path)
    run_script(script2_path)
    run_script(script3_path)

if __name__ == "__main__":
    main()
