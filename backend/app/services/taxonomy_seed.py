"""Authoritative taxonomy definitions and idempotent database seeder for CodeRazz."""

import logging
from typing import Any

from backend.app.models.misconception import MisconceptionTaxonomy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TAXONOMY_DEFINITIONS: list[dict[str, Any]] = [
    {
        "code": "A1",
        "category": "Loops & Indexing",
        "name": "Off-by-one in loop bounds",
        "description": (
            "Range end-bound misunderstanding (e.g., range(len(arr)) vs "
            "range(len(arr) - 1) or inclusive boundary errors)."
        ),
        "pedagogical_remedy": (
            "Check loop boundaries against valid array indices; note that range(n) "
            "generates numbers 0 to n-1."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "A2",
        "category": "Loops & Indexing",
        "name": "Infinite loop condition",
        "description": "While-loop predicate never mutates toward termination condition.",
        "pedagogical_remedy": (
            "Ensure loop counter or condition variables are modified inside the "
            "loop body to reach termination."
        ),
        "severity": "CRITICAL",
        "is_meta": False,
    },
    {
        "code": "A3",
        "category": "Loops & Indexing",
        "name": "Index out of range",
        "description": (
            "Accessing index i >= len(sequence) due to incorrect boundary "
            "assumption or unconstrained increment."
        ),
        "pedagogical_remedy": (
            "Remember Python uses 0-based indexing up to len(sequence)-1; verify "
            "index bounds before indexing."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "A4",
        "category": "Loops & Indexing",
        "name": "Inner loop variable shadowing / update",
        "description": (
            "Reusing outer loop variable in inner loop or updating the wrong "
            "iterator variable."
        ),
        "pedagogical_remedy": (
            "Use distinct variable names for nested loops (e.g., i and j) and "
            "ensure inner loops update the correct variable."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "A5",
        "category": "Loops & Indexing",
        "name": "Premature loop termination",
        "description": (
            "Misplaced return or break inside loop body on first iteration instead "
            "of after exhaustion."
        ),
        "pedagogical_remedy": (
            "Only return or break when the search condition is met; place fallback "
            "returns after the loop finishes."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "B1",
        "category": "Conditions & Logic",
        "name": "Assignment instead of equality",
        "description": (
            "Using '=' where '==' was intended (or assignment side-effects in "
            "conditional logic)."
        ),
        "pedagogical_remedy": "Use '==' for comparison and '=' for variable assignment.",
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "B2",
        "category": "Conditions & Logic",
        "name": "Inverted or incorrect boolean operators",
        "description": (
            "Misusing 'and' instead of 'or', or inverted inequality operators ('<' "
            "vs '>')."
        ),
        "pedagogical_remedy": (
            "Review boolean truth tables; ensure conditional combinations "
            "accurately reflect all acceptance criteria."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "B3",
        "category": "Conditions & Logic",
        "name": "Overlapping or misplaced elif branches",
        "description": (
            "Placing more general condition before specific condition, rendering "
            "branches unreachable."
        ),
        "pedagogical_remedy": "Order conditional branches from most specific to least specific.",
        "severity": "LOW",
        "is_meta": False,
    },
    {
        "code": "B4",
        "category": "Conditions & Logic",
        "name": "Indentation / dangling branch",
        "description": (
            "Incorrect indentation causing code to execute outside conditional "
            "guard."
        ),
        "pedagogical_remedy": (
            "Check python indentation levels; statements inside an if/else block "
            "must be indented consistently."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "B5",
        "category": "Conditions & Logic",
        "name": "Redundant / contradictory predicates",
        "description": (
            "Testing conditions that are impossible or already proven true by "
            "preceding guards."
        ),
        "pedagogical_remedy": (
            "Simplify boolean expressions by eliminating conditions already "
            "guaranteed by parent branches."
        ),
        "severity": "LOW",
        "is_meta": False,
    },
    {
        "code": "C1",
        "category": "Scope & State",
        "name": "Uninitialized variable usage",
        "description": (
            "Referencing identifier before first assignment in path or conditional "
            "branch."
        ),
        "pedagogical_remedy": (
            "Initialize variables before using them, especially accumulators and "
            "flag variables before loops."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "C2",
        "category": "Scope & State",
        "name": "Variable shadowing & local/global confusion",
        "description": (
            "Accidentally shadowing outer scope variables or expecting local "
            "mutation to persist globally."
        ),
        "pedagogical_remedy": (
            "Pass state explicitly through function parameters and return values "
            "rather than relying on global variables."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "C3",
        "category": "Scope & State",
        "name": "Unintended mutable object alias mutation",
        "description": (
            "Mutating default argument list/dict or modifying aliased list "
            "references unintentionally."
        ),
        "pedagogical_remedy": (
            "Use None as default parameter values for mutable types; make explicit "
            "copies (e.g. list.copy()) when needed."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "C4",
        "category": "Scope & State",
        "name": "Type mismatch in operations",
        "description": (
            "Attempting string + integer concatenation or invalid implicit type "
            "assumptions."
        ),
        "pedagogical_remedy": (
            "Explicitly cast data types before operations (e.g., str(num) or "
            "int(str_val))."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "C5",
        "category": "Scope & State",
        "name": "Loop variable rebinding",
        "description": (
            "Explicitly assigning to the loop iterator variable inside the loop "
            "expecting it to persist across iterations."
        ),
        "pedagogical_remedy": (
            "Do not manually rebind for-loop variables inside the loop; use while- "
            "loops if manual step control is required."
        ),
        "severity": "LOW",
        "is_meta": False,
    },
    {
        "code": "D1",
        "category": "Functions & Recursion",
        "name": "Missing recursive base case",
        "description": "Recursion continues indefinitely without termination condition.",
        "pedagogical_remedy": (
            "Define clear base cases at the start of recursive functions before "
            "making recursive calls."
        ),
        "severity": "CRITICAL",
        "is_meta": False,
    },
    {
        "code": "D2",
        "category": "Functions & Recursion",
        "name": "Missing or implicit None return",
        "description": (
            "Function computes value but fails to execute an explicit return "
            "statement."
        ),
        "pedagogical_remedy": (
            "Ensure all execution paths through fruitful functions return an "
            "explicit value instead of falling off the end."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "D3",
        "category": "Functions & Recursion",
        "name": "Argument count or order inversion",
        "description": "Calling function with swapped or incorrect number of parameters.",
        "pedagogical_remedy": (
            "Verify function signatures match call sites in argument count and "
            "positional ordering."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "D4",
        "category": "Functions & Recursion",
        "name": "Return inside loop instead of post-loop",
        "description": (
            "Returning accumulated result inside the first iteration of accumulator "
            "loop."
        ),
        "pedagogical_remedy": (
            "Accumulate results across all iterations and place the return "
            "statement outside the loop."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "D5",
        "category": "Functions & Recursion",
        "name": "Recursive call without argument reduction",
        "description": (
            "Calling recursive step with identical parameters, inducing maximum "
            "recursion depth error."
        ),
        "pedagogical_remedy": (
            "Ensure recursive arguments strictly converge toward the base case "
            "(e.g., n - 1 or rest of list)."
        ),
        "severity": "CRITICAL",
        "is_meta": False,
    },
    {
        "code": "E1",
        "category": "Data Structures",
        "name": "Modifying collection during iteration",
        "description": "Adding or deleting items from a list while looping over it.",
        "pedagogical_remedy": (
            "Iterate over a copy of the list (e.g., list(items)) or use list "
            "comprehensions to build a filtered collection."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "E2",
        "category": "Data Structures",
        "name": "Unchecked dictionary key access",
        "description": "Accessing d[k] without verification or .get() fallback.",
        "pedagogical_remedy": (
            "Use 'if key in d:' or 'd.get(key, default)' to safely access "
            "dictionary elements."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "E3",
        "category": "Data Structures",
        "name": "Shallow vs Deep copy confusion",
        "description": (
            "Mutating nested lists believing a .copy() or slice produced an "
            "independent clone."
        ),
        "pedagogical_remedy": (
            "Use copy.deepcopy() when cloning multi-dimensional or nested data "
            "structures."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "E4",
        "category": "Data Structures",
        "name": "Non-subscriptable object indexing",
        "description": "Applying [idx] to integers, floats, or non-iterable objects.",
        "pedagogical_remedy": (
            "Verify the operand is a valid sequence (list, tuple, string) before "
            "applying index brackets."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "F1",
        "category": "Algorithms & Efficiency",
        "name": "Premature accumulator reset",
        "description": (
            "Re-initializing counter or accumulator inside the loop body on every "
            "iteration."
        ),
        "pedagogical_remedy": (
            "Initialize accumulators and sum variables before the loop begins, not "
            "inside the loop body."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "F2",
        "category": "Algorithms & Efficiency",
        "name": "Inefficient quadratic lookup",
        "description": (
            "Using 'item in list' inside a loop instead of set/hash lookup leading "
            "to TLE."
        ),
        "pedagogical_remedy": (
            "Convert lists to sets or dictionaries for O(1) membership lookups "
            "inside loops."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "F3",
        "category": "Algorithms & Efficiency",
        "name": "Unstable sort assumption",
        "description": (
            "Expecting relative order preserved without understanding sorting "
            "stability."
        ),
        "pedagogical_remedy": (
            "Use tie-breaker keys or stable sort mechanisms when secondary ordering "
            "matters."
        ),
        "severity": "LOW",
        "is_meta": False,
    },
    {
        "code": "G1",
        "category": "I/O & Language Idioms",
        "name": "Confusing print() with return",
        "description": (
            "Printing the answer inside a function instead of returning it to the "
            "caller."
        ),
        "pedagogical_remedy": (
            "Use 'return result' to send values back to the caller; online judges "
            "and callers inspect return values, not console prints."
        ),
        "severity": "HIGH",
        "is_meta": False,
    },
    {
        "code": "G2",
        "category": "I/O & Language Idioms",
        "name": "Unparsed input data types",
        "description": (
            "Using input() directly as numeric operand without int() / float() "
            "conversion."
        ),
        "pedagogical_remedy": (
            "Convert string inputs to numeric types using int(input()) or "
            "float(input())."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "G3",
        "category": "I/O & Language Idioms",
        "name": "In-place string mutation attempt",
        "description": "Attempting s[0] = 'a' on immutable Python strings.",
        "pedagogical_remedy": (
            "Strings in Python are immutable; convert to a list of characters or "
            "create a new string using slicing and concatenation."
        ),
        "severity": "MEDIUM",
        "is_meta": False,
    },
    {
        "code": "S1",
        "category": "Meta-Classes",
        "name": "Careless slip / Syntax typo",
        "description": (
            "Syntactic misspelling, mismatched parenthesis, or minor formatting "
            "slip."
        ),
        "pedagogical_remedy": (
            "Check syntax error line and column indicators for typos or unmatched "
            "delimiters."
        ),
        "severity": "LOW",
        "is_meta": True,
    },
    {
        "code": "S2",
        "category": "Meta-Classes",
        "name": "Novel / Unclassified pattern",
        "description": "Genuine logic error with low confidence across known taxonomy classes.",
        "pedagogical_remedy": (
            "Inspect execution traces and edge cases where expected and actual "
            "outputs diverge."
        ),
        "severity": "LOW",
        "is_meta": True,
    },
]


async def seed_taxonomy(db: AsyncSession) -> dict[str, int]:
    """Idempotently seed or update the 30 core classes + 2 meta-classes.

    Safe across PostgreSQL 16 and SQLite fallback.
    Returns:
        dict with counts of created, updated, and total taxonomy items.
    """
    created_count = 0
    updated_count = 0

    for item in TAXONOMY_DEFINITIONS:
        stmt = select(MisconceptionTaxonomy).where(MisconceptionTaxonomy.code == item["code"])
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            new_item = MisconceptionTaxonomy(
                code=item["code"],
                category=item["category"],
                name=item["name"],
                description=item["description"],
                pedagogical_remedy=item["pedagogical_remedy"],
                severity=item["severity"],
                is_meta=item["is_meta"],
            )
            db.add(new_item)
            created_count += 1
        else:
            existing.category = item["category"]
            existing.name = item["name"]
            existing.description = item["description"]
            existing.pedagogical_remedy = item["pedagogical_remedy"]
            existing.severity = item["severity"]
            existing.is_meta = item["is_meta"]
            updated_count += 1

    await db.commit()
    logger.info(
        "Taxonomy seeded successfully: %d created, %d updated, %d total",
        created_count,
        updated_count,
        len(TAXONOMY_DEFINITIONS),
    )
    return {
        "created": created_count,
        "updated": updated_count,
        "total": len(TAXONOMY_DEFINITIONS),
    }
