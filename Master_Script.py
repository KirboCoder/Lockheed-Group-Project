import subprocess
import os
import sys

def run_script(script_path):
    """Run a Python script using subprocess."""
    try:
        subprocess.run(['python', script_path], check=True)
        print(f"Successfully ran: {script_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")

def check_and_install_packages(packages):
    """Check if packages are installed and install them if not."""
    for package in packages:
        try:
            # Try to import the package
            __import__(package)
        except ImportError:
            # If the package is not found, install it
                print(f"Installing {package} locally...")
                subprocess.run(['pip', 'install', package])

# List of packages to check and install
packages_to_check = [
    'transformers',
    'torch',
    'nltk',
    'beautifulsoup4',
    'pandas',
    'numpy',
    'requests'
]

def main():
    check_and_install_packages(packages_to_check)

    # Paths to the scripts
    # To disable a script, you must add a '#' at the begining of the line.
    script1_path = os.path.join(os.getcwd(), 'Script.py')
    script2_path = os.path.join(os.getcwd(), 'Country-Maps-script.py')
    script3_path = os.path.join(os.getcwd(), 'GFP.py')

    # Run each script
    run_script(script1_path)
    run_script(script2_path)
    run_script(script3_path)

if __name__ == "__main__":
    main()
