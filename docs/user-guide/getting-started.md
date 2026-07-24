# Getting Started

This guide walks you through installing Pier and running your first Pi delegation from Hermes.

## Prerequisites

- **Hermes Agent** v0.19.0 or later — [install guide](https://hermes-agent.nousresearch.com/docs)
- **Pi** v0.1.0 or later — `npm install -g @earendil-works/pi`
- **Python** 3.10 or later

## Installation

```bash
# Install Pier from PyPI
pip install pier-hermes

# Verify the installation
pier --version
```

### From Source

```bash
git clone https://github.com/thepragmatik/pier.git
cd pier
pip install -e .
```

## Quick Verification

```bash
# Check that Pier can find and communicate with Pi
pier doctor
```

Expected output:

```
✓ Pi binary found at /usr/local/bin/pi
✓ Pi version: 0.1.0
✓ Hermes Agent detected
✓ Pier ready
```

## First Delegation

### Via Hermes Skill (Layer 1)

1. Install the Pier skill in your Hermes profile:

```bash
# Copy the pier skill to your profile
cp skills/pier-skill/SKILL.md ~/.hermes/skills/pier/
```

2. Use it in a Hermes session:

```
> Use the Pier skill to add type hints to src/models.py
```

Hermes will invoke Pi via the terminal subprocess wrapper and return the result.

### Via Python API (Layer 2)

```python
from pier import PierSession

async with PierSession() as session:
    result = await session.run("Refactor src/auth.py to use async/await")
    print(result.summary)
    print(result.diff)
```

## Next Steps

- Learn about [Skills](skills.md) — the Layer 1 integration path
- Learn about [Plugins](plugins.md) — the Layer 2 & 3 integration paths
- Read the [Architecture Overview](../architecture/overview.md) for the full picture
