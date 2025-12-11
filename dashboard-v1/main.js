import Chart from 'chart.js/auto';

/**
 * @typedef {Object} HealthRecord
 * @property {string} date - Date string in YYYY-MM-DD format
 * @property {number|null} resting_bpm - Resting Heart Rate (bpm)
 * @property {number|null} weight - Weight in Kg
 * @property {number|null} bmi - Body Mass Index
 * @property {number} calories_total - Total daily energy expenditure
 * @property {number} bmr - Basal Metabolic Rate (Calculated via Mifflin-St Jeor)
 * @property {number} active_calories - Calories burned above BMR
 * @property {number} intensity_index - Intensity factor (Active Cals / Active Mins)
 * @property {number|null} overall_score - Fitbit Sleep Score (0-100)
 * @property {number} very_active_minutes - Minutes in peak zone
 * @property {number} moderately_active_minutes - Minutes in cardio zone
 * @property {number} lightly_active_minutes - Minutes in fat burn zone
 * @property {number} sedentary_minutes - Minutes inactive
 * @property {number|null} readiness_raw - Calculated Z-Score for readiness
 */

// Configuration
const DATA_URL = './dashboard_data.json';

// Global State

/** @type {HealthRecord[]} Store full dataset loaded from JSON */
let allData = [];

/** @type {Object.<string, Chart>} Registry of active chart instances to handle cleanup */
const charts = {};
// --- Helper Functions ---

/**
 * Calculates the average of a specific numeric property in the dataset.
 * Automatically filters out null or undefined values.
 * @param {HealthRecord[]} data - The array of health records
 * @param {keyof HealthRecord} key - The property name to average (e.g., 'resting_bpm')
 * @returns {string} The average value formatted to 1 decimal place, or '--' if no data.
 */
const calculateAverage = (data, key) => {
	const validData = data.filter(d => d[key] !== null && d[key] !== undefined);
	if (validData.length === 0) return '--';
	const sum = validData.reduce((acc, curr) => acc + (curr[key] || 0), 0);
	return (sum / validData.length).toFixed(1);
};

// --- Main Logic ---

/**
 * Bootstraps the dashboard application.
 * 1. Fetches data from local JSON.
 * 2. Initializes Date Picker constraints (min/max).
 * 3. Sets up event listeners for user interaction.
 * 4. Triggers the initial render.
 */
async function initDashboard() {
	try {
		const response = await fetch(DATA_URL);
		if (!response.ok) throw new Error("JSON not found. Run analyze.py first!");

		/** @type {HealthRecord[]} */
		allData = await response.json();

		// Debug Dates
		console.log("First Date in Data:", allData[0].date);
		console.log("Last Date in Data:", allData[allData.length - 1].date);

		// Setup Date Pickers
		const startDateEl = document.getElementById('start-date');
		const endDateEl = document.getElementById('end-date');
		const resetBtn = document.getElementById('reset-btn');

		// Set min/max allowed based on data
		const minDate = allData[0].date;
		const maxDate = allData[allData.length - 1].date;

		// Apply constraints
		startDateEl.min = minDate;
		startDateEl.max = maxDate;
		endDateEl.min = minDate;
		endDateEl.max = maxDate;

		// Set initial values
		startDateEl.value = minDate;
		endDateEl.value = maxDate;

		// Event Listeners for Filtering
		const handleFilter = () => {
			// Safety check: prevent selecting dates outside range manually
			if (startDateEl.value < minDate) startDateEl.value = minDate;
			if (endDateEl.value > maxDate) endDateEl.value = maxDate;

			updateDashboard(startDateEl.value, endDateEl.value);
		};

		startDateEl.addEventListener('change', handleFilter);
		endDateEl.addEventListener('change', handleFilter);
		resetBtn.addEventListener('click', () => {
			startDateEl.value = minDate;
			endDateEl.value = maxDate;
			handleFilter();
		});

		// Initial Render
		updateDashboard(minDate, maxDate);

	} catch (error) {
		console.error(error);
		alert("Error loading data. Check console.");
	}
}

/**
 * Core update loop.
 * Filters the global dataset based on selected date range and triggers re-render of all components.
 * @param {string} start - Start date string (YYYY-MM-DD)
 * @param {string} end - End date string (YYYY-MM-DD)
 */
