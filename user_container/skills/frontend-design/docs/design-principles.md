# Design Principles

Fundamentals of professional design. Not templates - principles that allow you to create unique, cohesive interfaces.

---

## 1. Typography

Typography is 90% of design. Bad typography = amateur look, regardless of everything else.

### Font selection

**Don't choose randomly.** Every font has character:
- **Serif** (Playfair, Cormorant, Lora) → elegance, tradition, literature, luxury
- **Sans-serif geometric** (Futura, Poppins, Outfit) → modernity, tech, cleanliness
- **Sans-serif humanist** (Source Sans, Nunito, Open Sans) → friendliness, readability
- **Monospace** (JetBrains Mono, Fira Code) → tech, code, data, precision
- **Display/Decorative** (Archivo Black, Bebas Neue) → headings, impact, branding

**Font pairing:**
- Contrast, not conflict: serif display + sans body, or geometric display + humanist body
- Max 2 font families (3 is already risky for chaos)
- One font can be enough if it has good weight variants

**Check before using:**
- Does the font have needed characters (accents, special chars)?
- Does it have needed weights (400, 500, 600, 700)?
- How does it look at small sizes?

### Typographic scale

Don't invent sizes randomly. Use a scale:

```css
/* 1.25 scale (major third) - universal */
--text-xs: 0.64rem;   /* 10px - small labels */
--text-sm: 0.8rem;    /* 13px - helper text */
--text-base: 1rem;    /* 16px - body text */
--text-lg: 1.25rem;   /* 20px - lead, emphasis */
--text-xl: 1.563rem;  /* 25px - h4 */
--text-2xl: 1.953rem; /* 31px - h3 */
--text-3xl: 2.441rem; /* 39px - h2 */
--text-4xl: 3.052rem; /* 49px - h1 */
```

**Line-height:**
- Headings: 1.1 - 1.2 (tight)
- Body text: 1.5 - 1.7 (loose for readability)
- UI elements: 1.2 - 1.4

**Letter-spacing:**
- Uppercase headings: +0.05em to +0.1em
- Body text: 0 (default)
- Small uppercase labels: +0.02em to +0.05em

---

## 2. Color

### Building a palette

**Start with one color** - primary/accent. Everything else follows from it.

**Minimal palette (5 colors):**
1. **Background** - main background (light or dark)
2. **Surface** - cards, elevated elements (slightly different from bg)
3. **Text** - main text (high contrast with bg)
4. **Text-muted** - helper text (50-60% contrast)
5. **Accent** - CTA, links, highlights (one strong color)

**Extended palette (+3):**
6. **Border** - subtle dividers
7. **Success** - confirmations (green)
8. **Error** - errors (red)

### Color selection techniques

**Method 1: Monochromatic**
- One color hue, different saturations and lightness
- Safe, always cohesive
- Example: all shades of blue

**Method 2: Analogous**
- Colors next to each other on the wheel (e.g., blue + purple)
- Harmonious, easy to use

**Method 3: Complementary**
- Colors opposite each other (e.g., blue + orange)
- High contrast, dynamic
- Use one as accent, the other minimally

### Contrast and accessibility

**Minimum contrast ratio:**
- Normal text: 4.5:1
- Large text (18px+): 3:1
- UI elements: 3:1

**Check contrast** - use tools:
- WebAIM Contrast Checker
- Chrome DevTools (inspect → color picker → contrast ratio)

### Dark vs light theme

**Light theme:**
- Background: #FFFFFF to #FAFAFA
- Text: #111111 to #1A1A1A
- Better for reading long text

**Dark theme:**
- Background: #0A0A0A to #121212 (not pure black #000!)
- Text: #E5E5E5 to #F5F5F5 (not pure white #FFF!)
- Surface lighter than background (opposite of light theme)
- Less shadows, more emphasis on borders

---

## 3. Spacing and Layout

### Spacing system

**Use a scale, not random values.** Base unit: 4px or 8px.

```css
/* 4px scale */
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
--space-24: 96px;
```

**Rules:**
- Related elements: small spacing (4-8px)
- Groups of elements: medium spacing (16-24px)
- Sections: large spacing (48-96px)

### Hierarchy through spacing

Spacing communicates relationships:
- **Close = related** (label and input: 4-8px)
- **Far = separated** (sections: 48-64px)

**Law of Proximity:** Elements close together are perceived as a group.

### Grids and layouts

**Container widths:**
```css
--container-sm: 640px;   /* text, articles */
--container-md: 768px;   /* forms */
--container-lg: 1024px;  /* dashboards */
--container-xl: 1280px;  /* full layouts */
```

