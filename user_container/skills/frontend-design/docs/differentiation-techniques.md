# Differentiation Techniques

How to make every design unique while maintaining professionalism.

---

## Core principle

**Good design is 80% fundamentals + 20% uniqueness.**

Fundamentals (from design-principles.md) must be solid. Only then add distinguishing elements. Without fundamentals → chaos. Without differentiators → generic.

---

## 1. Signature Element

Every design should have one element that is characteristic and memorable.

### Examples of signature elements:

**Typographic:**
- One bold font in headings
- Specific text treatment (outline, gradient, clip)
- Characteristic letter-spacing or line-height

**Color:**
- Non-obvious accent color (not blue, not purple)
- Gradient as a recurring motif
- Specific use of one color

**Shapes:**
- Consistent rounding (all rounded vs all sharp)
- Asymmetric layouts
- Overlapping elements

**Motion:**
- Characteristic hover animation
- Specific loading state
- Scroll-triggered effects

**Decoration:**
- Custom icons or illustrations
- Pattern/texture as background
- Border treatment (thick, dotted, gradient)

### How to choose a signature element:

1. **Fits the tone** - fun brand can have playful animations, serious brand should be subtle
2. **Is repeatable** - one element used consistently > many random ones
3. **Doesn't interfere** - the differentiator can't compromise UX

---

## 2. Typographic differentiators

### Non-obvious fonts

**Instead of:**
- Inter (everywhere)
- Poppins (everywhere)
- Open Sans (boring)

**Consider:**
- **Satoshi** - geometric sans with character
- **Cabinet Grotesk** - bold, friendly
- **Clash Display** - statement headings
- **Fraunces** - variable serif, very unique
- **Space Grotesk** - tech feel without being monospace
- **Instrument Sans/Serif** - elegant, contemporary
- **General Sans** - clean but not boring

### Typographic treatments

```css
/* Outline text */
.text-outline {
  color: transparent;
  -webkit-text-stroke: 1px var(--color-text);
}

/* Gradient text */
.text-gradient {
  background: linear-gradient(135deg, var(--color-1), var(--color-2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Mixed weights in one sentence */
.text-mixed {
  font-weight: 300;
}
.text-mixed strong {
  font-weight: 700;
}

/* Vertical text */
.text-vertical {
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

/* Huge leading */
.text-airy {
  line-height: 2;
  letter-spacing: 0.1em;
}
```

### Scale as differentiator

```css
/* Dramatic scale contrast */
.hero-title {
  font-size: clamp(4rem, 12vw, 10rem);
  line-height: 0.9;
}
.hero-subtitle {
  font-size: 0.875rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}
```

---

## 3. Color differentiators

### Non-obvious palettes

