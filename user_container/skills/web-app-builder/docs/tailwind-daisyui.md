# Tailwind CSS + DaisyUI Documentation

Tailwind CSS provides utility classes for styling. DaisyUI adds pre-built components on top of Tailwind.

## Installation (CDN)
```html
<!-- DaisyUI (includes Tailwind base styles) -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">

<!-- Tailwind CSS (for utilities) -->
<script src="https://cdn.tailwindcss.com"></script>
```

## HTML Setup
```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My App</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-base-200">
    <!-- Content -->
</body>
</html>
```

---

# Tailwind CSS Utilities

## Layout

### Container
```html
<div class="container mx-auto px-4">Centered content</div>
```

### Flexbox
```html
<!-- Basic flex -->
<div class="flex">
    <div>Item 1</div>
    <div>Item 2</div>
</div>

<!-- Direction -->
<div class="flex flex-col">Vertical</div>
<div class="flex flex-row">Horizontal</div>

<!-- Justify (main axis) -->
<div class="flex justify-start">Left</div>
<div class="flex justify-center">Center</div>
<div class="flex justify-end">Right</div>
<div class="flex justify-between">Space between</div>
<div class="flex justify-around">Space around</div>
<div class="flex justify-evenly">Space evenly</div>

<!-- Align (cross axis) -->
<div class="flex items-start">Top</div>
<div class="flex items-center">Center</div>
<div class="flex items-end">Bottom</div>
<div class="flex items-stretch">Stretch</div>

<!-- Wrap -->
<div class="flex flex-wrap">Wrap items</div>

<!-- Gap -->
<div class="flex gap-2">Small gap</div>
<div class="flex gap-4">Medium gap</div>
<div class="flex gap-x-4 gap-y-2">Different gaps</div>

<!-- Grow/Shrink -->
<div class="flex">
    <div class="flex-1">Grows</div>
    <div class="flex-none">Fixed</div>
</div>
```

### Grid
```html
<!-- Basic grid -->
<div class="grid grid-cols-3 gap-4">
    <div>1</div>
    <div>2</div>
    <div>3</div>
</div>

<!-- Responsive columns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

<!-- Column span -->
<div class="grid grid-cols-4">
    <div class="col-span-2">Spans 2 columns</div>
    <div class="col-span-1">1 column</div>
    <div class="col-span-1">1 column</div>
</div>

<!-- Auto columns -->
<div class="grid grid-cols-[auto_1fr_auto]">
    <div>Auto width</div>
    <div>Takes remaining</div>
    <div>Auto width</div>
</div>
```

### Position
```html
<div class="relative">
    <div class="absolute top-0 right-0">Top right</div>
    <div class="absolute bottom-0 left-0">Bottom left</div>
</div>

<div class="fixed top-0 left-0 w-full">Fixed header</div>
<div class="sticky top-0">Sticky element</div>
```

## Spacing

### Padding
```html
<div class="p-4">All sides</div>
<div class="px-4">Left and right</div>
<div class="py-4">Top and bottom</div>
<div class="pt-4 pb-2 pl-4 pr-2">Individual sides</div>
```

### Margin
```html
<div class="m-4">All sides</div>
<div class="mx-auto">Center horizontally</div>
<div class="my-4">Top and bottom</div>
<div class="mt-4 mb-2">Individual sides</div>
<div class="-mt-4">Negative margin</div>
```

### Space between children
```html
<div class="space-x-4">Horizontal space</div>
<div class="space-y-4">Vertical space</div>
```

## Sizing

### Width
```html
<div class="w-full">Full width</div>
<div class="w-1/2">Half width</div>
<div class="w-1/3">Third width</div>
<div class="w-64">256px</div>
<div class="w-screen">Viewport width</div>
<div class="max-w-md">Max width medium</div>
<div class="min-w-0">Min width 0</div>
```

### Height
```html
<div class="h-full">Full height</div>
<div class="h-screen">Viewport height</div>
<div class="h-64">256px</div>
<div class="min-h-screen">Min viewport height</div>
```

## Typography

### Font Size
```html
<p class="text-xs">Extra small</p>
<p class="text-sm">Small</p>
<p class="text-base">Base (default)</p>
<p class="text-lg">Large</p>
<p class="text-xl">Extra large</p>
<p class="text-2xl">2XL</p>
<p class="text-3xl">3XL</p>
<p class="text-4xl">4XL</p>
```

