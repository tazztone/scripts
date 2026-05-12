# Userscripts

A collection of production-grade browser userscripts (compatible with Violentmonkey/Tampermonkey) designed for high reliability and maintainability across modern SPAs.

## Standard Project Structure

Every userscript resides in its own subdirectory and adheres to the standard workflow defined in [userscript-development](./userscript-development/SKILL.md):

- **`RESEARCH_LOG.md`**: Rigorous documentation of the target site's DOM structure, robust selectors, and visual heuristics. Used to ensure longevity against UI updates.
- **`[name].user.js`**: The source code following a strict component separation (CONFIG, STYLES, UTILITIES, LOGIC, ORCHESTRATION).
- **`README.md`**: User guide containing configuration mapping and quick-install links.
- **`tests/`** (Optional): Testing infrastructure (e.g., Playwright) to verify logic against mock environments.

---

## Directory Inventory

| Directory | Description |
| :--- | :--- |
| [**`perplexity-auto-approve`**](./perplexity-auto-approve) | Automates specific action card approvals and enables external connectors on Perplexity.ai. |
| [**`topp-alarm`**](./topp-alarm) | Streamlines setting price alarms on Toppreise.ch directly from item views. |
| [**`userscript-development`**](./userscript-development) | Specialized workflow guidelines, architectural standards, and reference templates used to generate and maintain these scripts. |

---

## Shared Tooling

- **`venv/`**: A shared Python virtual environment utilized by individual projects for automated extraction (agent-assisted) and end-to-end validation.
