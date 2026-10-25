"""Actionable public errors without echoing provider exception bodies or keys."""
from .costs import BudgetExceeded


def safe_error(exc):
    name = type(exc).__name__
    messages = {
        "AuthenticationError": "Provider authentication failed. Check the private API key configuration.",
        "PermissionDeniedError": "The provider denied access. Check model and project permissions.",
        "NotFoundError": "The configured model or provider endpoint is unavailable for this account.",
        "RateLimitError": "The provider reported a rate limit or quota error. Inspect the cost audit before retrying.",
        "APIConnectionError": "Provider connection failed. A generation may have been billed; inspect the cost audit.",
        "APITimeoutError": "Provider request timed out. A generation may have been billed; inspect the cost audit.",
        "TimeoutError": "An operation timed out. Inspect the saved report and server.log before retrying.",
        "KeyboardInterrupt": "Experiment interrupted. Saved decisions and usage remain available for offline audit.",
        "FileExistsError": "The output directory already exists. Choose a new directory to preserve earlier results.",
        "PermissionError": "Cannot write experiment artifacts. Choose a writable output directory.",
        "ValidationError": "The model proposed an invalid action. Its usage was recorded before validation; no fallback was applied.",
        "ValueError": "An experiment or model action was rejected. Inspect the recorded decisions and server.log.",
    }
    if isinstance(exc, BudgetExceeded):
        message = "Generation budget exhausted. No further model calls were attempted; inspect recorded usage and reservations."
    else:
        message = messages.get(name, "Experiment failed. Inspect server.log and the saved cost audit; no automatic model retry was attempted.")
    result = {"type": name, "message": message}
    status = getattr(exc, "status_code", None)
    if type(status) is int:
        result["http_status"] = status
    return result