**Readability rule:** Text lines 45-75 characters (max-width: 65ch for body).

**Grid:**
- 12 columns for complex layouts
- CSS Grid > Flexbox for 2D layouts
- Gap instead of margins between elements

---

## 4. Visual Hierarchy

The eye must know where to look first, then, and last.

### Techniques for creating hierarchy

**1. Size** - bigger = more important
```
H1: 48px (most important)
H2: 32px
Body: 16px
Caption: 12px (least important)
```

**2. Weight** - bolder = more important
```
Heading: 700 (bold)
Body: 400 (regular)
Muted: 400 + lower contrast
```

**3. Color/Contrast** - stronger contrast = more important
```
Primary text: #111111 (100% contrast)
Secondary: #666666 (60% contrast)
Tertiary: #999999 (40% contrast)
```

**4. Position** - top and left = first (in LTR cultures)

**5. White space** - more space around = more important

### Squint test

Squint your eyes while looking at the design. Is the hierarchy clear? Do you know where to look first?

---

## 5. Components and Consistency

### Design tokens

Define once, use everywhere:

```css
:root {
  /* Colors */
  --color-bg: #ffffff;
  --color-surface: #f5f5f5;
  --color-text: #111111;
  --color-text-muted: #666666;
  --color-accent: #2563eb;
  --color-border: #e5e5e5;

  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-display: 'Poppins', sans-serif;

  /* Spacing */
  --space-unit: 4px;

  /* Radii */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 16px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;
}
```

### Component consistency

**Same element type = same styles:**
- All primary buttons look identical
- All cards have the same radius and shadow
- All inputs have the same border and focus state

**Variations are intentional:**
- Button primary, secondary, ghost - each has its place
- Don't create new variants without reason

---

## 6. Microinteractions and Animations

### Animation principles

**1. Purpose:** Animation must have a reason (feedback, context, orientation)

**2. Speed:**
- Hover/Focus: 100-150ms
- Appearing: 200-300ms
- Complex transitions: 300-500ms
- Never above 500ms for UI

**3. Easing:**
- `ease-out` - entering elements (accelerate at start)
- `ease-in` - exiting elements (slow down at end)
- `ease-in-out` - elements changing state
- Never `linear` for UI (looks mechanical)

### Basic interactions

```css
/* Hover lift */
.card {
  transition: transform 200ms ease, box-shadow 200ms ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Button press */
.button:active {
  transform: scale(0.98);
}

/* Focus ring */
.input:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
  border-color: var(--color-accent);
}
```

### Staggered animations

For lists of elements - appear sequentially:

```css
.item {
  opacity: 0;
  transform: translateY(10px);
  animation: fadeInUp 300ms ease forwards;
}
.item:nth-child(1) { animation-delay: 0ms; }
.item:nth-child(2) { animation-delay: 50ms; }
.item:nth-child(3) { animation-delay: 100ms; }
/* ... */

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## 7. Responsive Design

### Mobile-first

Start from mobile, add for larger screens:

```css
/* Base: mobile */
.container { padding: 16px; }
.grid { grid-template-columns: 1fr; }

/* Tablet: 768px+ */
@media (min-width: 768px) {
  .container { padding: 24px; }
  .grid { grid-template-columns: repeat(2, 1fr); }
}

/* Desktop: 1024px+ */
@media (min-width: 1024px) {
  .container { padding: 32px; }
  .grid { grid-template-columns: repeat(3, 1fr); }
}
```

### Breakpoints

```css
--breakpoint-sm: 640px;   /* large phones */
--breakpoint-md: 768px;   /* tablets */
--breakpoint-lg: 1024px;  /* small laptops */
--breakpoint-xl: 1280px;  /* desktops */
--breakpoint-2xl: 1536px; /* large monitors */
```

### Responsive typography

```css
/* Fluid typography */
h1 {
  font-size: clamp(2rem, 5vw, 3.5rem);
}

/* Or with breakpoints */
h1 {
  font-size: 2rem;
}
@media (min-width: 768px) {
  h1 { font-size: 2.5rem; }
}
@media (min-width: 1024px) {
  h1 { font-size: 3rem; }
}
```

---

## Checklist before delivery

- [ ] Typography: max 2 fonts, consistent scale, proper line-heights
- [ ] Colors: cohesive palette, sufficient contrast, works in dark/light
- [ ] Spacing: systematic (not random), creates hierarchy
- [ ] Hierarchy: squint test passes, clear what's important
- [ ] Consistency: same elements look the same
- [ ] Animations: fast, purposeful, with easing
- [ ] Responsive: works on mobile, tablet, desktop