### Font Weight
```html
<p class="font-thin">Thin</p>
<p class="font-normal">Normal</p>
<p class="font-medium">Medium</p>
<p class="font-semibold">Semibold</p>
<p class="font-bold">Bold</p>
```

### Text Color
```html
<p class="text-gray-500">Gray text</p>
<p class="text-red-500">Red text</p>
<p class="text-blue-600">Blue text</p>
<p class="text-primary">Primary (DaisyUI)</p>
<p class="text-secondary">Secondary (DaisyUI)</p>
```

### Text Alignment
```html
<p class="text-left">Left aligned</p>
<p class="text-center">Centered</p>
<p class="text-right">Right aligned</p>
<p class="text-justify">Justified</p>
```

### Line Height
```html
<p class="leading-none">No extra spacing</p>
<p class="leading-tight">Tight</p>
<p class="leading-normal">Normal</p>
<p class="leading-relaxed">Relaxed</p>
<p class="leading-loose">Loose</p>
```

### Text Overflow
```html
<p class="truncate">Truncate with ellipsis...</p>
<p class="overflow-ellipsis overflow-hidden">Ellipsis</p>
<p class="whitespace-nowrap">No wrap</p>
```

## Colors

### Background
```html
<div class="bg-white">White</div>
<div class="bg-gray-100">Light gray</div>
<div class="bg-blue-500">Blue</div>
<div class="bg-primary">Primary (DaisyUI)</div>
<div class="bg-base-100">Base 100 (DaisyUI)</div>
<div class="bg-base-200">Base 200 (DaisyUI)</div>
<div class="bg-transparent">Transparent</div>
```

### Opacity
```html
<div class="bg-black bg-opacity-50">50% opacity</div>
<div class="opacity-75">75% opacity element</div>
```

## Borders

### Border Width
```html
<div class="border">1px all sides</div>
<div class="border-2">2px</div>
<div class="border-t">Top only</div>
<div class="border-b-2">Bottom 2px</div>
```

### Border Color
```html
<div class="border border-gray-300">Gray border</div>
<div class="border border-primary">Primary border</div>
```

### Border Radius
```html
<div class="rounded">Small radius</div>
<div class="rounded-md">Medium</div>
<div class="rounded-lg">Large</div>
<div class="rounded-xl">Extra large</div>
<div class="rounded-full">Full (circle)</div>
<div class="rounded-t-lg">Top corners only</div>
```

## Shadows
```html
<div class="shadow-sm">Small shadow</div>
<div class="shadow">Default shadow</div>
<div class="shadow-md">Medium shadow</div>
<div class="shadow-lg">Large shadow</div>
<div class="shadow-xl">Extra large shadow</div>
```

## Responsive Design
```html
<!-- Mobile first: base -> sm -> md -> lg -> xl -> 2xl -->
<div class="text-sm md:text-base lg:text-lg">
    Responsive text size
</div>

<div class="flex flex-col md:flex-row">
    Stacks on mobile, row on desktop
</div>

<div class="hidden md:block">
    Hidden on mobile, visible on desktop
</div>

<div class="block md:hidden">
    Visible on mobile only
</div>
```

### Breakpoints
| Prefix | Min Width |
|--------|-----------|
| `sm:` | 640px |
| `md:` | 768px |
| `lg:` | 1024px |
| `xl:` | 1280px |
| `2xl:` | 1536px |

## Hover & States
```html
<button class="bg-blue-500 hover:bg-blue-600">Hover me</button>
<input class="border focus:border-blue-500 focus:ring-2">
<button class="active:bg-blue-700">Active state</button>
<button class="disabled:opacity-50" disabled>Disabled</button>
```

---

# DaisyUI Components

## Buttons
```html
<button class="btn">Default</button>
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-accent">Accent</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-link">Link</button>
<button class="btn btn-outline">Outline</button>
<button class="btn btn-outline btn-primary">Outline Primary</button>

<!-- Sizes -->
<button class="btn btn-xs">Tiny</button>
<button class="btn btn-sm">Small</button>
<button class="btn btn-md">Normal</button>
<button class="btn btn-lg">Large</button>

<!-- States -->
<button class="btn btn-disabled">Disabled</button>
<button class="btn loading">Loading</button>
<button class="btn"><span class="loading loading-spinner"></span>Loading</button>

<!-- Shapes -->
<button class="btn btn-circle">O</button>
<button class="btn btn-square">X</button>
<button class="btn btn-wide">Wide</button>
<button class="btn btn-block">Full Width</button>
```

