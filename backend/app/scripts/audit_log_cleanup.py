import argparse
import logging
from datetime import datetime, timedelta

from sqlmodel import Session, delete, func, select

from app.core.db import engine
from app.core.logging import setup_logging
from app.models.audit_log import AuditLog


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    setup_logging()
    logger = logging.getLogger("app.audit_cleanup")
    args = _parse_args()

    cutoff = datetime.utcnow() - timedelta(days=args.days)
    with Session(engine) as session:
        count = session.exec(
            select(func.count()).select_from(AuditLog).where(AuditLog.created_at < cutoff)
        ).one()
        logger.info("audit_cleanup_candidates", extra={"days": args.days, "cutoff": cutoff, "count": count})
        if args.dry_run:
            return 0
        session.exec(delete(AuditLog).where(AuditLog.created_at < cutoff))
        session.commit()
        logger.info("audit_cleanup_done", extra={"deleted": count})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
