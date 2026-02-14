# Custom CSS Components

Ready-to-use component patterns without DaisyUI. Copy and adapt these for distinctive designs.

---

## Buttons

### Solid Button (Versatile)
```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  font-weight: 500;
  font-size: 14px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--accent);
  color: white;
}
.btn-primary:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}
.btn-secondary:hover {
  background: var(--border);
}
```

### Ghost Button
```css
.btn-ghost {
  background: transparent;
  color: var(--text);
  padding: 12px 24px;
  border: none;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-ghost:hover {
  background: rgba(0, 0, 0, 0.05);
}
```

### Pill Button
```css
.btn-pill {
  padding: 10px 28px;
  border-radius: 50px;
  font-weight: 500;
  background: var(--accent);
  color: white;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-pill:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}
```

### Icon Button
```css
.btn-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: transparent;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.2s;
}
.btn-icon:hover {
  background: var(--surface);
  border-color: var(--text);
}
```

---

## Cards

### Basic Card
```css
.card {
  background: var(--surface, white);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  margin-bottom: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.card-body {
  color: var(--text-muted);
  line-height: 1.6;
}

.card-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
```

### Hover Lift Card
```css
.card-lift {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  cursor: pointer;
}
.card-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
}
```

### Bordered Card
```css
.card-bordered {
  background: white;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  transition: border-color 0.2s;
}
.card-bordered:hover {
  border-color: var(--accent);
}
```

### Image Card
```css
.card-image {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-image img {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.card-image-content {
  padding: 20px;
}
```

---

## Form Inputs

### Text Input
```css
.input {
  width: 100%;
  padding: 12px 16px;
  font-size: 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
  transition: all 0.2s;
}
.input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.1);
}
.input::placeholder {
  color: var(--text-muted);
}
```

### Input with Label
```css
.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--text);
}

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
```

### Floating Label Input
```css
.input-floating {
  position: relative;
}

.input-floating input {
  width: 100%;
  padding: 20px 16px 8px;
  font-size: 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
}

.input-floating label {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  color: var(--text-muted);
  pointer-events: none;
  transition: all 0.2s;
}

.input-floating input:focus + label,
.input-floating input:not(:placeholder-shown) + label {
  top: 12px;
  font-size: 12px;
  color: var(--accent);
}
```

### Checkbox
```css
.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.checkbox-wrapper input:checked + .checkbox {
  background: var(--accent);
  border-color: var(--accent);
}

.checkbox-wrapper input:checked + .checkbox::after {
  content: '✓';
  color: white;
  font-size: 14px;
}

.checkbox-wrapper input {
  display: none;
}
```

### Toggle Switch
```css
.toggle {
  position: relative;
  width: 48px;
  height: 26px;
  background: var(--border);
  border-radius: 13px;
  cursor: pointer;
  transition: background 0.3s;
}

.toggle::after {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  background: white;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: transform 0.3s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.toggle.active {
  background: var(--accent);
}

.toggle.active::after {
  transform: translateX(22px);
}
```

---

## Navigation

### Simple Navbar
```css
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid var(--border);
}

.navbar-brand {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  text-decoration: none;
}

.navbar-nav {
  display: flex;
  gap: 32px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-link {
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.nav-link:hover,
.nav-link.active {
  color: var(--accent);
}
```

### Tab Navigation
```css
.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
}

.tab {
  padding: 12px 20px;
  font-weight: 500;
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: -1px;
}

.tab:hover {
  color: var(--text);
}

.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
```

### Sidebar Navigation
```css
.sidebar {
  width: 260px;
  background: var(--surface);
  padding: 20px 0;
  height: 100vh;
}

.sidebar-section {
  margin-bottom: 24px;
}

.sidebar-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  padding: 0 20px;
  margin-bottom: 8px;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  color: var(--text);
  text-decoration: none;
  transition: background 0.2s;
}

.sidebar-link:hover {
  background: rgba(0, 0, 0, 0.05);
}

.sidebar-link.active {
  background: var(--accent);
  color: white;
}
```

---

## Modals

