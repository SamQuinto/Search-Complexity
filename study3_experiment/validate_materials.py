"""Check both Study 3 files. Run: python validate_materials.py

No extra packages are needed. This checks the saved JSONs and enumerates all
512 offers, rather than relying on previously recorded structural measures.
"""

from decimal import Decimal
from itertools import product
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
EXPECTED_COMPLEXITY = {"low": Decimal(421) / 512,
                       "high": Decimal(444) / 512}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_display_order(role):
    """Rank interests by their best Include score, then rank their features."""
    name = role["role_name"]
    groups = {}
    current_group = None
    for issue, options in role["scoresheet"].items():
        include = options[0]
        match = re.match(r"^<b>([^<]+):</b>", include["reason"])
        require(match is not None, f"Missing interest label for {name}, {issue}.")
        group = match.group(1)
        if group != current_group:
            require(group not in groups,
                    f"Interest features must stay together for {name}, {group}.")
            groups[group] = []
            current_group = group
        groups[group].append(Decimal(str(include["score"])))

    for group, scores in groups.items():
        require(scores == sorted(scores, reverse=True),
                f"Features must rank by descending Include score for {name}, {group}.")
    best_scores = [max(scores) for scores in groups.values()]
    require(best_scores == sorted(best_scores, reverse=True),
            f"Interests must rank by their highest Include score for {name}.")


def check_file(path, condition):
    data = json.loads(path.read_text(encoding="utf-8"))
    require(set(data) == {"roles", "tips"} and isinstance(data["tips"], str),
            "Expected the Empirica roles and tips fields.")
    names = ["Party A", "Party B", "Party C"]
    roles = data["roles"]
    require(isinstance(roles, list) and [role["role_name"] for role in roles] == names,
            "Expected a list with one role each for A, B and C.")
    issues = list(roles[0]["scoresheet"])
    require(len(issues) == 9, "Expected nine distinct issues.")
    for role in roles:
        name = role["role_name"]
        require(set(role) == {"role_name", "narrative", "RP", "scoresheet"},
                f"Unexpected role fields for {name}.")
        require(role["RP"] == 0, f"Unexpected reservation value for {name}.")
        require(isinstance(role["narrative"], str) and role["narrative"].strip(),
                f"Missing narrative for {name}.")
        require(set(role["scoresheet"]) == set(issues), f"Issue list differs for {name}.")
        for issue, options in role["scoresheet"].items():
            require([o["option"] for o in options] == ["Include", "Exclude"],
                    f"Option order differs for {name}, {issue}.")
            require(all(set(o) == {"option", "score", "reason"}
                        and type(o["score"]) in (int, float)
                        and isinstance(o["reason"], str) for o in options),
                    f"Unexpected option fields for {name}, {issue}.")
            require(all(Decimal(str(o["score"])).is_finite() for o in options),
                    f"Score must be finite for {name}, {issue}.")
            require(all(Decimal(str(o["score"])) == Decimal(str(o["score"])).quantize(Decimal("0.01"))
                        for o in options), f"Score exceeds two decimal places for {name}, {issue}.")
        check_display_order(role)

    # Offer entries are option indices: 0 = Include and 1 = Exclude. Decimal
    # arithmetic preserves the score at the > 0 boundary.
    offers = list(product((0, 1), repeat=9))
    votes = {}
    payoff_totals = {}
    for offer in offers:
        count = 0
        totals = []
        for role in roles:
            total = sum(Decimal(str(role["scoresheet"][issue][index]["score"]))
                        for issue, index in zip(issues, offer))
            count += total > Decimal(str(role["RP"]))
            totals.append(total)
        votes[offer] = count
        payoff_totals[offer] = totals

    acceptable = {offer for offer in offers if votes[offer] == 3}
    require(len(acceptable) == 4, "Expected four mutually acceptable offers.")
    minimum = min(min(payoff_totals[offer]) for offer in acceptable)
    require(minimum == {"low": Decimal("1.15"), "high": Decimal("1.00")}[condition],
            "Unexpected lowest agreement payoff after rounding.")
    for party in range(3):
        agreement_payoffs = [payoff_totals[offer][party] for offer in acceptable]
        require(min(agreement_payoffs) >= Decimal("1.00"),
                f"Agreement payoff below £1 for Party {'ABC'[party]}.")
    maximum = max(max(payoff_totals[offer]) for offer in acceptable)
    require(maximum == Decimal("11.25"),
            "Unexpected highest individual agreement payoff after rounding.")

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
          f"4 acceptable (0.78125%) | search complexity {complexity * 100}%")
    return data


def main():
    low = check_file(HERE / "study3_low_search_complexity.json", "low")
    high = check_file(HERE / "study3_high_search_complexity.json", "high")
    for low_role, high_role in zip(low["roles"], high["roles"], strict=True):
        name = low_role["role_name"]
        require(low_role["narrative"] == high_role["narrative"],
                f"Narratives differ between conditions for {name}.")
        require(set(low_role["scoresheet"]) == set(high_role["scoresheet"]),
                f"Issue sets differ between conditions for {name}.")
    require(low["tips"] == high["tips"], "Negotiation tips differ between conditions.")
    print("PASS: identical role narratives and shared instructions in both conditions.")
    print("PASS: interests and features rank by Include score for each role and condition.")


if __name__ == "__main__":
    main()
