# Hugging Face Heart SVG, Inline Liking & Date Filter - Research Log

This document details the DOM structure, selection strategies, API endpoints, inline liking behavior, and client-side date range filtering mechanisms used on Hugging Face model listing pages (`https://huggingface.co/models` and user/org pages like `https://huggingface.co/*/models`).

---

## 1. Trigger & Target Elements

**Goal**: Identify native heart icon SVGs on Hugging Face model cards, restore inline like/unlike actions, highlight unliked cards, and apply client-side date filtering.

**Target Path Signatures**:
- **Unliked Model List Card Heart (Outline `♡`)**: `d="M22.45,6a5.47,5.47,0,0,1,3.91,1.64...m0-2..."` (`d.includes('22.45')` or `d.includes('m0-2')`).
- **Liked Model List Card Heart (Solid `♥`)**: `d="M22.5,4c-2,0-3.9,0.8-5.3,2.2L16,7.4..."` (`d.includes('M22.5,4')` / `d.includes('M22.5 4')`) or styled with `text-red-500` / `fill-red-500`.
- **Detail Page Heart**: `d="M22.45,6a5.47,5.47,0,0,1,3.91,1.64..."` (`path[d^="M22.45"]`)

> [!NOTE]
> Hugging Face uses `<svg fill="currentColor">` for both outline and solid heart icons on model list cards. Therefore, checking `fill !== 'none'` alone is insufficient; path `d` signatures (`M22.45` vs `M22.5,4`) and red/pink CSS class inspection (`text-red-500`) are required to accurately distinguish unliked vs liked state.

---

## 2. Element Selectors & DOM Map

### Listing/Search Cards (Models, Datasets, Papers)
- **Card Container**: `article.overview-card-wrapper`
- **Model ID Anchor**: `article.overview-card-wrapper > a` (href format: `/${username}/${modelName}`)
- **Heart Container**: `div.mr-1.flex.items-center` inside card footer
- **SVG Selector**: `article.overview-card-wrapper a div.mr-1.flex.items-center > svg`
- **Date Tag**: `article.overview-card-wrapper time` (`datetime` attribute ISO timestamp e.g. `2026-07-23T09:16:19`)

### Repository Detail Pages (Models, Datasets, Spaces)
- **SVG Selector (Unliked/Outline)**: `h1 button.hover:bg-linear-to-t.relative.flex > svg.left-1.5.absolute`
- **SVG Selector (Liked/Filled)**: `h1 button.hover:bg-linear-to-t.relative.flex > svg.absolute.text-red-500`

---

## 3. Hugging Face REST APIs for Liking

### User Likes Synchronization
- The inline feature intentionally does not fetch the user’s complete liked-model list. Initial state comes from the card’s native heart; optimistic state is kept in memory until the page reloads.

### Like Model
- **Endpoint**: `POST /api/models/${modelId}/like`
- **Returns**: `200 OK`

### Unlike Model
- **Endpoint**: `DELETE /api/models/${modelId}/like`
- **Returns**: `200 OK`

---

## 4. Unliked Models Highlight & Inline Liking Strategy

1. **Card Tagging & Solid vs Outline Heart Inspection**:
   - Locate heart SVG via container attributes/classes (`[title*="like"]`, `[class*="heart"]`), exact SVG path `d` signatures (`M22.5,4`, `22.45`, `m0-2`), or the documented card-footer container.
   - Differentiate liked models (`.hf-is-liked`) by detecting red/pink color classes (`text-red-500`) or solid heart path signature (`M22.5,4`).
   - Differentiate unliked models (`.hf-is-unliked`) by detecting outline heart path signature (`M22.45` / `m0-2`) or gray styling (`text-gray-400`).
   - Do not use generic task/stat path fragments (`4.318`, `14c1.49`, `20.91`) as heart evidence.
2. **Green Border Styling**:
   ```css
   article.overview-card-wrapper.hf-is-unliked {
     border: 2px solid #10b981 !important;
     border-radius: 12px !important;
     box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;
     transition: border 0.3s ease, box-shadow 0.3s ease !important;
   }
   ```
3. **Inline Liking Event & Card Identification**:
   - **Model ID Resolution**: Cards contain multiple `<a>` tags (e.g. org avatar `/google` before model link `/google/gemma-7b`). Using `querySelectorAll('a[href^="/"]')` and filtering for 2-segment non-system routes guarantees accurate `modelId` resolution across all list styles.
   - **Click Interception**: Attach capture-phase listeners to the heart/count container. `mousedown` and `mouseup` stop propagation only; `click` prevents the parent `<a>` navigation. Enter and Space provide keyboard activation.
   - **Session Independence**: Requests to `POST /api/models/${modelId}/like` and `DELETE /api/models/${modelId}/like` use same-origin session cookies and operate independently of username detection. 401/403 responses prompt for login and restore the prior state.
   - **Native Appearance**: The retired yellow styling is not restored. Successful optimistic updates use Hugging Face’s native red/filled and gray/outline heart states.

---

## 5. Date Range Slider Filtering Strategy

1. **Date Parsing**: Read the ISO timestamp string from `card.querySelector('time').getAttribute('datetime')` (with fallback to `title` and relative text matching).
2. **Age Calculation**: Compute `daysAgo = (Date.now() - timestamp) / (1000 * 60 * 60 * 24)`.
3. **Filtering Rule**:
   If date filter is active and `daysAgo < minDays` or `daysAgo > maxDays`, add `.hf-date-filtered-out` (`display: none !important;`) to the card wrapper.
4. **Sidebar Injection Seam**:
   Detect left panel (`form`, `aside`, or `div.left-sidebar`) and inject `#hf-date-filter-widget` at top.
5. **Granular Presets & Inputs**:
   Provide presets (`24h`, `3d`, `7d`, `14d`, `30d`, `60d`, `90d`, `180d`, `1y`, `All`), range slider, and numeric day input fields.
6. **Empty State Handling**:
   When `visibleCards === 0` and `totalCards > 0`, render `#hf-df-empty-notice` notifying the user to scroll for more models or adjust date limits.

---

## 6. Lifecycle & SPA Observation

Hugging Face uses Svelte / client-side routing (SPA). A `MutationObserver` monitors DOM mutations on `document.body` with 200ms debouncing to automatically tag and date-filter new model cards loaded via lazy loading or infinite scrolling.

---

## 7. Code Audit & Robustness Hardenings (v1.7.7)

1. **MutationObserver Target Node Safety**: Resolved `const targetEl = target.nodeType === 1 ? target : target.parentElement;` before invoking `.closest('#hf-date-filter-widget')` to prevent `TypeError` exceptions when DOM mutations occur on text nodes (`Node.TEXT_NODE`).
2. **Multi-Path Heart SVG Inspection**: Updated `isModelLiked()` to iterate through all `<path>` elements via `querySelectorAll('path')` instead of querying only the first child path.
3. **SPA Detached Element Handling**: Added `!document.body.contains(noticeEl)` check inside `updateEmptyNotice()` to ensure empty notice re-injection after SPA page transitions.
4. **Min/Max Days Input Range Synchronization**: Enforced `DATE_MAX_DAYS >= DATE_MIN_DAYS` auto-adjustment when user increases `minInput`.
5. **Hydrated Like State Precedence**: Ignore userscript-owned `aria-pressed` values after binding and observe native heart-path attribute changes so hydrated liked cards lose the green unliked border.
