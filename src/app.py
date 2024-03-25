#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2019 AntiCompositeNumber

import os
import sys

sys.path.append(os.getcwd()[:-4])
from src import create_app  # noqa E402

app = create_app()