function updateDashboard(start, end) {
	// Filter Data
	const filteredData = allData.filter(d => d.date >= start && d.date <= end);

	// Update Text
	const statusEl = document.getElementById('data-status');
	if (statusEl) {
		statusEl.textContent = `Showing ${filteredData.length} days (${start} to ${end})`;
	}

	if (filteredData.length === 0) return;

	// Render All
	renderKPIs(filteredData);
	renderTrendChart(filteredData);
	renderCaloriesCompositionChart(filteredData); // NEW: BMR vs Active
	renderActivityZonesChart(filteredData);       // NEW: Doughnut Chart
	renderWeightChart(filteredData);              // Fixed naming mismatch
	renderScatterChart(filteredData);
}

// --- Renderers ---

/**
 * Updates the DOM elements for Key Performance Indicators.
 * Calculates dynamic averages based on the currently filtered view.
 * @param {HealthRecord[]} data - The filtered dataset
 */
function renderKPIs(data) {
	const lastDay = data[data.length - 1];

	const avgRHR = calculateAverage(data, 'resting_bpm');
	const avgSleep = calculateAverage(data, 'overall_score');
	const avgCals = calculateAverage(data, 'calories_total');

	// Helper to safely set text content
	const setText = (id, val) => {
		const el = document.getElementById(id);
		if (el) el.textContent = val;
	};

	setText('kpi-readiness', lastDay.readiness_raw ? lastDay.readiness_raw.toFixed(2) : '--');
	setText('kpi-rhr', avgRHR);
	setText('kpi-sleep', avgSleep);
	setText('kpi-cals', parseInt(avgCals).toLocaleString());

	// Dynamic Styling for Readiness
	const elReadiness = document.getElementById('kpi-readiness');
	if (elReadiness && lastDay.readiness_raw !== null) {
		if (lastDay.readiness_raw > 1) elReadiness.style.color = '#2ecc71';
		else if (lastDay.readiness_raw < -1) elReadiness.style.color = '#e74c3c';
		else elReadiness.style.color = '#3498db';
	}
}

/**
 * Lifecycle manager for Chart.js instances.
 * Destroys any existing chart on the target canvas before creating a new one
 * to prevent canvas reuse errors and visual glitches.
 * @param {string} canvasId - The HTML ID of the canvas element
 * @param {import('chart.js').ChartConfiguration} config - The Chart.js configuration object
 */
function createChart(canvasId, config) {
	const canvas = document.getElementById(canvasId);
	if (!canvas) return; // Prevent error if HTML element is missing

	if (charts[canvasId]) {
		charts[canvasId].destroy();
	}
	const ctx = canvas.getContext('2d');
	charts[canvasId] = new Chart(ctx, config);
}

/**
 * Renders the "Health Trend" Line Chart.
 * Compares Daily Readiness (Z-Score) vs Resting Heart Rate.
 * @param {HealthRecord[]} data - The filtered dataset
 */
function renderTrendChart(data) {
	createChart('trendChart', {
		type: 'line',
		data: {
			labels: data.map(d => d.date),
			datasets: [
				{
					label: 'Readiness',
					data: data.map(d => d.readiness_raw),
					borderColor: '#3498db',
					backgroundColor: 'rgba(52, 152, 219, 0.1)',
					yAxisID: 'y',
					borderWidth: 2,
					pointRadius: 1,
					tension: 0.3
				},
				{
					label: 'RHR',
					data: data.map(d => d.resting_bpm),
					borderColor: '#e74c3c',
					yAxisID: 'y1',
					borderWidth: 1,
					borderDash: [5, 5],
					pointRadius: 0
				}
			]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			interaction: { mode: 'index', intersect: false },
			scales: {
				x: { display: false },
				y: { type: 'linear', display: true, position: 'left', grid: { color: '#444' } },
				y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
			},
			plugins: { legend: { labels: { color: '#fff' } } }
		}
	});
}

/**
 * Renders the "Daily Energy" Stacked Bar Chart.
 * Visualizes the composition of Total Calories (BMR vs Active Burn).
 * @param {HealthRecord[]} data - The filtered dataset
 */
