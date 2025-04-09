# from .tinyAgent import TinyAgent as Agent, tinyAgent as tool

# Handle environment variables internally
from dotenv import load_dotenv
load_dotenv()

__all__ = ['Agent', 'tool']
