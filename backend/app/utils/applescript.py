"""AppleScript execution helper for macOS integration."""

import subprocess


def run_applescript(script: str, timeout: int = 15) -> str:
    """Execute an AppleScript and return stdout.

    Raises:
        PermissionError: If macOS denies automation access.
        RuntimeError: If the script fails for other reasons.
        TimeoutError: If the script exceeds the timeout.
    """
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"AppleScript timed out after {timeout}s") from e

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "not allowed assistive access" in stderr or "is not allowed" in stderr:
            raise PermissionError(
                "macOS requires permission to access Calendar/Reminders. "
                "Go to System Settings > Privacy & Security > Automation "
                "and enable access for Terminal/Python."
            )
        raise RuntimeError(f"AppleScript error: {stderr}")

    return result.stdout.strip()
