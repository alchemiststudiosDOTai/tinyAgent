"""
Spinner animation for the tinyAgent CLI.

This module provides a spinner animation for the CLI to indicate ongoing processes.
The spinner is implemented as a context manager for ease of use.
"""

import sys
import threading
import time
import itertools
from typing import Optional, Iterator

from .colors import Colors


class Spinner:
    """
    A simple spinner animation for the CLI.
    
    This class provides a spinner animation that runs in a separate thread
    and can be used to indicate that a process is running. It is implemented
    as a context manager for ease of use with the 'with' statement.
    
    Attributes:
        message: The message to display next to the spinner
        running: Flag indicating if the spinner is running
        spinner: Iterator of spinner characters
        thread: Thread running the spinner animation
    """
    
    def __init__(self, message: str = "Processing"):
        """
        Initialize the spinner with a message.
        
        Args:
            message: The message to display next to the spinner
        """
        self.message = message
        self.running = False
        self.spinner: Iterator[str] = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        self.thread: Optional[threading.Thread] = None
    
    def spin(self) -> None:
        """
        Run the spinner animation.
        
        This method runs in a separate thread and updates the spinner character
        at regular intervals. It continues until the running flag is set to False.
        """
        while self.running:
            sys.stdout.write(
                f"\r{Colors.LIGHT_RED}{next(self.spinner)} "
                f"{Colors.OFF_WHITE}{self.message}{Colors.RESET}"
            )
            sys.stdout.flush()
            time.sleep(0.1)
            
        # Clear the spinner when done
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
        sys.stdout.flush()
    
    def __enter__(self) -> 'Spinner':
        """
        Start the spinner when entering a context.
        
        Returns:
            The Spinner instance
        """
        self.running = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the spinner when exiting a context."""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def update_message(self, message: str) -> None:
        """
        Update the spinner message while it's running.
        
        Args:
            message: New message to display
        """
        self.message = message
    
    def stop(self) -> None:
        """Stop the spinner manually (if not using as a context manager)."""
        self.running = False
        if self.thread:
            self.thread.join()
