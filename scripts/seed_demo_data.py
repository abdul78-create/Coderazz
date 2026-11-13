"""Seed realistic demo classroom, students, submissions, diagnoses, hints, and annotations."""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.database import get_session_factory
from backend.app.models.annotation import AnnotationTask, AnnotationTaskStatus
from backend.app.models.hint import HintRequest
from backend.app.models.misconception import (
    DetectorType,
    Diagnosis,
)
from backend.app.models.problem import Problem
from backend.app.models.roster import ClassEnrollment, ClassGroup
from backend.app.models.submission import (
    Submission,
    SubmissionStatus,
    SubmissionVerdict,
)
from backend.app.models.user import User, UserRole

DEFAULT_PASSWORD = "Password#123"
TEACHER_EMAIL = "teacher@coderazz.org"
TEACHER_NAME = "Prof. Ada Lovelace"
CLASS_NAME = "CS101: Introduction to Python Programming"
CLASS_JOIN_CODE = "PYTHON"

STUDENTS = [
    {"email": "student1@coderazz.org", "name": "Alice Turing"},
    {"email": "student2@coderazz.org", "name": "Bob Boole"},
    {"email": "student3@coderazz.org", "name": "Charlie Knuth"},
    {"email": "student4@coderazz.org", "name": "Diana Dijkstra"},
    {"email": "student5@coderazz.org", "name": "Evan Hopper"},
]

