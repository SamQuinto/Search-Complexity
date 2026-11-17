"""Check both Study 3 files. Run: python validate_materials.py

No extra packages are needed. This checks the saved JSONs and enumerates all
512 offers, rather than relying on previously recorded structural measures.
"""

from decimal import Decimal
import hashlib
from itertools import product
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXPECTED_COMPLEXITY = {"low": Decimal(421) / 512,
                       "high": Decimal(444) / 512}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_file(path, condition):
    data = json.loads(path.read_text(encoding="utf-8"))
    names = ["Party A", "Party B", "Party C"]
    require(list(data["roles"]) == names, "Expected one role each for A, B and C.")
    require(data["condition"] == condition, "Wrong condition label.")
    require(data["player_count"] == 3, "Expected three participants.")
    issues = data["active_issues"]
    require(len(issues) == 9 and len(set(issues)) == 9,
            "Expected nine distinct issues.")
    require(data["required_issues"] == issues, "Every issue must be required.")
    require(not data["invented_issues_enabled"], "Extra issues must be disabled.")
    require(data["agreement_rules"] == {
        "approval_rule": "unanimous", "required_acceptances": 3,
        "require_positive_each_party": True,
        "require_nonnegative_each_party": False,
        "threshold": 0, "allow_zero": False, "comparison": ">",
    }, "Expected unanimous acceptance with all three totals above zero.")
    require([i["name"] for i in data["issues"]] == issues,
            "Issue catalogue order differs from the role tables.")

    for name, role in data["roles"].items():
        require(role["RP"] == 0, f"Unexpected reservation value for {name}.")
        require(role["narrative"] == role["full_text"], "Role text copies differ.")
        require(list(role["determinatescoretable"]) == issues,
                f"Issue order differs for {name}.")
        for issue, definition in zip(issues, data["issues"]):
            options = role["determinatescoretable"][issue]
            require([o["option"] for o in options] == ["Include", "Exclude"],
                    f"Option order differs for {name}, {issue}.")
            require([o["label"] for o in definition["options"]] ==
                    ["Include", "Exclude"], "Issue catalogue options differ.")
            for index in (0, 1):
                require(options[index]["score"] == definition["options"][index][name],
                        f"Score copies differ for {name}, {issue}.")

    # The transfer folder can also be copied elsewhere. When the project source
    # is present, compare every original story, option explanation and score.
    source = data["material_source"]
    source_path = HERE.parent.parent / source["project_file"]
    source_checked = False
    if source_path.exists():
        require(hashlib.sha256(source_path.read_bytes()).hexdigest() == source["sha256"],
                "The original source file has changed.")
        original = json.loads(source_path.read_text(encoding="utf-8"))
        require(data["scenario_id"] == original["scenario_metadata"]["scenario_id"],
                "Source scenario ID differs.")
        for role in original["roles"]:
            exported = data["roles"][role["role_name"]]
            require(exported["narrative"] == role["narrative"], "Narrative changed.")
            require(exported["RP"] == role["RP"], "Reservation value changed.")
            require(exported["determinatescoretable"] == role["scoresheet"],
                    "Payoff table or option explanations changed.")
        require(data["tips"] == original["tips"] + data["task_instructions"],
                "Original tips differ beyond the documented added instructions.")
        source_checked = True

    # Offer entries are option indices: 0 = Include and 1 = Exclude. Decimal
    # arithmetic preserves the six-decimal points for the > 0 boundary.
    offers = list(product((0, 1), repeat=9))
    votes = {}
    for offer in offers:
        count = 0
        for role in data["roles"].values():
            total = sum(Decimal(str(role["determinatescoretable"][issue][index]["score"]))
                        for issue, index in zip(issues, offer))
            count += total > Decimal(str(role["RP"]))
        votes[offer] = count

    acceptable = {offer for offer in offers if votes[offer] == 3}
    require(len(acceptable) == 4, "Expected four mutually acceptable offers.")

    # Work backwards from agreement. A one-issue revision qualifies only when
    # more people meet their reservation values. Keep any starting offer with
    # at least one qualifying route to an acceptable offer.
    reachable = set(acceptable)
    for count in (2, 1, 0):
        for offer in offers:
            if votes[offer] != count:
                continue
            for index in range(9):
                revised = offer[:index] + (1 - offer[index],) + offer[index + 1:]
                if votes[revised] > count and revised in reachable:
                    reachable.add(offer)
                    break
    complexity = Decimal(len(offers) - len(reachable)) / len(offers)
    require(complexity == EXPECTED_COMPLEXITY[condition],
            f"Unexpected {condition} search complexity: {complexity}")
    print(f"{condition.upper()}: PASS | 3 roles | 9 issues | 512 offers | "
          f"4 acceptable (0.78125%) | search complexity {complexity * 100}% | "
          f"original source comparison: {'PASS' if source_checked else 'not available here'}")
    return data


def main():
    low = check_file(HERE / "study3_low_search_complexity.json", "low")
    high = check_file(HERE / "study3_high_search_complexity.json", "high")
    require(low["active_issues"] == high["active_issues"], "Condition issue orders differ.")
    for name in low["roles"]:
        require(low["roles"][name]["narrative"] == high["roles"][name]["narrative"],
                f"Narratives differ between conditions for {name}.")
    for field in ("tips", "readrole_instructions", "task_instructions", "agreement_rules"):
        require(low[field] == high[field], f"Condition instructions differ: {field}")
    print("PASS: identical role narratives and shared instructions in both conditions.")


if __name__ == "__main__":
    main()