## Cards
```html
<div class="card bg-base-100 shadow-xl">
    <figure>
        <img src="image.jpg" alt="Image">
    </figure>
    <div class="card-body">
        <h2 class="card-title">Card Title</h2>
        <p>Card description goes here.</p>
        <div class="card-actions justify-end">
            <button class="btn btn-primary">Action</button>
        </div>
    </div>
</div>

<!-- Compact card -->
<div class="card card-compact bg-base-100 shadow-xl">

<!-- Side image -->
<div class="card card-side bg-base-100 shadow-xl">
    <figure><img src="image.jpg" alt="Image"></figure>
    <div class="card-body">
        <h2 class="card-title">Title</h2>
        <p>Description</p>
    </div>
</div>
```

## Form Inputs
```html
<!-- Text Input -->
<input type="text" placeholder="Type here" class="input input-bordered w-full max-w-xs">

<!-- With label -->
<label class="form-control w-full max-w-xs">
    <div class="label">
        <span class="label-text">Name</span>
    </div>
    <input type="text" placeholder="Enter name" class="input input-bordered">
    <div class="label">
        <span class="label-text-alt">Helper text</span>
    </div>
</label>

<!-- Input sizes -->
<input class="input input-xs">
<input class="input input-sm">
<input class="input input-md">
<input class="input input-lg">

<!-- Input colors -->
<input class="input input-primary">
<input class="input input-secondary">
<input class="input input-success">
<input class="input input-warning">
<input class="input input-error">

<!-- Textarea -->
<textarea class="textarea textarea-bordered" placeholder="Bio"></textarea>

<!-- Select -->
<select class="select select-bordered w-full max-w-xs">
    <option disabled selected>Pick one</option>
    <option>Option 1</option>
    <option>Option 2</option>
</select>

<!-- Checkbox -->
<input type="checkbox" class="checkbox">
<input type="checkbox" class="checkbox checkbox-primary">
<input type="checkbox" checked class="checkbox checkbox-success">

<!-- Radio -->
<input type="radio" name="radio-1" class="radio">
<input type="radio" name="radio-1" class="radio radio-primary" checked>

<!-- Toggle -->
<input type="checkbox" class="toggle">
<input type="checkbox" class="toggle toggle-primary" checked>

<!-- Range -->
<input type="range" min="0" max="100" class="range">
<input type="range" min="0" max="100" class="range range-primary" step="25">

<!-- File input -->
<input type="file" class="file-input file-input-bordered w-full max-w-xs">
```

## Modal
```html
<!-- Open modal with button -->
<button class="btn" onclick="my_modal.showModal()">Open Modal</button>

<dialog id="my_modal" class="modal">
    <div class="modal-box">
        <h3 class="font-bold text-lg">Hello!</h3>
        <p class="py-4">Modal content here.</p>
        <div class="modal-action">
            <form method="dialog">
                <button class="btn">Close</button>
            </form>
        </div>
    </div>
    <form method="dialog" class="modal-backdrop">
        <button>close</button>
    </form>
</dialog>
```

## Navbar
```html
<div class="navbar bg-base-100">
    <div class="flex-1">
        <a class="btn btn-ghost text-xl">My App</a>
    </div>
    <div class="flex-none">
        <ul class="menu menu-horizontal px-1">
            <li><a>Link 1</a></li>
            <li><a>Link 2</a></li>
        </ul>
    </div>
</div>

<!-- With dropdown -->
<div class="navbar bg-base-100">
    <div class="flex-1">
        <a class="btn btn-ghost text-xl">Logo</a>
    </div>
    <div class="flex-none">
        <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-ghost btn-circle avatar">
                <div class="w-10 rounded-full">
                    <img alt="Avatar" src="avatar.jpg">
                </div>
            </div>
            <ul tabindex="0" class="menu menu-sm dropdown-content bg-base-100 rounded-box z-[1] mt-3 w-52 p-2 shadow">
                <li><a>Profile</a></li>
                <li><a>Settings</a></li>
                <li><a>Logout</a></li>
            </ul>
        </div>
    </div>
</div>
```

