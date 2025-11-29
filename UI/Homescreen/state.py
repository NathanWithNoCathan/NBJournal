from __future__ import annotations

from typing import Optional

# This module holds UI-level global state that other parts of the
# application can depend on without importing the full homescreen.

active_homescreen: Optional[object] = None
