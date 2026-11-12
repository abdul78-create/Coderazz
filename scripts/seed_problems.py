"""Seed starter catalog of programming problems and test cases into CodeRazz."""

import asyncio
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from backend.app.database import get_engine, get_session_factory
from backend.app.models.problem import Problem, ProblemDifficulty, TestCase

PROBLEMS_DATA = [
    {
        "slug": "two-sum",
        "title": "Two Sum",
        "category": "Arrays & Hashing",
        "difficulty": ProblemDifficulty.EASY,
        "order_index": 1,
        "description": (
            "### Description\n"
            "Given a space-separated list of integers `nums` on the first line, and a target integer `target` on the second line, "
            "find the indices of the two numbers such that they add up to `target`.\n\n"
            "Return the indices separated by a space in ascending order. You may assume each input has exactly one solution.\n\n"
            "### Constraints\n"
            "- `2 <= len(nums) <= 10^4`\n"
            "- `-10^9 <= nums[i] <= 10^9`\n"
            "- `-10^9 <= target <= 10^9`\n\n"
            "### Example 1\n"
            "**Input:**\n"
            "```\n"
            "2 7 11 15\n"
            "9\n"
            "```\n"
            "**Output:**\n"
            "```\n"
            "0 1\n"
            "```\n"
            "**Explanation:** `nums[0] + nums[1] = 2 + 7 = 9`."
        ),
        "starter_code": (
            "import sys\n\n"
            "def solve():\n"
            "    lines = sys.stdin.read().strip().splitlines()\n"
            "    if len(lines) < 2:\n"
            "        return\n"
            "    nums = list(map(int, lines[0].split()))\n"
            "    target = int(lines[1].strip())\n"
            "    \n"
            "    # Your code here: find two indices whose elements sum to target\n"
            "    pass\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        ),
        "solution_template": (
            "import sys\n\n"
            "def solve():\n"
            "    lines = sys.stdin.read().strip().splitlines()\n"
            "    if len(lines) < 2:\n"
            "        return\n"
            "    nums = list(map(int, lines[0].split()))\n"
            "    target = int(lines[1].strip())\n"
            "    seen = {}\n"
            "    for i, n in enumerate(nums):\n"
            "        diff = target - n\n"
            "        if diff in seen:\n"
            "            print(f'{seen[diff]} {i}')\n"
            "            return\n"
            "        seen[n] = i\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        ),
        "test_cases": [
            {
                "input_data": "2 7 11 15\n9",
                "expected_output": "0 1",
                "is_hidden": False,
                "explanation": "2 + 7 = 9 at indices 0 and 1",
                "order_index": 1,
            },
            {
                "input_data": "3 2 4\n6",
                "expected_output": "1 2",
                "is_hidden": False,
                "explanation": "2 + 4 = 6 at indices 1 and 2",
                "order_index": 2,
            },
            {
                "input_data": "3 3\n6",
                "expected_output": "0 1",
                "is_hidden": True,
                "explanation": "Duplicate values at different indices",
                "order_index": 3,
            },
            {
                "input_data": "-1 -2 -3 -4 -5\n-8",
                "expected_output": "2 4",
                "is_hidden": True,
                "explanation": "Negative numbers: -3 + -5 = -8",
                "order_index": 4,
            },
            {
                "input_data": "100 200 500 1000\n1500",
                "expected_output": "2 3",
                "is_hidden": True,
                "explanation": "Larger values: 500 + 1000 = 1500",
                "order_index": 5,
            },
        ],
    },
    {
        "slug": "reverse-string",
        "title": "Reverse String",
        "category": "Strings",
        "difficulty": ProblemDifficulty.EASY,
        "order_index": 2,
        "description": (
            "### Description\n"
            "Given a single string `s` via standard input, print the reversed string.\n\n"
            "### Constraints\n"
            "- `1 <= len(s) <= 10^5`\n"
            "- String contains printable ASCII characters.\n\n"
            "### Example 1\n"
            "**Input:** `hello`\n"
            "**Output:** `olleh`\n"
        ),
        "starter_code": (
            "import sys\n\n"
            "def reverse_string():\n"
            "    s = sys.stdin.read().strip()\n"
            "    # Your code here: reverse s and print it\n"
            "    pass\n\n"
            "if __name__ == '__main__':\n"
            "    reverse_string()\n"
        ),
        "solution_template": (
            "import sys\n\n"
            "def reverse_string():\n"
            "    s = sys.stdin.read().strip()\n"
            "    print(s[::-1])\n\n"
            "if __name__ == '__main__':\n"
            "    reverse_string()\n"
        ),
        "test_cases": [
            {
                "input_data": "hello",
                "expected_output": "olleh",
                "is_hidden": False,
                "explanation": "Standard 5-letter word",
                "order_index": 1,
            },
            {
                "input_data": "CodeRazz",
                "expected_output": "zzaRedoC",
                "is_hidden": False,
                "explanation": "Mixed case string",
                "order_index": 2,
            },
            {
                "input_data": "a",
                "expected_output": "a",
                "is_hidden": True,
                "explanation": "Single character edge case",
                "order_index": 3,
            },
            {
                "input_data": "racecar",
                "expected_output": "racecar",
                "is_hidden": True,
                "explanation": "Palindrome word",
                "order_index": 4,
            },
            {
                "input_data": "1234567890",
                "expected_output": "0987654321",
                "is_hidden": True,
                "explanation": "Numeric digits",
                "order_index": 5,
            },
        ],
    },
    {
        "slug": "count-vowels",
        "title": "Count Vowels",
        "category": "Strings & Loops",
        "difficulty": ProblemDifficulty.EASY,
        "order_index": 3,
        "description": (
            "### Description\n"
            "Given an input string `text`, count and print the total number of vowels (`a, e, i, o, u`, case-insensitive) in the string.\n\n"
            "### Constraints\n"
            "- `0 <= len(text) <= 10^5`\n\n"
            "### Example 1\n"
            "**Input:** `CodeRazz Tutor`\n"
            "**Output:** `5`\n"
            "**Explanation:** The vowels are `o, e, a, u, o` (total 5)."
        ),
        "starter_code": (
            "import sys\n\n"
            "def count_vowels():\n"
            "    text = sys.stdin.read().strip()\n"
            "    # Count vowels a, e, i, o, u\n"
            "    pass\n\n"
            "if __name__ == '__main__':\n"
            "    count_vowels()\n"
        ),
        "solution_template": (
            "import sys\n\n"
            "def count_vowels():\n"
            "    text = sys.stdin.read().strip()\n"
            "    vowels = set('aeiouAEIOU')\n"
            "    count = sum(1 for c in text if c in vowels)\n"
            "    print(count)\n\n"
            "if __name__ == '__main__':\n"
            "    count_vowels()\n"
        ),
        "test_cases": [
            {
                "input_data": "CodeRazz Tutor",
                "expected_output": "5",
                "is_hidden": False,
                "explanation": "o, e, a, u, o",
                "order_index": 1,
            },
            {
                "input_data": "rhythm",
                "expected_output": "0",
                "is_hidden": False,
                "explanation": "No vowels in word",
                "order_index": 2,
            },
            {
                "input_data": "AEIOUaeiou",
                "expected_output": "10",
                "is_hidden": True,
                "explanation": "All vowels both cases",
                "order_index": 3,
            },
            {
                "input_data": "The quick brown fox jumps over the lazy dog",
                "expected_output": "11",
                "is_hidden": True,
                "explanation": "Full pangram",
                "order_index": 4,
            },
        ],
    },
    {
        "slug": "fizz-buzz",
        "title": "FizzBuzz",
        "category": "Conditionals & Loops",
        "difficulty": ProblemDifficulty.EASY,
        "order_index": 4,
        "description": (
            "### Description\n"
            "Given an integer `n` from standard input, print numbers from `1` to `n` separated by a space on a single line with these rules:\n"
            "- For multiples of 3, print `Fizz` instead of the number.\n"
            "- For multiples of 5, print `Buzz` instead of the number.\n"
            "- For numbers which are multiples of both 3 and 5, print `FizzBuzz`.\n\n"
            "### Constraints\n"
            "- `1 <= n <= 100`\n\n"
            "### Example 1\n"
            "**Input:** `5`\n"
            "**Output:** `1 2 Fizz 4 Buzz`\n"
        ),
        "starter_code": (
            "import sys\n\n"
            "def fizz_buzz():\n"
            "    data = sys.stdin.read().strip()\n"
            "    if not data:\n"
            "        return\n"
            "    n = int(data)\n"
            "    # Print FizzBuzz sequence up to n\n"
            "    pass\n\n"
            "if __name__ == '__main__':\n"
            "    fizz_buzz()\n"
        ),
        "solution_template": (
            "import sys\n\n"
            "def fizz_buzz():\n"
            "    data = sys.stdin.read().strip()\n"
            "    if not data:\n"
            "        return\n"
            "    n = int(data)\n"
            "    res = []\n"
            "    for i in range(1, n + 1):\n"
            "        if i % 15 == 0:\n"
            "            res.append('FizzBuzz')\n"
            "        elif i % 3 == 0:\n"
            "            res.append('Fizz')\n"
            "        elif i % 5 == 0:\n"
            "            res.append('Buzz')\n"
            "        else:\n"
            "            res.append(str(i))\n"
            "    print(' '.join(res))\n\n"
            "if __name__ == '__main__':\n"
            "    fizz_buzz()\n"
        ),
        "test_cases": [
            {
                "input_data": "5",
                "expected_output": "1 2 Fizz 4 Buzz",
                "is_hidden": False,
                "explanation": "Sequence up to 5",
                "order_index": 1,
            },
            {
                "input_data": "15",
                "expected_output": "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz",
                "is_hidden": False,
                "explanation": "Sequence up to 15 checking FizzBuzz",
                "order_index": 2,
            },
            {
                "input_data": "1",
                "expected_output": "1",
                "is_hidden": True,
                "explanation": "Single item boundary",
                "order_index": 3,
            },
            {
                "input_data": "30",
                "expected_output": (
                    "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz "
                    "16 17 Fizz 19 Buzz Fizz 22 23 Fizz Buzz 26 Fizz 28 29 FizzBuzz"
                ),
                "is_hidden": True,
                "explanation": "Sequence up to 30 with two FizzBuzz multiples",
                "order_index": 4,
            },
        ],
    },
    {
        "slug": "valid-palindrome",
        "title": "Valid Palindrome",
        "category": "Strings",
        "difficulty": ProblemDifficulty.EASY,
        "order_index": 5,
        "description": (
            "### Description\n"
            "Given a string `s`, determine if it is a palindrome, considering only alphanumeric characters and ignoring cases.\n\n"
            "Print `true` if it is a palindrome, and `false` otherwise.\n\n"
            "### Constraints\n"
            "- `1 <= len(s) <= 2 * 10^5`\n\n"
            "### Example 1\n"
            "**Input:** `A man, a plan, a canal: Panama`\n"
            "**Output:** `true`\n"
            "**Explanation:** `amanaplanacanalpanama` is a palindrome."
        ),
        "starter_code": (
            "import sys\n\n"
            "def is_palindrome():\n"
            "    s = sys.stdin.read().strip()\n"
            "    # Check if s is palindrome ignoring non-alphanumeric and case\n"
            "    pass\n\n"
            "if __name__ == '__main__':\n"
            "    is_palindrome()\n"
        ),
        "solution_template": (
            "import sys\n\n"
            "def is_palindrome():\n"
            "    s = sys.stdin.read().strip()\n"
            "    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n"
            "    if cleaned == cleaned[::-1]:\n"
            "        print('true')\n"
            "    else:\n"
            "        print('false')\n\n"
            "if __name__ == '__main__':\n"
            "    is_palindrome()\n"
        ),
        "test_cases": [
            {
                "input_data": "A man, a plan, a canal: Panama",
                "expected_output": "true",
                "is_hidden": False,
                "explanation": "Classic Panama palindrome with punctuation and spaces",
                "order_index": 1,
            },
            {
                "input_data": "race a car",
                "expected_output": "false",
                "is_hidden": False,
                "explanation": "raceacar is not a palindrome",
                "order_index": 2,
            },
            {
                "input_data": " ",
                "expected_output": "true",
                "is_hidden": True,
                "explanation": "Empty string after non-alphanumeric filter is valid palindrome",
                "order_index": 3,
            },
            {
                "input_data": "0P",
                "expected_output": "false",
                "is_hidden": True,
                "explanation": "Alphanumeric mismatch: '0p' != 'p0'",
                "order_index": 4,
            },
        ],
    },
]


async def seed_problems():
    """Seed or update starter problems in PostgreSQL."""
    print("Connecting to database to seed starter problems...")
    factory = get_session_factory()

    async with factory() as session:
        for p_data in PROBLEMS_DATA:
            slug = p_data["slug"]
            query = select(Problem).where(Problem.slug == slug)
            res = await session.execute(query)
            existing = res.scalar_one_or_none()

            if existing:
                print(f"Problem '{slug}' already exists. Updating attributes...")
                existing.title = p_data["title"]
                existing.description = p_data["description"]
                existing.difficulty = p_data["difficulty"]
                existing.category = p_data["category"]
                existing.starter_code = p_data["starter_code"]
                existing.solution_template = p_data["solution_template"]
                problem_id = existing.id
            else:
                print(f"Creating problem: '{slug}' ({p_data['title']})...")
                new_prob = Problem(
                    slug=slug,
                    title=p_data["title"],
                    description=p_data["description"],
                    difficulty=p_data["difficulty"],
                    category=p_data["category"],
                    starter_code=p_data["starter_code"],
                    solution_template=p_data["solution_template"],
                    order_index=p_data["order_index"],
                )
                session.add(new_prob)
                await session.flush()
                problem_id = new_prob.id

            # Seed test cases
            for tc_data in p_data["test_cases"]:
                tc_query = select(TestCase).where(
                    TestCase.problem_id == problem_id,
                    TestCase.order_index == tc_data["order_index"],
                )
                tc_res = await session.execute(tc_query)
                existing_tc = tc_res.scalar_one_or_none()

                if not existing_tc:
                    new_tc = TestCase(
                        problem_id=problem_id,
                        input_data=tc_data["input_data"],
                        expected_output=tc_data["expected_output"],
                        is_hidden=tc_data["is_hidden"],
                        explanation=tc_data.get("explanation"),
                        order_index=tc_data["order_index"],
                    )
                    session.add(new_tc)

        await session.commit()
        print("Successfully seeded all 5 starter problems and test cases!")

    engine = get_engine()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_problems())

