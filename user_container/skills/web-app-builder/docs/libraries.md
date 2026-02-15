# Additional Libraries

This document covers optional libraries you can add to your web apps for specific functionality.

---

## Chart.js (Simple Charts)

Best for: Basic charts, dashboards, quick visualizations.

### CDN
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### Basic Usage
```html
<canvas id="myChart" width="400" height="200"></canvas>

<script>
const ctx = document.getElementById('myChart').getContext('2d');
const myChart = new Chart(ctx, {
    type: 'bar',  // 'line', 'pie', 'doughnut', 'radar', 'polarArea', 'bubble', 'scatter'
    data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{
            label: 'Sales',
            data: [12, 19, 3, 5, 2, 3],
            backgroundColor: [
                'rgba(255, 99, 132, 0.2)',
                'rgba(54, 162, 235, 0.2)',
                'rgba(255, 206, 86, 0.2)',
                'rgba(75, 192, 192, 0.2)',
                'rgba(153, 102, 255, 0.2)',
                'rgba(255, 159, 64, 0.2)'
            ],
            borderColor: [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)',
                'rgba(255, 159, 64, 1)'
            ],
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});
</script>
```

### Line Chart
```javascript
new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        datasets: [{
            label: 'Views',
            data: [65, 59, 80, 81, 56],
            fill: false,
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
        }]
    }
});
```

### Pie/Doughnut Chart
```javascript
new Chart(ctx, {
    type: 'doughnut',  // or 'pie'
    data: {
        labels: ['Red', 'Blue', 'Yellow'],
        datasets: [{
            data: [300, 50, 100],
            backgroundColor: ['#ff6384', '#36a2eb', '#ffce56']
        }]
    }
});
```

### With Vue 3
```html
<div id="app">
    <canvas ref="chartRef"></canvas>
    <button @click="updateData([40, 50, 60])">Update</button>
</div>

<script>
const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        const chartRef = ref(null);
        let chartInstance = null;

        onMounted(() => {
            chartInstance = new Chart(chartRef.value, {
                type: 'bar',
                data: {
                    labels: ['A', 'B', 'C'],
                    datasets: [{
                        label: 'Data',
                        data: [10, 20, 30]
                    }]
                }
            });
        });

        function updateData(newData) {
            chartInstance.data.datasets[0].data = newData;
            chartInstance.update();
        }

        return { chartRef, updateData };
    }
}).mount('#app');
</script>
```

---

## ECharts (Advanced Charts)

Best for: Complex visualizations, interactive charts, large datasets, geographic maps.

### CDN
```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
```

### Basic Usage
```html
<div id="chart" style="width: 600px; height: 400px;"></div>

<script>
const chart = echarts.init(document.getElementById('chart'));

chart.setOption({
    title: { text: 'Sales Report' },
    tooltip: {},
    xAxis: {
        data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    },
    yAxis: {},
    series: [{
        name: 'Sales',
        type: 'bar',
        data: [5, 20, 36, 10, 10]
    }]
});

// Responsive resize
window.addEventListener('resize', () => chart.resize());
</script>
```

### Line Chart with Area
```javascript
chart.setOption({
    xAxis: { type: 'category', data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] },
    yAxis: { type: 'value' },
    series: [{
        data: [820, 932, 901, 934, 1290],
        type: 'line',
        areaStyle: {},
        smooth: true
    }]
});
```

### Pie Chart
```javascript
chart.setOption({
    series: [{
        type: 'pie',
        radius: '50%',
        data: [
            { value: 1048, name: 'Search' },
            { value: 735, name: 'Direct' },
            { value: 580, name: 'Email' },
            { value: 484, name: 'Social' }
        ],
        emphasis: {
            itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
        }
    }]
});
```

---

## Leaflet (Maps)

Best for: Interactive maps, markers, polygons, open-source.

### CDN
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1/dist/leaflet.js"></script>
```

### Basic Map
```html
<div id="map" style="height: 400px;"></div>

