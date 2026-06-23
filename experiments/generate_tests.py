import os
import json
import random
import time

# =========================
# Settings
# =========================

OBJECTS = 10
TEST_SIZES = [500, 1000, 20000]

MATERIALS = [
    "wood",
    "metal",
    "plasticic",
    "glass",
    "stone",
    "rubber",
    "paper",
    "fabric",
    "ceramic",
    "carbon"
]

BASE_DIR = "tests"

# =========================
# Creation
# =========================

os.makedirs(BASE_DIR, exist_ok=True)

print("🚀 Starting experiment generation...\n")

for obj_id in range(1, OBJECTS + 1):

    object_name = f"object_{obj_id}"

    material = MATERIALS[(obj_id - 1) % len(MATERIALS)]

    object_dir = os.path.join(BASE_DIR, object_name)

    os.makedirs(object_dir, exist_ok=True)

    print(f"📦 Created object: {object_name} ({material})")

    # object metadata
    info = {
        "id": obj_id,
        "material": material
    }

    with open(
        os.path.join(object_dir, "info.json"),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(info, f, indent=4)

    # =========================
    # Experiments
    # =========================

    for size in TEST_SIZES:

        print(f"   ⚙️ Experiment: {size}")

        size_dir = os.path.join(object_dir, str(size))

        os.makedirs(size_dir, exist_ok=True)

        start_time = time.time()

        tests = []

        passed = 0
        failed = 0

        for i in range(size):

            value = random.randint(1, 100000)

            status = random.choice(["PASS", "FAIL"])

            if status == "PASS":
                passed += 1
            else:
                failed += 1

            tests.append({
                "test_id": i + 1,
                "value": value,
                "status": status
            })

        end_time = time.time()

        # save experiment results
        with open(
            os.path.join(size_dir, "tests.json"),
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(tests, f, indent=2)

        # result
        result = {
            "object": object_name,
            "material": material,
            "test_count": size,
            "passed": passed,
            "failed": failed,
            "execution_time_sec": round(end_time - start_time, 2)
        }

        with open(
            os.path.join(size_dir, "result.json"),
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(result, f, indent=2)

        print(
            f"      ✅ PASS: {passed} | ❌ FAIL: {failed}"
        )

print("\n🎉 All experiments finished!")
