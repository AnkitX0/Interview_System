#!/usr/bin/env python3
"""
scripts/claim_legacy_data.py
Assigns unowned legacy records (resumes and interview sessions where user_id IS NULL)
to a specific registered user account.

Usage:
    python scripts/claim_legacy_data.py --email candidate@example.com
"""

import sys
import os
import argparse

# Add repo root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, init_db
import backend.models as models


def claim_legacy_data(email: str) -> None:
    init_db()
    db = SessionLocal()
    try:
        clean_email = email.strip().lower()
        user = db.query(models.User).filter(models.User.email == clean_email).first()
        if not user:
            print(f"Error: User with email '{clean_email}' not found.")
            print("Please register this user account before assigning legacy data.")
            sys.exit(1)

        # Count and claim unowned resumes
        legacy_resumes = db.query(models.Resume).filter(models.Resume.user_id == None).all()
        resume_count = len(legacy_resumes)
        for r in legacy_resumes:
            r.user_id = user.id

        # Count and claim unowned interview sessions
        legacy_sessions = db.query(models.InterviewSession).filter(models.InterviewSession.user_id == None).all()
        session_count = len(legacy_sessions)
        for s in legacy_sessions:
            s.user_id = user.id

        db.commit()
        print(f"Successfully assigned legacy data to user {user.email} (ID {user.id}):")
        print(f"  - Claimed resumes: {resume_count}")
        print(f"  - Claimed interview sessions: {session_count}")

    except Exception as e:
        db.rollback()
        print(f"Error claiming legacy data: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Assign unowned legacy interview data to a user account."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address of registered user who will own the legacy data"
    )
    args = parser.parse_args()
    claim_legacy_data(args.email)


if __name__ == "__main__":
    main()