<script>
const map = L.map('map').setView([51.505, -0.09], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
</script>
```

### Add Marker
```javascript
const marker = L.marker([51.5, -0.09]).addTo(map);
marker.bindPopup('<b>Hello!</b><br>I am a popup.').openPopup();
```

### Add Circle
```javascript
L.circle([51.508, -0.11], {
    color: 'red',
    fillColor: '#f03',
    fillOpacity: 0.5,
    radius: 500
}).addTo(map);
```

### Add Polygon
```javascript
L.polygon([
    [51.509, -0.08],
    [51.503, -0.06],
    [51.51, -0.047]
]).addTo(map);
```

### Click Events
```javascript
map.on('click', (e) => {
    L.marker(e.latlng).addTo(map);
});
```

### With Vue 3
```html
<div id="app">
    <div ref="mapRef" style="height: 400px;"></div>
    <button @click="addMarker()" class="btn btn-primary mt-2">Add Marker</button>
</div>

<script>
const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        const mapRef = ref(null);
        let map = null;
        const markers = [];

        onMounted(() => {
            map = L.map(mapRef.value).setView([51.505, -0.09], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap'
            }).addTo(map);
        });

        function addMarker() {
            const center = map.getCenter();
            const marker = L.marker(center).addTo(map);
            markers.push(marker);
        }

        return { mapRef, addMarker };
    }
}).mount('#app');
</script>
```

---

## Quill (Rich Text Editor)

Best for: WYSIWYG content editing, blog posts, comments.

### CDN
```html
<link href="https://cdn.jsdelivr.net/npm/quill@2/dist/quill.snow.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/quill@2/dist/quill.js"></script>
```

### Basic Editor
```html
<div id="editor"></div>

<script>
const quill = new Quill('#editor', {
    theme: 'snow',
    placeholder: 'Write something...',
    modules: {
        toolbar: [
            ['bold', 'italic', 'underline', 'strike'],
            ['blockquote', 'code-block'],
            [{ 'header': 1 }, { 'header': 2 }],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            [{ 'color': [] }, { 'background': [] }],
            ['link', 'image'],
            ['clean']
        ]
    }
});

// Get content
const html = quill.root.innerHTML;
const delta = quill.getContents();

// Set content
quill.setContents(delta);
quill.root.innerHTML = html;

// Listen for changes
quill.on('text-change', (delta, oldDelta, source) => {
    console.log('Content changed:', quill.root.innerHTML);
});
</script>
```

### With Vue 3
```html
<div id="app">
    <div ref="editorRef"></div>
    <button @click="save()" class="btn btn-primary mt-2">Save</button>
</div>

<script>
const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        const editorRef = ref(null);
        let quill = null;

        onMounted(() => {
            quill = new Quill(editorRef.value, {
                theme: 'snow',
                modules: {
                    toolbar: [['bold', 'italic'], ['link', 'image']]
                }
            });
        });

        function getContent() { return quill.root.innerHTML; }
        function setContent(html) { quill.root.innerHTML = html; }

        function save() {
            const content = getContent();
            // Save to database
        }

        return { editorRef, save };
    }
}).mount('#app');
</script>
```

---

## SortableJS (Drag & Drop)

Best for: Sortable lists, kanban boards, drag-and-drop interfaces.

### CDN
```html
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1/Sortable.min.js"></script>
```

### Basic Sortable List
```html
<ul id="items">
    <li>Item 1</li>
    <li>Item 2</li>
    <li>Item 3</li>
</ul>

<script>
new Sortable(document.getElementById('items'), {
    animation: 150,
    ghostClass: 'opacity-50'
});
</script>
```

### With Handle
```html
<ul id="items">
    <li><span class="handle">☰</span> Item 1</li>
    <li><span class="handle">☰</span> Item 2</li>
</ul>

<script>
new Sortable(document.getElementById('items'), {
    handle: '.handle',
    animation: 150
});
</script>
```

### Between Lists (Kanban)
```html
<div class="flex gap-4">
    <div>
        <h3>Todo</h3>
        <ul id="todo" class="sortable-list"></ul>
    </div>
    <div>
        <h3>Done</h3>
        <ul id="done" class="sortable-list"></ul>
    </div>
</div>

<script>
document.querySelectorAll('.sortable-list').forEach(list => {
    new Sortable(list, {
        group: 'shared',
        animation: 150,
        onEnd: (evt) => {
            console.log('Moved from', evt.from.id, 'to', evt.to.id);
            console.log('Old index:', evt.oldIndex, 'New index:', evt.newIndex);
        }
    });
});
</script>
```

### With Vue 3
```html
<div id="app">
    <div class="flex gap-4">
        <div v-for="column in columns" :key="column.id">
            <h3 class="font-bold mb-2">{{ column.name }}</h3>
            <ul :ref="el => columnRefs[column.id] = el" class="min-h-[100px] bg-base-200 p-2 rounded">
                <li v-for="item in column.items" :key="item.id" :data-id="item.id"
                    class="p-2 bg-base-100 rounded mb-1 cursor-move">
                    {{ item.title }}
                </li>
            </ul>
        </div>
    </div>
