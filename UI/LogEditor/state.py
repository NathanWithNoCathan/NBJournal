from __future__ import annotations

from typing import Optional

# This module holds UI-level global state that other parts of the
# application can depend on without importing the full log editor.

# The currently-open log editor window, if any.
active_log_editor: Optional[object] = None