### Basic Modal
```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s;
}

.modal-overlay.active {
  opacity: 1;
  visibility: visible;
}

.modal {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow: auto;
  transform: scale(0.9) translateY(20px);
  transition: transform 0.3s;
}

.modal-overlay.active .modal {
  transform: scale(1) translateY(0);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--text-muted);
}

.modal-body {
  padding: 24px;
}

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
}
```

---

## Alerts/Notifications

### Alert Box
```css
.alert {
  padding: 16px 20px;
  border-radius: 8px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.alert-success {
  background: #ECFDF5;
  color: #065F46;
  border: 1px solid #A7F3D0;
}

.alert-error {
  background: #FEF2F2;
  color: #991B1B;
  border: 1px solid #FECACA;
}

.alert-warning {
  background: #FFFBEB;
  color: #92400E;
  border: 1px solid #FDE68A;
}

.alert-info {
  background: #EFF6FF;
  color: #1E40AF;
  border: 1px solid #BFDBFE;
}
```

### Toast Notification
```css
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: var(--text);
  color: white;
  padding: 16px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 12px;
  transform: translateY(100px);
  opacity: 0;
  transition: all 0.3s ease;
}

.toast.show {
  transform: translateY(0);
  opacity: 1;
}
```

---

## Badges & Tags

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 50px;
  background: var(--surface);
  color: var(--text);
}

.badge-primary {
  background: var(--accent);
  color: white;
}

.badge-success {
  background: #ECFDF5;
  color: #065F46;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  margin-right: 6px;
}
```

---

## Animations & Effects

### Fade In
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.fade-in {
  animation: fadeIn 0.3s ease;
}
```

### Slide Up
```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.slide-up {
  animation: slideUp 0.4s ease;
}
```

### Staggered Reveal
```css
.stagger-item {
  opacity: 0;
  transform: translateY(20px);
  animation: slideUp 0.4s ease forwards;
}
.stagger-item:nth-child(1) { animation-delay: 0.1s; }
.stagger-item:nth-child(2) { animation-delay: 0.2s; }
.stagger-item:nth-child(3) { animation-delay: 0.3s; }
.stagger-item:nth-child(4) { animation-delay: 0.4s; }
.stagger-item:nth-child(5) { animation-delay: 0.5s; }
```

### Pulse
```css
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
.pulse {
  animation: pulse 2s ease-in-out infinite;
}
```

### Skeleton Loading
```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--surface) 25%,
    rgba(0, 0, 0, 0.05) 50%,
    var(--surface) 75%
  );
  background-size: 200% 100%;
  animation: skeleton 1.5s infinite;
  border-radius: 4px;
}

@keyframes skeleton {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## Layout Helpers

### Container
```css
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.container-sm { max-width: 640px; }
.container-md { max-width: 768px; }
.container-lg { max-width: 1024px; }
.container-xl { max-width: 1280px; }
```

### Flex Utilities
```css
.flex { display: flex; }
.flex-col { flex-direction: column; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.gap-6 { gap: 24px; }
```

### Grid
```css
.grid {
  display: grid;
  gap: 24px;
}
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }

@media (max-width: 768px) {
  .grid-2, .grid-3, .grid-4 {
    grid-template-columns: 1fr;
  }
}
```

---

## Background Patterns

### Dot Pattern
```css
.bg-dots {
  background-image: radial-gradient(
    circle,
    var(--border) 1px,
    transparent 1px
  );
  background-size: 20px 20px;
}
```

### Grid Pattern
```css
.bg-grid {
  background-image:
    linear-gradient(var(--border) 1px, transparent 1px),
    linear-gradient(90deg, var(--border) 1px, transparent 1px);
  background-size: 40px 40px;
}
```

### Gradient Mesh
```css
.bg-mesh {
  background:
    radial-gradient(at 40% 20%, var(--accent) 0px, transparent 50%),
    radial-gradient(at 80% 0%, var(--accent2) 0px, transparent 50%),
    radial-gradient(at 0% 50%, var(--accent) 0px, transparent 50%),
    radial-gradient(at 80% 50%, var(--accent2) 0px, transparent 50%),
    radial-gradient(at 0% 100%, var(--accent) 0px, transparent 50%);
  opacity: 0.15;
}
```

### Noise Texture
```css
.bg-noise::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  opacity: 0.05;
  pointer-events: none;
}
```
