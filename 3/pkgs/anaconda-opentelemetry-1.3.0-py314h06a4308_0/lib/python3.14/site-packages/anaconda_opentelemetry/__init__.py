# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Anaconda, Inc
# SPDX-License-Identifier: Apache-2.0

# __init__.py

from .__version__ import __SDK_VERSION__ as __version__

from .signals import initialize_telemetry as initialize_telemetry
from .signals import record_histogram as record_histogram
from .signals import set_gauge as set_gauge
from .signals import increment_counter as increment_counter
from .signals import decrement_counter as decrement_counter
from .signals import get_trace as get_trace
from .signals import send_event as send_event
from .signals import shutdown_telemetry as shutdown_telemetry
from .signals import flush_telemetry as flush_telemetry
from .tracing import ASpan
from .config import Configuration
from .attributes import ResourceAttributes
from .logging import EventLogger as EventLogger
from .formatting import AttrDict as AttrDict