</div>

<script>
const { createApp, ref, reactive, onMounted, nextTick } = Vue;

createApp({
    setup() {
        const columns = reactive([
            { id: 'todo', name: 'Todo', items: [{ id: 1, title: 'Task 1' }] },
            { id: 'done', name: 'Done', items: [] }
        ]);
        const columnRefs = {};

        onMounted(async () => {
            await nextTick();
            Object.values(columnRefs).forEach(el => {
                new Sortable(el, {
                    group: 'kanban',
                    animation: 150,
                    onEnd: handleMove
                });
            });
        });

        function handleMove(evt) {
            // Update data model based on DOM changes
        }

        return { columns, columnRefs, handleMove };
    }
}).mount('#app');
</script>
```

---

## Day.js (Date Handling)

Best for: Date formatting, manipulation, relative time.

### CDN
```html
<script src="https://cdn.jsdelivr.net/npm/dayjs@1/dayjs.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dayjs@1/plugin/relativeTime.js"></script>
<script>dayjs.extend(dayjs_plugin_relativeTime);</script>
```

### Basic Usage
```javascript
// Current date/time
dayjs();

// Parse date
dayjs('2024-01-15');
dayjs('2024-01-15T10:30:00');

// Format
dayjs().format('YYYY-MM-DD');           // 2024-01-15
dayjs().format('DD/MM/YYYY');           // 15/01/2024
dayjs().format('MMMM D, YYYY');         // January 15, 2024
dayjs().format('h:mm A');               // 2:30 PM
dayjs().format('dddd');                 // Monday

// Manipulation
dayjs().add(7, 'day');
dayjs().subtract(1, 'month');
dayjs().startOf('month');
dayjs().endOf('week');

// Comparison
dayjs('2024-01-15').isBefore('2024-01-20');
dayjs('2024-01-15').isAfter('2024-01-10');
dayjs('2024-01-15').isSame('2024-01-15', 'day');

// Relative time (requires plugin)
dayjs('2024-01-10').fromNow();          // 5 days ago
dayjs().to(dayjs('2024-01-20'));        // in 5 days
```

---

## jsPDF (PDF Export)

Best for: Generating PDFs from JavaScript, reports, invoices.

### CDN
```html
<script src="https://cdn.jsdelivr.net/npm/jspdf@2/dist/jspdf.umd.min.js"></script>
```

### Basic PDF
```javascript
const { jsPDF } = window.jspdf;
const doc = new jsPDF();

doc.text('Hello World!', 10, 10);
doc.save('document.pdf');
```

### With Styling
```javascript
const doc = new jsPDF();

// Title
doc.setFontSize(22);
doc.text('Invoice', 105, 20, { align: 'center' });

// Content
doc.setFontSize(12);
doc.text('Customer: John Doe', 20, 40);
doc.text('Date: ' + new Date().toLocaleDateString(), 20, 50);

// Line
doc.line(20, 55, 190, 55);

// Table-like content
let y = 65;
const items = [
    { name: 'Product 1', price: 29.99 },
    { name: 'Product 2', price: 49.99 }
];

items.forEach(item => {
    doc.text(item.name, 20, y);
    doc.text('$' + item.price.toFixed(2), 170, y, { align: 'right' });
    y += 10;
});

// Total
doc.setFontSize(14);
doc.text('Total: $79.98', 170, y + 10, { align: 'right' });

doc.save('invoice.pdf');
```

### HTML to PDF (with html2canvas)
```html
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1/dist/html2canvas.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jspdf@2/dist/jspdf.umd.min.js"></script>

<script>
async function exportToPDF(elementId) {
    const element = document.getElementById(elementId);
    const canvas = await html2canvas(element);
    const imgData = canvas.toDataURL('image/png');

    const pdf = new jspdf.jsPDF();
    const imgWidth = 190;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, imgHeight);
    pdf.save('export.pdf');
}
</script>
```

---

## Canvas Confetti (Celebrations)

Best for: Success animations, celebrations, gamification.

### CDN
```html
<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1/dist/confetti.browser.min.js"></script>
```

### Basic Usage
```javascript
// Simple burst
confetti();