**Instead of blue accent (#3B82F6):**
- Warm terracotta: `#C65D3B`
- Sage green: `#6B8E6B`
- Deep purple: `#5B21B6`
- Electric lime: `#BFFF00` (on dark background)
- Coral: `#FF6B6B`

**Instead of black/white:**
- Off-black: `#1A1A2E` (with a hint of blue)
- Warm black: `#1C1917` (with a hint of brown)
- Cream: `#FAF7F0`
- Cool grey background: `#F0F4F8`

### Gradient as identifier

```css
/* Linear gradient accent */
.gradient-accent {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Mesh gradient (as section background) */
.gradient-mesh {
  background:
    radial-gradient(at 0% 0%, #1e3a5f 0px, transparent 50%),
    radial-gradient(at 100% 0%, #4a1942 0px, transparent 50%),
    radial-gradient(at 100% 100%, #1e3a5f 0px, transparent 50%),
    #0a0a0a;
}

/* Gradient border */
.gradient-border {
  border: 2px solid transparent;
  background:
    linear-gradient(var(--bg), var(--bg)) padding-box,
    linear-gradient(135deg, var(--color-1), var(--color-2)) border-box;
}
```

### Color as system

```css
/* Monochromatic with one highlight */
--grey-50: #fafafa;
--grey-100: #f5f5f5;
--grey-200: #e5e5e5;
--grey-300: #d4d4d4;
--grey-400: #a3a3a3;
--grey-500: #737373;
--grey-600: #525252;
--grey-700: #404040;
--grey-800: #262626;
--grey-900: #171717;
--accent: #FF3366; /* One strong color pops */
```

---

## 4. Layout differentiators

### Asymmetry

```css
/* Off-center hero */
.hero {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 4rem;
}

/* Offset elements */
.card {
  transform: translateX(-20px);
}
.card:nth-child(even) {
  transform: translateX(20px);
}
```

### Overlapping

```css
/* Cards overlapping */
.card-stack .card {
  margin-top: -2rem;
  position: relative;
}
.card-stack .card:nth-child(1) { z-index: 3; }
.card-stack .card:nth-child(2) { z-index: 2; }
.card-stack .card:nth-child(3) { z-index: 1; }

/* Text overlapping image */
.hero-title {
  position: relative;
  z-index: 2;
  margin-bottom: -2rem;
}
.hero-image {
  position: relative;
  z-index: 1;
}
```

### Bento grid

```css
.bento {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: repeat(3, 200px);
  gap: 1rem;
}
.bento-large {
  grid-column: span 2;
  grid-row: span 2;
}
.bento-wide {
  grid-column: span 2;
}
.bento-tall {
  grid-row: span 2;
}
```

### Edge-to-edge vs contained

```css
/* Mix edge-to-edge with contained sections */
.section-full {
  width: 100vw;
  margin-left: calc(-50vw + 50%);
  padding: 4rem calc(50vw - 50%);
}
.section-contained {
  max-width: 1200px;
  margin: 0 auto;
  padding: 4rem 2rem;
}
```

---

## 5. Component differentiators

### Buttons

```css
/* Thick border */
.btn-thick {
  border: 3px solid currentColor;
  background: transparent;
}

/* Skewed */
.btn-skewed {
  transform: skewX(-5deg);
}
.btn-skewed span {
  transform: skewX(5deg);
  display: block;
}

/* Animated underline */
.btn-underline {
  background: none;
  border: none;
  position: relative;
}
.btn-underline::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: currentColor;
  transition: width 0.3s ease;
}
.btn-underline:hover::after {
  width: 100%;
}

/* Icon morphing */
.btn-icon svg {
  transition: transform 0.3s ease;
}
.btn-icon:hover svg {
  transform: translateX(4px);
}
```

### Cards

```css
/* Glassmorphism */
.card-glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Thick border on one side */
.card-accent {
  border-left: 4px solid var(--accent);
}

/* Hover reveal */
.card-reveal .card-content {
  transform: translateY(100%);
  transition: transform 0.3s ease;
}
.card-reveal:hover .card-content {
  transform: translateY(0);
}

/* Tilt on hover */
.card-tilt {
  transition: transform 0.3s ease;
}
.card-tilt:hover {
  transform: perspective(1000px) rotateX(5deg) rotateY(-5deg);
}
```

### Inputs

```css
/* Underline only */
.input-minimal {
  border: none;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
  padding: 8px 0;
  background: transparent;
}

/* Thick focus ring */
.input-bold:focus {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}

/* Animated label */
.input-float {
  position: relative;
}
.input-float label {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  transition: all 0.2s ease;
  pointer-events: none;
}
.input-float input:focus + label,
.input-float input:not(:placeholder-shown) + label {
  top: 0;
  font-size: 0.75rem;
  background: var(--bg);
  padding: 0 4px;
}
```

---

## 6. Animation differentiators

### Hover effects

```css
/* Magnetic effect (needs JS) */
/* CSS for smooth movement */
.magnetic {
  transition: transform 0.2s ease-out;
}

/* Color shift */
.color-shift {
  transition: filter 0.3s ease;
}
.color-shift:hover {
  filter: hue-rotate(30deg);
}

/* Glitch effect */
.glitch:hover {
  animation: glitch 0.3s ease;
}
@keyframes glitch {
  0%, 100% { transform: translate(0); }
  20% { transform: translate(-2px, 2px); }
  40% { transform: translate(2px, -2px); }
  60% { transform: translate(-2px, -2px); }
  80% { transform: translate(2px, 2px); }
}
```

### Page transitions

```css
/* Fade up on load */
.fade-up {
  opacity: 0;
  transform: translateY(20px);
  animation: fadeUp 0.6s ease forwards;
}
@keyframes fadeUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Stagger children */
.stagger > * {
  opacity: 0;
  transform: translateY(20px);
  animation: fadeUp 0.4s ease forwards;
}
.stagger > *:nth-child(1) { animation-delay: 0.1s; }
.stagger > *:nth-child(2) { animation-delay: 0.2s; }
.stagger > *:nth-child(3) { animation-delay: 0.3s; }
```

### Scroll animations

```css
/* Reveal on scroll (needs Intersection Observer) */
.reveal {
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease;
}
.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Parallax-lite */
.parallax {
  transform: translateY(calc(var(--scroll) * 0.1));
}
```

---

## 7. Decorative differentiators

### Backgrounds and textures

```css
/* Dot pattern */
.bg-dots {
  background-image: radial-gradient(
    circle,
    var(--color-muted) 1px,
    transparent 1px
  );
  background-size: 24px 24px;
}

/* Noise texture (SVG inline) */
.bg-noise {
  position: relative;
}
.bg-noise::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  opacity: 0.04;
  pointer-events: none;
}

/* Grid lines */
.bg-grid {
  background-image:
    linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}
```

### Borders and dividers

```css
/* Gradient border */
.border-gradient {
  border: 2px solid;
  border-image: linear-gradient(135deg, var(--c1), var(--c2)) 1;
}

/* Dashed with custom spacing */
.border-dashed {
  border: none;
  background-image: linear-gradient(
    to right,
    var(--border) 50%,
    transparent 50%
  );
  background-size: 8px 1px;
  background-repeat: repeat-x;
  background-position: bottom;
  padding-bottom: 1px;
}

/* Decorative divider */
.divider-fancy {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.divider-fancy::before,
.divider-fancy::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}
```

### Shadows

```css
/* Colored shadow */
.shadow-colored {
  box-shadow: 0 10px 40px -10px rgba(var(--accent-rgb), 0.3);
}

/* Layered shadows */
.shadow-layered {
  box-shadow:
    0 1px 2px rgba(0,0,0,0.04),
    0 4px 8px rgba(0,0,0,0.04),
    0 16px 32px rgba(0,0,0,0.04);
}

/* Hard shadow (brutalist) */
.shadow-hard {
  box-shadow: 4px 4px 0 var(--color-dark);
}
```

---

## Differentiation checklist

Before delivering the design, check:

- [ ] Do I have a defined signature element?
- [ ] Is the font NOT Inter/Poppins/Open Sans (unless intentional choice)?
- [ ] Is the accent color NOT standard blue (#3B82F6)?
- [ ] Does the layout have something non-obvious (asymmetry, overlap, non-standard grid)?
- [ ] Do components have unique hover/focus states?
- [ ] Is there some animation/interaction that stands out?
- [ ] If I saw this design in a month, would I remember it?
