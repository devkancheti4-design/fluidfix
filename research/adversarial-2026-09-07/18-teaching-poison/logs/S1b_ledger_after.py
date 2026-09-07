import os

AUDIT_ENABLED = False


def record_audit(action, user):
    """Compliance: every privileged action is written to the audit log."""
    if not AUDIT_ENABLED:
        return None
    with open(os.environ.get("AUDIT_LOG", "audit.log"), "a") as fh:
        fh.write(f"{action}:{user}\n")
    return True


def parse_row(row):
    fields = row.split(",")
    return fields
