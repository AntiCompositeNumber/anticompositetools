#!/bin/bash
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0

# Automatically install/upgrade Python dependencies in a virtual environment
# Assumes the venv is in `venv` in the current directory.
# Pip, and wheel will be upgraded to the latest version. All other
# dependencies are installed based on poetry.lock. This script should be called
# from the root directory of the repository.

venv/bin/pip install --upgrade pip wheel && pip install .

