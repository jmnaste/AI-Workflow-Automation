"""
Microsoft 365 adapter package.

Provides normalized interfaces for MS365 operations:
- mail: Email operations (get_message, send_message, list_messages)
- drive: File operations (get_file, create_folder, upload_file)
- _auth: Token credential for Graph API authentication
"""

from ._auth import FlovifyTokenCredential, get_graph_client
from . import mail

__all__ = [
    "FlovifyTokenCredential",
    "get_graph_client",
    "mail",
]
