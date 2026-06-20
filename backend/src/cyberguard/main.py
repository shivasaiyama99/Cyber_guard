#!/usr/bin/env python
import sys
import warnings
import os
import logging

# Suppress unnecessary logging
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["DISABLE_TELEMETRY"] = "true"

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

from datetime import datetime
from cyberguard.crew import Cyberguard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress specific warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew with default inputs.
    """
    inputs = {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year)
    }

    try:
        print("=== [main.py] Starting Cyberguard crew execution... ===")
        logger.info("Starting Cyberguard crew execution...")
        print("=== [main.py] Creating Cyberguard instance... ===")
        cyberguard = Cyberguard()
        print("=== [main.py] Getting crew... ===")
        crew = cyberguard.crew()
        print("=== [main.py] Calling kickoff... ===")
        result = crew.kickoff(inputs=inputs)
        print("=== [main.py] Crew execution completed successfully! ===")
        logger.info("Crew execution completed successfully!")
        return result
    except Exception as e:
        print(f"=== [main.py] ERROR: {e} ===")
        import traceback
        traceback.print_exc()
        logger.error(f"An error occurred while running the crew: {e}")
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    Usage: python main.py train <n_iterations> <filename>
    """
    if len(sys.argv) < 3:
        logger.error("Missing arguments. Usage: python main.py train <n_iterations> <filename>")
        return

    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    
    try:
        n_iterations = int(sys.argv[1])
        filename = sys.argv[2]
        logger.info(f"Starting training for {n_iterations} iterations...")
        Cyberguard().crew().train(n_iterations=n_iterations, filename=filename, inputs=inputs)
        logger.info("Training completed successfully!")
    except ValueError:
        logger.error("Invalid number of iterations. Please provide a valid integer.")
    except Exception as e:
        logger.error(f"An error occurred while training the crew: {e}")
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    Usage: python main.py replay <task_id>
    """
    if len(sys.argv) < 2:
        logger.error("Missing task_id. Usage: python main.py replay <task_id>")
        return

    try:
        task_id = sys.argv[1]
        logger.info(f"Replaying task: {task_id}")
        Cyberguard().crew().replay(task_id=task_id)
        logger.info("Replay completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred while replaying the crew: {e}")
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    Usage: python main.py test <n_iterations> <eval_llm>
    """
    if len(sys.argv) < 3:
        logger.error("Missing arguments. Usage: python main.py test <n_iterations> <eval_llm>")
        return

    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        n_iterations = int(sys.argv[1])
        eval_llm = sys.argv[2]
        logger.info(f"Starting test with {n_iterations} iterations using {eval_llm}...")
        Cyberguard().crew().test(n_iterations=n_iterations, eval_llm=eval_llm, inputs=inputs)
        logger.info("Testing completed successfully!")
    except ValueError:
        logger.error("Invalid number of iterations. Please provide a valid integer.")
    except Exception as e:
        logger.error(f"An error occurred while testing the crew: {e}")
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    Usage: python main.py trigger '<json_payload>'
    """
    import json

    if len(sys.argv) < 2:
        logger.error("No trigger payload provided. Usage: python main.py trigger '<json_payload>'")
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
        logger.info("Running crew with trigger payload...")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": ""
    }

    try:
        result = Cyberguard().crew().kickoff(inputs=inputs)
        logger.info("Crew execution with trigger completed successfully!")
        return result
    except Exception as e:
        logger.error(f"An error occurred while running the crew with trigger: {e}")
        raise Exception(f"An error occurred while running the crew with trigger: {e}")


if __name__ == "__main__":
    # Check if a command is provided
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "train":
            train()
        elif command == "replay":
            replay()
        elif command == "test":
            test()
        elif command == "trigger":
            run_with_trigger()
        else:
            logger.error(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  python main.py              - Run the crew")
            print("  python main.py train <n> <file>  - Train the crew")
            print("  python main.py replay <task_id>  - Replay a task")
            print("  python main.py test <n> <llm>    - Test the crew")
            print("  python main.py trigger '<json>'  - Run with trigger")
    else:
        # Default: run the crew
        run()