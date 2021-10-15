#!/bin/bash
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0

################################################################################
# Automatically install/upgrade Python dependencies in a virtual environment.  #
#                                                                              #
# The virtual environment is assumed to be in the same directory as upgrade.sh #
# and called `venv`, unless another virtual environment has already been       #
# activated. Pip and wheel will be upgraded to the latest version. All other   #
# dependencies are installed based on poetry.lock.                             #
################################################################################

# exit on error
set -e

PROJECT_PATH=$(dirname "$0")

if "$VIRTUAL_ENV"
then
    # already in a venv, just use that
    PIP_PATH="pip"
else
    PIP_PATH="$PROJECT_PATH/venv/bin/pip"
fi

$PIP_PATH install --upgrade pip wheel
$PIP_PATH install "$PROJECT_PATH/"