## Tabs
```html
<div role="tablist" class="tabs tabs-boxed">
    <a role="tab" class="tab">Tab 1</a>
    <a role="tab" class="tab tab-active">Tab 2</a>
    <a role="tab" class="tab">Tab 3</a>
</div>

<!-- Lifted tabs -->
<div role="tablist" class="tabs tabs-lifted">
    <a role="tab" class="tab">Tab 1</a>
    <a role="tab" class="tab tab-active">Tab 2</a>
    <a role="tab" class="tab">Tab 3</a>
</div>

<!-- Bordered tabs -->
<div role="tablist" class="tabs tabs-bordered">
    <a role="tab" class="tab">Tab 1</a>
    <a role="tab" class="tab tab-active">Tab 2</a>
    <a role="tab" class="tab">Tab 3</a>
</div>
```

## Dropdown
```html
<div class="dropdown">
    <div tabindex="0" role="button" class="btn m-1">Click</div>
    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
        <li><a>Item 1</a></li>
        <li><a>Item 2</a></li>
    </ul>
</div>

<!-- Dropdown positions -->
<div class="dropdown dropdown-end">    <!-- Right aligned -->
<div class="dropdown dropdown-top">    <!-- Opens upward -->
<div class="dropdown dropdown-left">   <!-- Opens to the left -->
<div class="dropdown dropdown-right">  <!-- Opens to the right -->
<div class="dropdown dropdown-hover">  <!-- Opens on hover -->
```

## Alert
```html
<div role="alert" class="alert">
    <span>Default alert</span>
</div>

<div role="alert" class="alert alert-info">
    <span>Info message</span>
</div>

<div role="alert" class="alert alert-success">
    <span>Success!</span>
</div>

<div role="alert" class="alert alert-warning">
    <span>Warning!</span>
</div>

<div role="alert" class="alert alert-error">
    <span>Error!</span>
</div>
```

## Badge
```html
<span class="badge">Badge</span>
<span class="badge badge-primary">Primary</span>
<span class="badge badge-secondary">Secondary</span>
<span class="badge badge-outline">Outline</span>
<span class="badge badge-lg">Large</span>
<span class="badge badge-sm">Small</span>
```

## Loading Indicators
```html
<span class="loading loading-spinner loading-xs"></span>
<span class="loading loading-spinner loading-sm"></span>
<span class="loading loading-spinner loading-md"></span>
<span class="loading loading-spinner loading-lg"></span>

<span class="loading loading-dots loading-md"></span>
<span class="loading loading-ring loading-md"></span>
<span class="loading loading-ball loading-md"></span>
<span class="loading loading-bars loading-md"></span>
<span class="loading loading-infinity loading-md"></span>
```

## Progress
```html
<progress class="progress w-56" value="40" max="100"></progress>
<progress class="progress progress-primary w-56" value="70" max="100"></progress>
<progress class="progress progress-success w-56" value="100" max="100"></progress>
```

## Avatar
```html
<div class="avatar">
    <div class="w-24 rounded">
        <img src="avatar.jpg">
    </div>
</div>

<!-- Rounded -->
<div class="avatar">
    <div class="w-24 rounded-full">
        <img src="avatar.jpg">
    </div>
</div>

<!-- Placeholder (no image) -->
<div class="avatar placeholder">
    <div class="bg-neutral text-neutral-content w-24 rounded-full">
        <span class="text-3xl">JD</span>
    </div>
</div>

<!-- Avatar group -->
<div class="avatar-group -space-x-6">
    <div class="avatar"><div class="w-12"><img src="1.jpg"></div></div>
    <div class="avatar"><div class="w-12"><img src="2.jpg"></div></div>
    <div class="avatar placeholder">
        <div class="bg-neutral text-neutral-content w-12">
            <span>+99</span>
        </div>
    </div>
</div>
```

## Table
```html
<div class="overflow-x-auto">
    <table class="table">
        <thead>
            <tr>
                <th></th>
                <th>Name</th>
                <th>Job</th>
                <th>Favorite Color</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <th>1</th>
                <td>John</td>
                <td>Developer</td>
                <td>Blue</td>
            </tr>
            <tr class="hover">  <!-- Hover effect -->
                <th>2</th>
                <td>Jane</td>
                <td>Designer</td>
                <td>Purple</td>
            </tr>
        </tbody>
    </table>
</div>

<!-- Zebra striped -->
<table class="table table-zebra">

<!-- Compact -->
<table class="table table-xs">
<table class="table table-sm">
```

