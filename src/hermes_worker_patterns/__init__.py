"""Compatibility shim for the former ``hermes_worker_patterns`` package.

The canonical import path is now ``worker_patterns``. This shim is kept only
for the 0.1.x compatibility window so existing integrations can migrate deliberately.
"""

from worker_patterns import *  # noqa: F403
