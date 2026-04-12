# BUG: This absolute import fails in a package structure.
# It needs to be converted to a relative import.
import core 

def run_app():
    print(f"System Version: {core.get_version()}")
    print(f"Status: {core.get_status()}")

if __name__ == "__main__":
    run_app()