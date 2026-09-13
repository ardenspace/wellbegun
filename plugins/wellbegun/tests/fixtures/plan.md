---
status: approved
---

# Minimal producer → gate → consumer

<!-- wellbegun:contract producer -->
{
  "id": "producer",
  "kind": "step",
  "scope_id": "scope-producer",
  "goal": "Produce producer",
  "completion": [
    {
      "id": "works",
      "text": "Observable contract holds."
    }
  ],
  "verification": [
    "python3 check.py"
  ],
  "decisions": [],
  "registry": [],
  "discretion": "Local implementation details",
  "requires": [],
  "grade": "basic"
}
<!-- /wellbegun:contract -->

<!-- wellbegun:contract gate -->
{
  "id": "gate",
  "kind": "gate",
  "scope_id": "scope-gate",
  "goal": "Produce gate",
  "completion": [
    {
      "id": "works",
      "text": "Observable contract holds."
    }
  ],
  "verification": [
    "python3 check.py"
  ],
  "decisions": [],
  "registry": [],
  "discretion": "Local implementation details",
  "requires": [
    "producer"
  ],
  "grade": "fresh",
  "producers": [
    "producer"
  ],
  "consumers": [
    "consumer"
  ]
}
<!-- /wellbegun:contract -->

<!-- wellbegun:contract consumer -->
{
  "id": "consumer",
  "kind": "step",
  "scope_id": "scope-consumer",
  "goal": "Produce consumer",
  "completion": [
    {
      "id": "works",
      "text": "Observable contract holds."
    }
  ],
  "verification": [
    "python3 check.py"
  ],
  "decisions": [],
  "registry": [],
  "discretion": "Local implementation details",
  "requires": [
    "gate"
  ],
  "grade": "basic"
}
<!-- /wellbegun:contract -->