// Custom options
confetti({
    particleCount: 100,
    spread: 70,
    origin: { y: 0.6 }
});

// From a specific point
confetti({
    particleCount: 100,
    startVelocity: 30,
    spread: 360,
    origin: {
        x: Math.random(),
        y: Math.random() - 0.2
    }
});
```

### Fireworks Effect
```javascript
function fireworks() {
    const duration = 3 * 1000;
    const end = Date.now() + duration;

    (function frame() {
        confetti({
            particleCount: 2,
            angle: 60,
            spread: 55,
            origin: { x: 0 }
        });
        confetti({
            particleCount: 2,
            angle: 120,
            spread: 55,
            origin: { x: 1 }
        });

        if (Date.now() < end) {
            requestAnimationFrame(frame);
        }
    }());
}
```

### On Button Click
```html
<button onclick="confetti()">Celebrate!</button>
```

---

## Heroicons (Icons)

Best for: UI icons, clean SVG icons.

### Usage
Copy SVG directly from [heroicons.com](https://heroicons.com).

```html
<!-- Outline style (24x24) -->
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
</svg>

<!-- Solid style (24x24) -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6">
    <path fill-rule="evenodd" d="M12 3.75a.75.75 0 01.75.75v6.75h6.75a.75.75 0 010 1.5h-6.75v6.75a.75.75 0 01-1.5 0v-6.75H4.5a.75.75 0 010-1.5h6.75V4.5a.75.75 0 01.75-.75z" clip-rule="evenodd" />
</svg>

<!-- Mini style (20x20) -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
    <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
</svg>
```

### Common Icons
```html
<!-- Check -->
<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
</svg>

<!-- X/Close -->
<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
</svg>

<!-- Menu (hamburger) -->
<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
</svg>

<!-- Search -->
<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
</svg>

<!-- User -->
<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
</svg>

<!-- Home -->
<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
</svg>
```

---

## Canvas API (Drawing)

For custom graphics, animations, and image manipulation.

### Basic Canvas
```html
<canvas id="canvas" width="400" height="300"></canvas>

<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Rectangle
ctx.fillStyle = 'blue';
ctx.fillRect(10, 10, 100, 50);

// Outlined rectangle
ctx.strokeStyle = 'red';
ctx.strokeRect(130, 10, 100, 50);

// Line
ctx.beginPath();
ctx.moveTo(10, 100);
ctx.lineTo(200, 100);
ctx.stroke();

// Circle
ctx.beginPath();
ctx.arc(100, 180, 40, 0, Math.PI * 2);
ctx.fillStyle = 'green';
ctx.fill();

// Text
ctx.font = '20px Arial';
ctx.fillStyle = 'black';
ctx.fillText('Hello Canvas!', 10, 260);
</script>
```

### Drawing App Example
```html
<canvas id="drawingCanvas" width="800" height="600" style="border: 1px solid black;"></canvas>

<script>
const canvas = document.getElementById('drawingCanvas');
const ctx = canvas.getContext('2d');
let isDrawing = false;
let lastX = 0;
let lastY = 0;

canvas.addEventListener('mousedown', (e) => {
    isDrawing = true;
    [lastX, lastY] = [e.offsetX, e.offsetY];
});

canvas.addEventListener('mousemove', (e) => {
    if (!isDrawing) return;
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
    [lastX, lastY] = [e.offsetX, e.offsetY];
});

canvas.addEventListener('mouseup', () => isDrawing = false);
canvas.addEventListener('mouseout', () => isDrawing = false);
</script>
```

### Export Canvas as Image
```javascript
// As data URL
const dataURL = canvas.toDataURL('image/png');

// Download
const link = document.createElement('a');
link.download = 'drawing.png';
link.href = canvas.toDataURL();
link.click();
```

---

## html2canvas (Screenshot)

Capture HTML elements as images.

### CDN
```html
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1/dist/html2canvas.min.js"></script>
```

### Basic Usage
```javascript
async function captureElement(elementId) {
    const element = document.getElementById(elementId);
    const canvas = await html2canvas(element);

    // Display
    document.body.appendChild(canvas);

    // Download
    const link = document.createElement('a');
    link.download = 'screenshot.png';
    link.href = canvas.toDataURL();
    link.click();
}
```

### With Options
```javascript
const canvas = await html2canvas(element, {
    scale: 2,              // Higher quality
    backgroundColor: '#fff',
    logging: false,
    useCORS: true          // For external images
});
```