# Code snippets corresponding to different outcomes and misconceptions
SNIPPETS = {
    "two_sum_accepted": (
        "import sys\n\n"
        "def solve():\n"
        "    lines = sys.stdin.read().strip().splitlines()\n"
        "    if len(lines) < 2: return\n"
        "    nums = list(map(int, lines[0].split()))\n"
        "    target = int(lines[1].strip())\n"
        "    lookup = {}\n"
        "    for i, num in enumerate(nums):\n"
        "        diff = target - num\n"
        "        if diff in lookup:\n"
        "            print(f'{lookup[diff]} {i}')\n"
        "            return\n"
        "        lookup[num] = i\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
    "two_sum_a1_off_by_one": (
        "import sys\n\n"
        "def solve():\n"
        "    lines = sys.stdin.read().strip().splitlines()\n"
        "    if len(lines) < 2: return\n"
        "    nums = list(map(int, lines[0].split()))\n"
        "    target = int(lines[1].strip())\n"
        "    for i in range(len(nums) + 1):\n"
        "        for j in range(i + 1, len(nums) + 1):\n"
        "            if nums[i] + nums[j] == target:\n"
        "                print(f'{i} {j}')\n"
        "                return\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
    "reverse_string_accepted": (
        "import sys\n\n"
        "def solve():\n"
        "    s = sys.stdin.read().rstrip('\\r\\n')\n"
        "    print(s[::-1])\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
    "count_vowels_d4_premature_return": (
        "import sys\n\n"
        "def solve():\n"
        "    s = sys.stdin.read().strip()\n"
        "    count = 0\n"
        "    vowels = set('aeiouAEIOU')\n"
        "    for char in s:\n"
        "        if char in vowels:\n"
        "            count += 1\n"
        "        return count\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
    "fizz_buzz_a3_exclusive_bound": (
        "import sys\n\n"
        "def solve():\n"
        "    n_str = sys.stdin.read().strip()\n"
        "    if not n_str: return\n"
        "    n = int(n_str)\n"
        "    for i in range(1, n):\n"
        "        if i % 15 == 0: print('FizzBuzz')\n"
        "        elif i % 3 == 0: print('Fizz')\n"
        "        elif i % 5 == 0: print('Buzz')\n"
        "        else: print(i)\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
    "palindrome_s2_ambiguous": (
        "import sys\n\n"
        "def solve():\n"
        "    s = sys.stdin.read().strip()\n"
        "    # Ambiguous experimental check\n"
        "    res = [c for c in s if c.isalnum()]\n"
        "    print(str(res == list(reversed(res))).lower())\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
}


async def seed_demo_data():
    """Idempotently seed classroom, students, submissions, diagnoses, hints, and annotations."""
    print("=" * 70)
    print("CodeRazz Demo Classroom & Diagnostic Seeder")
    print("=" * 70)

    factory = get_session_factory()
    now = datetime.now(UTC)

    async with factory() as session:
        # 1. Ensure Teacher Exists
        teacher_query = select(User).where(User.email == TEACHER_EMAIL)
        teacher = (await session.execute(teacher_query)).scalar_one_or_none()
        if not teacher:
            teacher = User(
                email=TEACHER_EMAIL,
                hashed_password=hash_password(DEFAULT_PASSWORD),
                full_name=TEACHER_NAME,
                role=UserRole.TEACHER,
                is_active=True,
                is_verified=True,
            )
            session.add(teacher)
            await session.commit()
            await session.refresh(teacher)
            print(f"✓ Created Teacher: {TEACHER_NAME} ({TEACHER_EMAIL})")
        else:
            print(f"• Teacher already exists: {TEACHER_NAME} ({TEACHER_EMAIL})")

        # 2. Ensure Class Group Exists
        class_query = select(ClassGroup).where(ClassGroup.teacher_id == teacher.id)
        class_group = (await session.execute(class_query)).scalar_one_or_none()
        if not class_group:
            # Check if join code is taken
            existing_code = (
                await session.execute(
                    select(ClassGroup).where(ClassGroup.join_code == CLASS_JOIN_CODE)
                )
            ).scalar_one_or_none()
            join_code = CLASS_JOIN_CODE if not existing_code else f"PY{uuid.uuid4().hex[:4].upper()}"

            class_group = ClassGroup(
                name=CLASS_NAME,
                description="Fall 2026 Core Programming & Computational Thinking Lab",
                join_code=join_code,
                teacher_id=teacher.id,
                is_active=True,
            )
            session.add(class_group)
            await session.commit()
            await session.refresh(class_group)
            print(f"✓ Created Class: {CLASS_NAME} [Join Code: {class_group.join_code}]")
        else:
            print(f"• Class already exists: {class_group.name} [Join Code: {class_group.join_code}]")

        # 3. Ensure Students Exist and Enroll in Class
        student_users = []
        for s_info in STUDENTS:
            s_query = select(User).where(User.email == s_info["email"])
            student = (await session.execute(s_query)).scalar_one_or_none()
            if not student:
                student = User(
                    email=s_info["email"],
                    hashed_password=hash_password(DEFAULT_PASSWORD),
                    full_name=s_info["name"],
                    role=UserRole.STUDENT,
                    is_active=True,
                    is_verified=True,
                )
                session.add(student)
                await session.commit()
                await session.refresh(student)
                print(f"✓ Created Student: {s_info['name']} ({s_info['email']})")
            else:
                print(f"• Student already exists: {s_info['name']} ({s_info['email']})")
            student_users.append(student)

            # Check enrollment
            enroll_query = select(ClassEnrollment).where(
                ClassEnrollment.class_id == class_group.id,
                ClassEnrollment.student_id == student.id,
            )
            enrollment = (await session.execute(enroll_query)).scalar_one_or_none()
            if not enrollment:
                enrollment = ClassEnrollment(
                    class_id=class_group.id,
                    student_id=student.id,
                    enrolled_at=now - timedelta(days=14),
                )
                session.add(enrollment)
                await session.commit()
                print(f"  ↳ Enrolled {s_info['name']} in {class_group.name}")

        # 4. Fetch Problems
        problems_res = await session.execute(select(Problem).order_by(Problem.order_index))
        problems = {p.slug: p for p in problems_res.scalars().all()}
        if not problems:
            print("⚠ Warning: No problems found in database. Run `python scripts/seed_problems.py` first.")
            return

        two_sum = problems.get("two-sum")
        count_vowels = problems.get("count-vowels")
        fizz_buzz = problems.get("fizz-buzz")
        reverse_string = problems.get("reverse-string")
        valid_palindrome = problems.get("valid-palindrome")

        # 5. Check if submissions already exist for this class
        existing_subs = await session.execute(
            select(Submission).where(Submission.user_id.in_([s.id for s in student_users]))
        )
        if len(existing_subs.scalars().all()) >= 15:
            print(f"• Class already has {len(existing_subs.scalars().all())} submissions seeded. Skipping submission generation.")
            print("\nDemo environment is ready!")
            print(f"  Teacher Portal : {TEACHER_EMAIL} / {DEFAULT_PASSWORD}")
            print(f"  Class Join Code: {class_group.join_code}")
            print(f"  Student Sample : student1@coderazz.org / {DEFAULT_PASSWORD}")
            return

        print("\nSimulating 2 weeks of student submissions, diagnoses, hints, and annotations...")

        # Simulation plan across students and days:
        # Day 1-3: Students start Two Sum, some get A1 (off-by-one)
        # Day 4-7: Students work on Count Vowels, high prevalence of D4 (return in loop)
        # Day 8-10: Students work on FizzBuzz with A3
        # Day 11-14: Low confidence novel patterns triggering Annotation Queue
        submission_timeline = [
            # Alice: Solves Two Sum correctly after A1 struggle
            {
                "student": student_users[0],
                "problem": two_sum,
                "days_ago": 13,
                "code": SNIPPETS["two_sum_a1_off_by_one"],
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "A1",
                "confidence": 0.95,
                "detector": DetectorType.RULE_AST,
                "hints": [1, 2],
            },
            {
                "student": student_users[0],
                "problem": two_sum,
                "days_ago": 12,
                "code": SNIPPETS["two_sum_accepted"],
                "verdict": SubmissionVerdict.ACCEPTED,
                "misconception": None,
                "hints": [],
            },
            # Bob: Trapped in D4 accumulator return inside loop
            {
                "student": student_users[1],
                "problem": count_vowels,
                "days_ago": 10,
                "code": SNIPPETS["count_vowels_d4_premature_return"],
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "D4",
                "confidence": 0.98,
                "detector": DetectorType.RULE_AST,
                "hints": [1, 2, 3, 4],
            },
            # Charlie: Also hits D4 on Count Vowels (driving class struggle peak)
            {
                "student": student_users[2],
                "problem": count_vowels,
                "days_ago": 9,
                "code": SNIPPETS["count_vowels_d4_premature_return"],
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "D4",
                "confidence": 0.98,
                "detector": DetectorType.RULE_AST,
                "hints": [1, 2],
            },
            # Diana: Hits A3 exclusive bound on Fizz Buzz
            {
                "student": student_users[3],
                "problem": fizz_buzz,
                "days_ago": 7,
                "code": SNIPPETS["fizz_buzz_a3_exclusive_bound"],
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "A3",
                "confidence": 0.92,
                "detector": DetectorType.RULE_AST,
                "hints": [1],
            },
            # Evan: Hits A1 off-by-one on Two Sum
            {
                "student": student_users[4],
                "problem": two_sum,
                "days_ago": 6,
                "code": SNIPPETS["two_sum_a1_off_by_one"],
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "A1",
                "confidence": 0.95,
                "detector": DetectorType.RULE_AST,
                "hints": [1, 2, 3],
            },
            # Alice: Reverse String Accepted
            {
                "student": student_users[0],
                "problem": reverse_string,
                "days_ago": 5,
                "code": SNIPPETS["reverse_string_accepted"],
                "verdict": SubmissionVerdict.ACCEPTED,
                "misconception": None,
                "hints": [],
            },
            # Bob: Reverse String Accepted
            {
                "student": student_users[1],
                "problem": reverse_string,
                "days_ago": 4,
                "code": SNIPPETS["reverse_string_accepted"],
                "verdict": SubmissionVerdict.ACCEPTED,
                "misconception": None,
                "hints": [],
            },
            # Charlie: Ambiguous palindrome triggering S2 Novel Misconception Task
            {
                "student": student_users[2],
                "problem": valid_palindrome,
                "days_ago": 3,
                "code": SNIPPETS["palindrome_s2_ambiguous"],
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "S2",
                "confidence": 0.38,
                "detector": DetectorType.ML_CLASSIFIER,
                "hints": [],
                "spawn_annotation": True,
                "annotation_trigger": "NOVEL_MISCONCEPTION (S2)",
                "annotation_status": AnnotationTaskStatus.PENDING,
            },
            # Diana: Low confidence classification triggering Annotation Task
            {
                "student": student_users[3],
                "problem": count_vowels,
                "days_ago": 2,
                "code": "def solve():\n    return 'unclear logic'\n",
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "S2",
                "confidence": 0.32,
                "detector": DetectorType.ML_CLASSIFIER,
                "hints": [],
                "spawn_annotation": True,
                "annotation_trigger": "LOW_CONFIDENCE (0.32 < 0.50)",
                "annotation_status": AnnotationTaskStatus.PENDING,
            },
            # Evan: Another submission that was already reviewed and RESOLVED by the teacher
            {
                "student": student_users[4],
                "problem": count_vowels,
                "days_ago": 1,
                "code": SNIPPETS["count_vowels_d4_premature_return"],
                "verdict": SubmissionVerdict.WRONG_ANSWER,
                "misconception": "D4",
                "confidence": 1.0,
                "detector": DetectorType.HUMAN_OVERRIDE,
                "hints": [1, 2],
                "spawn_annotation": True,
                "annotation_trigger": "LOW_CONFIDENCE (0.41 < 0.50)",
                "annotation_status": AnnotationTaskStatus.RESOLVED,
                "annotation_notes": "Verified accumulator premature return by Prof. Ada Lovelace",
            },
        ]

        total_subs = 0
        total_hints = 0
        total_annotations = 0

        for item in submission_timeline:
            prob = item["problem"]
            if not prob:
                continue

            sub_time = now - timedelta(days=item["days_ago"], hours=2)
            passed_cases = prob.order_index if item["verdict"] == SubmissionVerdict.ACCEPTED else 0

            sub = Submission(
                user_id=item["student"].id,
                problem_id=prob.id,
                code=item["code"],
                language="python",
                status=SubmissionStatus.COMPLETED,
                verdict=item["verdict"],
                runtime_ms=18,
                memory_kb=2048,
                test_cases_passed=passed_cases,
                total_test_cases=3,
                error_message="Wrong Answer on test case 1" if item["verdict"] != SubmissionVerdict.ACCEPTED else None,
                created_at=sub_time,
            )
            session.add(sub)
            await session.commit()
            await session.refresh(sub)
            total_subs += 1

            # Attach Diagnosis if non-accepted
            diag = None
            if item["misconception"]:
                diag = Diagnosis(
                    submission_id=sub.id,
                    misconception_code=item["misconception"],
                    confidence_score=item["confidence"],
                    detector_type=item["detector"],
                    is_primary=True,
                    evidence_lines=[7],
                    explanation=f"Automated diagnosis identifying {item['misconception']} pattern.",
                    created_at=sub_time,
                )
                session.add(diag)
                await session.commit()
                await session.refresh(diag)

            # Attach Hint Requests
            for level in item.get("hints", []):
                tier_names = {
                    1: ("Level 1: Nudge", 0.00),
                    2: ("Level 2: Conceptual Explanation", 0.05),
                    3: ("Level 3: Counter-Example", 0.10),
                    4: ("Level 4: Worked Analogue", 0.15),
                    5: ("Level 5: Targeted Pointer", 0.25),
                }
                title, penalty = tier_names[level]
                hint_req = HintRequest(
                    submission_id=sub.id,
                    diagnosis_id=diag.id if diag else None,
                    user_id=item["student"].id,
                    problem_id=prob.id,
                    hint_level=level,
                    hint_title=title,
                    hint_content=f"Pedagogical guidance for {item['misconception'] or 'general'} challenge.",
                    penalty_score=penalty,
                    leak_check_passed=True,
                    created_at=sub_time + timedelta(minutes=level * 5),
                )
                session.add(hint_req)
                total_hints += 1

            await session.commit()

            # Spawn Annotation Task if configured
            if item.get("spawn_annotation"):
                task = AnnotationTask(
                    submission_id=sub.id,
                    diagnosis_id=diag.id if diag else None,
                    status=item["annotation_status"],
                    assigned_annotator_id=teacher.id if item["annotation_status"] == AnnotationTaskStatus.RESOLVED else None,
                    original_misconception_code="S2" if "S2" in item["annotation_trigger"] else "D4",
                    original_confidence=item["confidence"],
                    trigger_reason=item["annotation_trigger"],
                    resolved_misconception_code=item["misconception"] if item["annotation_status"] == AnnotationTaskStatus.RESOLVED else None,
                    annotator_notes=item.get("annotation_notes"),
                    resolved_at=sub_time + timedelta(hours=1) if item["annotation_status"] == AnnotationTaskStatus.RESOLVED else None,
                    created_at=sub_time,
                )
                session.add(task)
                await session.commit()
                total_annotations += 1

        print("\n✓ Successfully Seeded:")
        print(f"  • Submissions: {total_subs}")
        print(f"  • Hint Requests: {total_hints}")
        print(f"  • Annotation Tasks: {total_annotations}")
        print("\n" + "=" * 70)
        print("Demo Environment Credentials:")
        print(f"  Teacher Portal : {TEACHER_EMAIL} / {DEFAULT_PASSWORD}")
        print(f"  Class Join Code: {class_group.join_code}")
        print(f"  Student Sample : student1@coderazz.org / {DEFAULT_PASSWORD}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
