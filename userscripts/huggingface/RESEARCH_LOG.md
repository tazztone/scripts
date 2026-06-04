# Hugging Face Heart SVG - Research Log

This document details the DOM structure and selection strategies used to modify the heart icon on the Hugging Face models page (`https://huggingface.co/models`).

---

## 1. Trigger & Target Elements

**Goal**: Identify the heart icon SVGs on Hugging Face pages and apply custom CSS styles to make them larger and stand out in yellow.

**Target Path Signature**:
`d="M22.45,6a5.47,5.47,0,0,1,3.91,1.64,5.7,5.7,0,0,1,0,8L16,26.13,5.64,15.64a5.7,5.7,0,0,1,0-8,5.48,5.48,0,0,1,7.82,0L16,10.24l2.53-2.58A5.44,5.44,0,0,1,22.45,6m0-2a7.47,7.47,0,0,0-5.34,2.24L16,7.36,14.89,6.24a7.49,7.49,0,0,0-10.68,0,7.72,7.72,0,0,0,0,10.82L16,29,27.79,17.06a7.72,7.72,0,0,0,0-10.82A7.49,7.49,0,0,0,22.45,4Z"`

**Findings**:
The heart SVG appears in two main contexts on Hugging Face:
1. **Listings & Cards**: Used as the "like count" indicator on models, datasets, spaces, and paper cards.
2. **Detail Header**: Used as the "Like" button inside the main header on repository detail pages.

---

## 2. Element Selectors & DOM Map

### Listing/Search Cards (Models, Datasets, Papers)
- **SVG Selector**: `article.overview-card-wrapper a div.mr-1.flex.items-center > svg.flex-none.w-3.text-gray-400`
- **SVG Parent Classes**: `mr-1 flex items-center overflow-hidden whitespace-nowrap text-sm leading-tight text-gray-400`
- **Path**: Uses the exact unliked heart path.

### Spaces Listing Cards
- **SVG Selector**: `article a header div.flex.h-4.items-center > svg.mr-1.text-gray-100`
- **SVG Parent Classes**: `flex h-4 items-center text-xs rounded border !border-white/5 bg-white/10 px-1 dark:!border-white/5`

### Repository Detail Pages (Models, Datasets, Spaces)
- **SVG Selector (Unliked/Outline)**: `h1 button.hover:bg-linear-to-t.relative.flex > svg.left-1.5.absolute`
- **SVG Selector (Liked/Filled)**: `h1 button.hover:bg-linear-to-t.relative.flex > svg.absolute.text-red-500`
- **SVG Parent/Container**: `button[title="Like"]` or `button[title="Unlike"]` (typically has CSS hash suffixes like `.svelte-8w3x9m`).

---

## 3. Styling Strategy

Because the goal is styling/appearance modification, we can achieve this entirely using CSS injection. By using the modern CSS `:has()` selector, we can target only SVGs containing the specific path of interest. This avoids CPU-intensive JS observers and behaves instantly upon element mounting.

### CSS Rules:
We want to target:
1. The outline/unliked heart SVG path (`d^="M22.45"`).
2. The elements containing them to adjust their dimensions, margins, and colors.

```css
/* Style target SVG containing the specific heart outline path */
svg:has(path[d^="M22.45"]) {
  color: #fbbf24 !important; /* Tailwind amber-400 / yellow */
  fill: currentColor !important;
  transform: scale(1.3) !important;
  transition: transform 0.2s ease, color 0.2s ease !important;
}

/* Hover effect to make it "pop out" more */
svg:has(path[d^="M22.45"]):hover {
  transform: scale(1.5) !important;
  color: #f59e0b !important; /* Tailwind amber-500 */
}
```

---

## 4. Lifecycle & SPA Behavior

Hugging Face uses Svelte / client-side routing (SPA). 
- If we inject the CSS styling once in the document `<head>`, the browser will automatically apply it to any new elements dynamically matched by `:has(...)` as they are created.
- This renders dynamic URL/navigation tracking unnecessary, though we still structure the script cleanly to inject the styles immediately upon page load.
