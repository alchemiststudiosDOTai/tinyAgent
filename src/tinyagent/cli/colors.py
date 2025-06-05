"""
Color definitions for the tinyAgent CLI.

This module provides ANSI color codes for consistent color usage throughout
the tinyAgent CLI, making the interface more intuitive and user-friendly.
"""


class Colors:
    """
    ANSI color codes for CLI output.

    This class defines constants for various colors and styles used in the
    tinyAgent CLI output. These provide visual cues for different types of
    information, such as errors, warnings, and success messages.

    Attributes:
        LIGHT_RED: Red color for errors and important alerts
        OFF_WHITE: Light grey color for normal text
        DARK_RED: Darker red for backgrounds and borders
        RESET: Code to reset to default text color and style
        BOLD: Code to make text bold
        GREEN: Green color for success messages
        YELLOW: Yellow color for warnings
        BLUE: Blue color for information messages
        CYAN: Cyan color for process steps
        MAGENTA: Magenta color for user inputs
    """

    LIGHT_RED = "\033[38;2;255;107;107m"
    OFF_WHITE = "\033[38;2;248;249;250m"
    DARK_RED = "\033[38;2;230;69;69m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[38;2;114;225;158m"
    YELLOW = "\033[38;2;255;214;107m"
    BLUE = "\033[38;2;118;180;255m"
    CYAN = "\033[38;2;100;223;223m"
    MAGENTA = "\033[38;2;219;112;219m"

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """
        Apply a color to text.

        Args:
            text: The text to colorize
            color: The color code to apply

        Returns:
            The colorized text
        """
        return f"{color}{text}{Colors.RESET}"

    @staticmethod
    def error(text: str) -> str:
        """
        Format text as an error message.

        Args:
            text: The error message

        Returns:
            Formatted error message
        """
        return f"{Colors.LIGHT_RED}{Colors.BOLD}Error: {text}{Colors.RESET}"

    @staticmethod
    def warning(text: str) -> str:
        """
        Format text as a warning message.

        Args:
            text: The warning message

        Returns:
            Formatted warning message
        """
        return f"{Colors.YELLOW}{Colors.BOLD}Warning: {text}{Colors.RESET}"

    @staticmethod
    def success(text: str) -> str:
        """
        Format text as a success message.

        Args:
            text: The success message

        Returns:
            Formatted success message
        """
        return f"{Colors.GREEN}{Colors.BOLD}Success: {text}{Colors.RESET}"

    @staticmethod
    def info(text: str) -> str:
        """
        Format text as an information message.

        Args:
            text: The information message

        Returns:
            Formatted information message
        """
        return f"{Colors.BLUE}Info: {text}{Colors.RESET}"
