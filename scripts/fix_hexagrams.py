"""Fix systematic trigram binary errors in hexagram JSON files.

The agents used a bottom-to-top trigram reading convention for 兑/巽/震/艮,
but the project convention is top-to-bottom (matching trigrams.json).

Affected mappings (4 of 8 trigrams):
  Correct: 兑=110, 巽=011, 震=100, 艮=001
  Agent:   兑=011, 巽=110, 震=001, 艮=100

乾(111), 坤(000), 坎(010), 离(101) are symmetric so unaffected.

This script:
1. Reads trigrams.json for authoritative binary mapping
2. For each hexagram, fixes upper_trigram and lower_trigram binary by looking up the trigram name
3. Recalculates the binary field = upper_trigram + lower_trigram
4. Regenerates line names from the corrected binary
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# 1. Load authoritative trigram binary mapping
trigrams = json.loads((DATA_DIR / "trigrams.json").read_text(encoding="utf-8"))
TRIGRAM_BIN = {t["name_cn"]: t["binary"] for t in trigrams}
print(f"Trigram mapping: {TRIGRAM_BIN}")

YIN_YANG = {"1": "九", "0": "六"}
POS_NAMES = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}


def fix_hexagram(h: dict) -> dict:
    """Fix a single hexagram's trigram binary values, binary field, and line names."""
    upper_name = h["upper_name"]
    lower_name = h["lower_name"]

    # Fix trigram binaries using name lookup
    old_upper = h["upper_trigram"]
    old_lower = h["lower_trigram"]
    h["upper_trigram"] = TRIGRAM_BIN[upper_name]
    h["lower_trigram"] = TRIGRAM_BIN[lower_name]

    # Recalculate binary = upper + lower
    h["binary"] = h["upper_trigram"] + h["lower_trigram"]

    # Fix line names from corrected binary
    binary = h["binary"]  # positions: [4][5][6][1][2][3] (upper then lower)
    # In the binary string: index 0=pos4, 1=pos5, 2=pos6, 3=pos1, 4=pos2, 5=pos3
    pos_to_bin_idx = {4: 0, 5: 1, 6: 2, 1: 3, 2: 4, 3: 5}

    for line in h["lines"]:
        pos = line["position"]
        digit = binary[pos_to_bin_idx[pos]]
        expected_yao = YIN_YANG[digit]
        if pos == 1:
            expected_name = f"初{expected_yao}"
        elif pos == 6:
            expected_name = f"上{expected_yao}"
        else:
            expected_name = f"{expected_yao}{POS_NAMES[pos]}"
        line["name"] = expected_name

    changes = []
    if old_upper != h["upper_trigram"]:
        changes.append(f"upper {old_upper}→{h['upper_trigram']}")
    if old_lower != h["lower_trigram"]:
        changes.append(f"lower {old_lower}→{h['lower_trigram']}")

    return h, changes


# 2. Process both part files
for part_name in ["hexagrams_part1.json", "hexagrams_part2.json"]:
    part_path = DATA_DIR / part_name
    data = json.loads(part_path.read_text(encoding="utf-8"))

    total_changes = 0
    for i, h in enumerate(data):
        _, changes = fix_hexagram(h)
        if changes:
            total_changes += 1
            print(f"  #{h['number']} {h['name']['cn']}: {', '.join(changes)}")

    # Write back
    part_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fixed {total_changes}/{len(data)} hexagrams in {part_name}")

# 3. Final validation
print("\n=== Final validation ===")
errors = []
all_data = []
for part_name in ["hexagrams_part1.json", "hexagrams_part2.json"]:
    all_data.extend(json.loads((DATA_DIR / part_name).read_text(encoding="utf-8")))

# Check all binaries unique
from collections import Counter
bin_counts = Counter(h["binary"] for h in all_data)
dupes = {b: c for b, c in bin_counts.items() if c > 1}
if dupes:
    for b, c in dupes.items():
        matches = [h for h in all_data if h["binary"] == b]
        names = [f"#{m['number']}{m['name']['cn']}" for m in matches]
        errors.append(f"DUPLICATE binary {b}: {', '.join(names)}")

# Check binary = upper + lower
pos_to_bin_idx = {4: 0, 5: 1, 6: 2, 1: 3, 2: 4, 3: 5}
for h in all_data:
    expected_bin = h["upper_trigram"] + h["lower_trigram"]
    if h["binary"] != expected_bin:
        errors.append(f"#{h['number']} {h['name']['cn']}: binary={h['binary']} != {expected_bin}")
    # Check line names
    for line in h["lines"]:
        pos = line["position"]
        digit = h["binary"][pos_to_bin_idx[pos]]
        yao = "九" if digit == "1" else "六"
        expected_name = POS_NAMES[pos] + yao
        if line["name"] != expected_name:
            errors.append(f"#{h['number']} {h['name']['cn']} pos{pos}: name={line['name']} != {expected_name}")

# Check numbers 1-64
numbers = sorted(h["number"] for h in all_data)
if numbers != list(range(1, 65)):
    errors.append(f"Numbers: {numbers}")

if errors:
    print(f"FAIL: {len(errors)} errors remaining")
    for e in errors[:20]:
        print(f"  {e}")
else:
    print("PASS: All 64 hexagrams valid!")

print(f"Total: {len(all_data)} hexagrams")