## Toast
```html
<div class="toast toast-end">
    <div class="alert alert-success">
        <span>Message sent.</span>
    </div>
</div>

<!-- Positions -->
<div class="toast toast-top toast-start">
<div class="toast toast-top toast-center">
<div class="toast toast-top toast-end">
<div class="toast toast-middle toast-start">
<div class="toast toast-middle toast-center">
<div class="toast toast-middle toast-end">
<div class="toast toast-bottom toast-start">
<div class="toast toast-bottom toast-center">
<div class="toast toast-bottom toast-end">
```

## Stats
```html
<div class="stats shadow">
    <div class="stat">
        <div class="stat-figure text-primary">
            <!-- Icon here -->
        </div>
        <div class="stat-title">Total Users</div>
        <div class="stat-value">25.6K</div>
        <div class="stat-desc">21% more than last month</div>
    </div>

    <div class="stat">
        <div class="stat-title">Total Revenue</div>
        <div class="stat-value text-primary">$89,400</div>
        <div class="stat-desc">Jan 1st - Feb 1st</div>
    </div>
</div>
```

## Menu (Sidebar)
```html
<ul class="menu bg-base-200 rounded-box w-56">
    <li><a>Item 1</a></li>
    <li><a>Item 2</a></li>
    <li>
        <details open>
            <summary>Parent</summary>
            <ul>
                <li><a>Submenu 1</a></li>
                <li><a>Submenu 2</a></li>
            </ul>
        </details>
    </li>
</ul>
```

## Drawer (Sidebar Layout)
```html
<div class="drawer lg:drawer-open">
    <input id="my-drawer" type="checkbox" class="drawer-toggle">
    <div class="drawer-content">
        <!-- Page content -->
        <label for="my-drawer" class="btn btn-primary drawer-button lg:hidden">
            Open Menu
        </label>
    </div>
    <div class="drawer-side">
        <label for="my-drawer" class="drawer-overlay"></label>
        <ul class="menu bg-base-200 text-base-content min-h-full w-80 p-4">
            <li><a>Sidebar Item 1</a></li>
            <li><a>Sidebar Item 2</a></li>
        </ul>
    </div>
</div>
```

---

## Theming

### Built-in Themes
```html
<html data-theme="light">    <!-- Light theme -->
<html data-theme="dark">     <!-- Dark theme -->
<html data-theme="cupcake">
<html data-theme="bumblebee">
<html data-theme="emerald">
<html data-theme="corporate">
<html data-theme="synthwave">
<html data-theme="retro">
<html data-theme="cyberpunk">
<html data-theme="valentine">
<html data-theme="halloween">
<html data-theme="garden">
<html data-theme="forest">
<html data-theme="aqua">
<html data-theme="lofi">
<html data-theme="pastel">
<html data-theme="fantasy">
<html data-theme="wireframe">
<html data-theme="black">
<html data-theme="luxury">
<html data-theme="dracula">
<html data-theme="cmyk">
<html data-theme="autumn">
<html data-theme="business">
<html data-theme="acid">
<html data-theme="lemonade">
<html data-theme="night">
<html data-theme="coffee">
<html data-theme="winter">
<html data-theme="dim">
<html data-theme="nord">
<html data-theme="sunset">
```

### Toggle Dark Mode with Vue 3
```html
<div id="app">
    <label class="swap swap-rotate">
        <input type="checkbox" :checked="dark" @change="toggleDark">
        <span class="swap-on">Dark</span>
        <span class="swap-off">Light</span>
    </label>
</div>

<script>
const { createApp, ref, onMounted } = Vue;
createApp({
    setup() {
        const dark = ref(localStorage.getItem('theme') === 'dark');
        function toggleDark() {
            dark.value = !dark.value;
            localStorage.setItem('theme', dark.value ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', dark.value ? 'dark' : 'light');
        }
        onMounted(() => {
            document.documentElement.setAttribute('data-theme', dark.value ? 'dark' : 'light');
        });
        return { dark, toggleDark };
    }
}).mount('#app');
</script>
```

### Theme Colors
DaisyUI provides semantic color classes:

| Class | Usage |
|-------|-------|
| `primary` | Primary brand color |
| `secondary` | Secondary color |
| `accent` | Accent color |
| `neutral` | Neutral/gray |
| `base-100` | Page background |
| `base-200` | Slightly darker background |
| `base-300` | Even darker background |
| `info` | Info messages |
| `success` | Success states |
| `warning` | Warning states |
| `error` | Error states |

Usage:
```html
<div class="bg-primary text-primary-content">Primary background</div>
<div class="bg-base-100">Base background</div>
<div class="text-primary">Primary text</div>
<div class="border-secondary">Secondary border</div>
```
