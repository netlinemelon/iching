"""Merge hexagrams_part1.json and hexagrams_part2.json into hexagrams.json."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

part1 = json.loads((DATA_DIR / "hexagrams_part1.json").read_text(encoding="utf-8"))
part2 = json.loads((DATA_DIR / "hexagrams_part2.json").read_text(encoding="utf-8"))

all_hexagrams = part1 + part2

# Verify we have exactly 64
assert len(all_hexagrams) == 64, f"Expected 64 hexagrams, got {len(all_hexagrams)}"

# Verify ordering 1-64
numbers = [h["number"] for h in all_hexagrams]
assert numbers == list(range(1, 65)), f"Numbers not sequential: {sorted(numbers)}"

# Verify no duplicate binaries
binaries = [h["binary"] for h in all_hexagrams]
assert len(set(binaries)) == 64, f"Duplicate binaries found"

out_path = DATA_DIR / "hexagrams.json"
out_path.write_text(json.dumps(all_hexagrams, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"OK: Merged {len(all_hexagrams)} hexagrams → {out_path}")
print(f"File size: {out_path.stat().st_size} bytes")
