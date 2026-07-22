# Hugging Face Heart SVG - Research Log

This document details the DOM structure, selection strategies, and API endpoints used to modify heart icons, highlight unliked models, and enable inline liking on the Hugging Face models page (`https://huggingface.co/models`).

---

## 1. Trigger & Target Elements

**Goal**: Identify the heart icon SVGs on Hugging Face pages and apply custom CSS styles to make them larger and stand out in yellow.

**Target Path Signatures**:
- Detail Page Heart: `d="M22.45,6a5.47,5.47,0,0,1,3.91,1.64..."` (`path[d^="M22.45"]`)
- Model List Card Heart: `d="M22.5,4c-2,0-3.9,0.8-5.3,2.2L16,7.4..."` (`path[d^="M22.5,4"]`)

---

## 2. Element Selectors & DOM Map

### Listing/Search Cards (Models, Datasets, Papers)
- **Card Container**: `article.overview-card-wrapper`
- **Model ID Anchor**: `article.overview-card-wrapper > a` (href format: `/${username}/${modelName}`)
- **Heart Container**: `div.mr-1.flex.items-center` inside card footer
- **SVG Selector**: `article.overview-card-wrapper a div.mr-1.flex.items-center > svg`

### Repository Detail Pages (Models, Datasets, Spaces)
- **SVG Selector (Unliked/Outline)**: `h1 button.hover:bg-linear-to-t.relative.flex > svg.left-1.5.absolute`
- **SVG Selector (Liked/Filled)**: `h1 button.hover:bg-linear-to-t.relative.flex > svg.absolute.text-red-500`

---

## 3. Hugging Face REST APIs for Liking

### User Likes List
- **Endpoint**: `GET /api/users/${username}/likes`
- **Returns**: Array of liked objects containing `repo.name` (e.g., `"thinkingmachines/Inkling"`).

### Like Model
- **Endpoint**: `POST /api/models/${modelId}/like`
- **Returns**: `200 OK`

### Unlike Model
- **Endpoint**: `DELETE /api/models/${modelId}/like`
- **Returns**: `200 OK`

---

## 4. Unliked Models Highlight & Inline Liking Strategy

1. **User Detection**: Detect current logged-in user via `data-props` attributes, header profile links, or `/api/whoami`.
2. **Likes Synchronization**: Fetch the user's liked model set from `/api/users/${username}/likes`.
3. **Card Tagging**: Tag each `article.overview-card-wrapper` as `.hf-is-liked` or `.hf-is-unliked`.
4. **Green Border Styling**:
   ```css
   article.overview-card-wrapper.hf-is-unliked {
     border: 2px solid #10b981 !important;
     border-radius: 12px !important;
     box-shadow: 0 4px 20px rgba(16, 185, 129, 0.15) !important;
     transition: border 0.3s ease, box-shadow 0.3s ease !important;
   }
   ```
5. **Inline Liking Event & Card Identification**:
   - **Model ID Resolution**: Cards contain multiple `<a>` tags (e.g. org avatar `/google` before model link `/google/gemma-7b`). Using `querySelectorAll('a[href^="/"]')` and filtering for 2-segment non-system routes guarantees accurate `modelId` resolution across all list styles.
   - **Click Interception**: Attach capture-phase listeners (`mousedown`, `mouseup`, `click`) to heart containers with `e.preventDefault()`, `e.stopPropagation()`, and `e.stopImmediatePropagation()`. This prevents the parent `<a>` anchor tag from triggering page navigation.
   - **Session Independence**: Rest requests to `POST /api/models/${modelId}/like` and `DELETE /api/models/${modelId}/like` rely on standard HTTP session cookies and operate independently of username detection. 401/403 responses gracefully prompt for login if unauthenticated.

---

## 5. Lifecycle & SPA Observation

Hugging Face uses Svelte / client-side routing (SPA). A `MutationObserver` monitors DOM mutations on `document.body` with 200ms debouncing to automatically tag new model cards loaded via lazy loading or infinite scrolling.
