---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Design Process

Think like a designer from a software house, not like an automation. Every design must be unique.

### Step 1: Understand context (BEFORE coding)

- **Who uses it?** Age, profession, tech-savviness
- **What problem does it solve?** What's the main goal?
- **What tone?** Formal/casual, innovative/familiar, serious/playful
- **What emotions?** Trust, excitement, calm, professionalism

### Step 2: Find inspiration

**Don't copy - analyze.** See `docs/inspiration-process.md`.

- Check how the best in the industry do it
- Extract common patterns (what do the best examples have in common?)
- Identify what makes them look professional

### Step 3: Apply fundamentals

**Solid foundations = professional look.** See `docs/design-principles.md`.

- Typography: max 2 fonts, consistent scale, proper line-heights
- Colors: 5-6 color palette with sufficient contrast
- Spacing: systematic (4/8px scale), creates hierarchy
- Hierarchy: clear what's important (squint test)

### Step 4: Add differentiation

**80% fundamentals + 20% uniqueness.** See `docs/differentiation-techniques.md`.

Every design needs a "signature element":
- Non-obvious font (not Inter/Poppins)
- Unusual accent color (not standard blue)
- Characteristic animation or hover effect
- Unique layout element

### Step 5: Validate decisions

Every decision must have justification:
- "Why this font?" → because it fits the tone/industry
- "Why this color?" → because it evokes the right emotions
- "Why this layout?" → because it best presents the content

---

## DaisyUI vs Custom CSS

**Use custom CSS** (default):
- For all projects where appearance matters
- Landing pages, applications, dashboards
- When you want professional, unique results

**Use DaisyUI** only when:
- User explicitly asks for "quick prototype"
- Internal tools where appearance isn't a priority
- Speed is more important than uniqueness

See `docs/custom-components.md` for ready-to-use CSS components.

---

## Content Guidelines

**NO EMOJIS** in UI unless user explicitly requests them. Emojis are a telltale sign of AI-generated content and look unprofessional.

Instead of emojis, use:
- **Icons**: Lucide, Heroicons, Phosphor Icons (via CDN or inline SVG)
- **Images**: Use web search to find relevant professional stock photos
- **Illustrations**: Simple SVG illustrations or CSS shapes
- **Nothing**: Sometimes negative space is better than filler content

---

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.
