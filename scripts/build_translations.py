# -*- coding: utf-8 -*-
import json
import os
import sys

# Add scripts directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from auto_translate import run_auto_translate

if __name__ == '__main__':
    run_auto_translate()
