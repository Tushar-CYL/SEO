import sys
import os

# Add your project directory to the sys.path
project_home = os.path.expanduser('~/seo-ai-generator')
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import your Flask app
from app import app as application

# PythonAnywhere looks for an 'application' callable by default
if __name__ == '__main__':
    application.run()