function renderCaloriesCompositionChart(data) {
	createChart('calStackChart', {
		type: 'bar',
		data: {
			labels: data.map(d => d.date),
			datasets: [
				{
					label: 'BMR (Base)',
					data: data.map(d => d.bmr),
					backgroundColor: '#7f8c8d', // Grey
					stack: 'Stack 0'
				},
				{
					label: 'Active Burn',
					data: data.map(d => d.active_calories),
					backgroundColor: '#e67e22', // Orange
					stack: 'Stack 0'
				}
			]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			interaction: { mode: 'index', intersect: false },
			scales: {
				x: { display: false },
				y: {
					stacked: true,
					grid: { color: '#444' },
					title: { display: true, text: 'Calories (Kcal)' }
				}
			},
			plugins: { legend: { labels: { color: '#fff' } } }
		}
	});
}

/**
 * Renders the "Activity Zones" Doughnut Chart.
 * Aggregates total minutes spent in each zone (Sedentary to Very Active) for the period.
 * @param {HealthRecord[]} data - The filtered dataset
 */
function renderActivityZonesChart(data) {
	// Sum up totals for the filtered period
	const totals = data.reduce((acc, curr) => ({
		sedentary: acc.sedentary + curr.sedentary_minutes,
		light: acc.light + curr.lightly_active_minutes,
		moderate: acc.moderate + curr.moderately_active_minutes,
		very: acc.very + curr.very_active_minutes
	}), { sedentary: 0, light: 0, moderate: 0, very: 0 });

	createChart('zonesChart', {
		type: 'doughnut',
		data: {
			labels: ['Sedentary', 'Light', 'Moderate', 'Very Active'],
			datasets: [{
				data: [totals.sedentary, totals.light, totals.moderate, totals.very],
				backgroundColor: ['#2c3e50', '#f1c40f', '#e67e22', '#e74c3c'],
				borderWidth: 0
			}]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			plugins: {
				legend: { position: 'right', labels: { color: '#fff' } }
			}
		}
	});
}


/**
 * Renders the "Weight vs Calories" Dual-Axis Line Chart.
 * Correlates body weight trends (Left Axis) with Caloric Expenditure (Right Axis).
 * @param {HealthRecord[]} data - The filtered dataset
 */
function renderWeightChart(data) {
	// Chart.js handles nulls gracefully
	createChart('weightChart', {
		type: 'line',
		data: {
			labels: data.map(d => d.date),
			datasets: [
				{
					label: 'Weight (Kg)',
					data: data.map(d => d.weight),
					borderColor: '#f1c40f',
					backgroundColor: 'rgba(241, 196, 15, 0.1)',
					yAxisID: 'y',
					tension: 0.1,
					spanGaps: true
				},
				{
					label: 'Calories',
					data: data.map(d => d.calories_total),
					borderColor: '#e67e22',
					yAxisID: 'y1',
					borderWidth: 1,
					pointRadius: 0,
					fill: true
				}
			]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			interaction: { mode: 'index', intersect: false },
			scales: {
				x: { display: false },
				y: {
					type: 'linear', display: true, position: 'left',
					title: { display: true, text: 'Weight (Kg)' },
					grid: { color: '#444' }
				},
				y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
			},
			plugins: { legend: { labels: { color: '#fff' } } }
		}
	});
}

/**
 * Renders the "Activity vs Sleep" Scatter Plot.
 * X-Axis: Calories Burned, Y-Axis: Sleep Score.
 * Useful for finding correlations between exertion and rest quality.
 * @param {HealthRecord[]} data - The filtered dataset
 */
function renderScatterChart(data) {
	const scatterData = data
		.filter(d => d.calories_total > 0 && d.overall_score > 0)
		.map(d => ({ x: d.calories_total, y: d.overall_score }));

	createChart('scatterChart', {
		type: 'scatter',
		data: {
			datasets: [{
				label: 'Cals vs Sleep',
				data: scatterData,
				backgroundColor: 'rgba(155, 89, 182, 0.6)',
				borderColor: 'rgba(155, 89, 182, 1)',
			}]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			scales: {
				x: { title: { display: true, text: 'Calories' }, grid: { color: '#444' } },
				y: { title: { display: true, text: 'Sleep Score' }, grid: { color: '#444' } }
			},
			plugins: { legend: { labels: { color: '#fff' } } }
		}
	});
}

initDashboard();