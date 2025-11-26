import Chart from 'chart.js/auto';

/**
 * @typedef {Object} HealthRecord
 * @property {string} date - The date string (YYYY-MM-DD)
 * @property {number|null} resting_bpm - Resting Heart Rate
 * @property {number|null} weight - Weight in Lbs
 * @property {number|null} bmi - Body Mass Index
 * @property {number} calories_total - Total calories burned
 * @property {number|null} overall_score - Sleep score (0-100)
 * @property {number} very_active_minutes - Minutes of high activity
 * @property {number|null} readiness_raw - Calculated readiness Z-Score
 */

// Configuration
const DATA_URL = './dashboard_data.json';

// --- Helper Functions ---

/**
 * Calculates the average of a specific key in the dataset, ignoring nulls.
 * @param {HealthRecord[]} data
 * @param {keyof HealthRecord} key
 * @returns {string} The formatted average
 */
const calculateAverage = (data, key) => {
	const validData = data.filter(d => d[key] !== null && d[key] !== undefined);
	if (validData.length === 0) return '--';
	const sum = validData.reduce((acc, curr) => acc + (curr[key] || 0), 0);
	return (sum / validData.length).toFixed(1);
};

// --- Main Logic ---

/**
 * Initializes the dashboard by fetching data and rendering components.
 */
async function initDashboard() {
	try {
		const response = await fetch(DATA_URL);
		if (!response.ok) throw new Error("JSON not found. Run analyze.py first!");

		/** @type {HealthRecord[]} */
		const rawData = await response.json();

		// Update Header Date Range
		const start = rawData[0].date;
		const end = rawData[rawData.length - 1].date;
		const dateRangeEl = document.getElementById('date-range');
		if (dateRangeEl) {
			dateRangeEl.textContent = `Data Range: ${start} to ${end} (${rawData.length} days)`;
		}

		// Render Components
		renderKPIs(rawData);
		renderTrendChart(rawData);
		renderWeightVsCaloriesChart(rawData); // Updated function
		renderScatterChart(rawData);

	} catch (error) {
		console.error(error);
		alert("Error loading data. Check console for details.");
	}
}

/**
 * Renders the Key Performance Indicators cards.
 * @param {HealthRecord[]} data
 */
function renderKPIs(data) {
	const lastDay = data[data.length - 1];

	// Calculate Averages
	const avgRHR = calculateAverage(data, 'resting_bpm');
	const avgSleep = calculateAverage(data, 'overall_score');
	const avgCals = calculateAverage(data, 'calories_total');

	// DOM Elements
	const elReadiness = document.getElementById('kpi-readiness');
	const elRHR = document.getElementById('kpi-rhr');
	const elSleep = document.getElementById('kpi-sleep');
	const elCals = document.getElementById('kpi-cals');

	// Update Text
	if (elReadiness) elReadiness.textContent = lastDay.readiness_raw ? lastDay.readiness_raw.toFixed(2) : '--';
	if (elRHR) elRHR.textContent = avgRHR;
	if (elSleep) elSleep.textContent = avgSleep;
	if (elCals) elCals.textContent = parseInt(avgCals).toLocaleString();

	// Dynamic Styling for Readiness
	if (elReadiness && lastDay.readiness_raw !== null) {
		if (lastDay.readiness_raw > 1) elReadiness.style.color = '#2ecc71'; // Green
		else if (lastDay.readiness_raw < -1) elReadiness.style.color = '#e74c3c'; // Red
		else elReadiness.style.color = '#3498db'; // Blue/Normal
	}
}

/**
 * Renders the main trend chart (Readiness vs RHR).
 * @param {HealthRecord[]} data
 */
function renderTrendChart(data) {
	const canvas = document.getElementById('trendChart');
	if (!canvas) return;

	// @ts-ignore
	const ctx = canvas.getContext('2d');

	new Chart(ctx, {
		type: 'line',
		data: {
			labels: data.map(d => d.date),
			datasets: [
				{
					label: 'Readiness Score',
					data: data.map(d => d.readiness_raw),
					borderColor: '#3498db',
					backgroundColor: 'rgba(52, 152, 219, 0.1)',
					yAxisID: 'y',
					borderWidth: 2,
					tension: 0.3,
					pointRadius: 1
				},
				{
					label: 'RHR (Resting Heart Rate)',
					data: data.map(d => d.resting_bpm),
					borderColor: '#e74c3c',
					yAxisID: 'y1',
					borderWidth: 1,
					borderDash: [5, 5],
					tension: 0.1,
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
				y: {
					type: 'linear', display: true, position: 'left',
					title: { display: true, text: 'Readiness (Z-Score)' },
					grid: { color: '#444' }
				},
				y1: {
					type: 'linear', display: true, position: 'right',
					title: { display: true, text: 'BPM' },
					grid: { drawOnChartArea: false }
				}
			},
			plugins: {
				legend: { labels: { color: '#fff' } }
			}
		}
	});
}

/**
 * Renders Weight vs Calories using Dual Y-Axes.
 * We use the FULL dataset (including nulls) to keep dates aligned.
 * @param {HealthRecord[]} data
 */
function renderWeightVsCaloriesChart(data) {
	const canvas = document.getElementById('weightChart');
	if (!canvas) return;

	const ctx = canvas.getContext('2d');

	// Note: Chart.js handles null values gracefully (breaks the line)
	// so we don't need to filter. This keeps X-Axis consistent for both datasets.

	new Chart(ctx, {
		type: 'line',
		data: {
			labels: data.map(d => d.date),
			datasets: [
				{
					label: 'Weight (Lbs)',
					data: data.map(d => d.weight), // Includes nulls
					borderColor: '#f1c40f',
					backgroundColor: 'rgba(241, 196, 15, 0.1)',
					yAxisID: 'y', // Left Axis
					tension: 0.1,
					borderWidth: 2,
					spanGaps: true // Connects points even if there are missing days
				},
				{
					label: 'Calories Burned',
					data: data.map(d => d.calories_total),
					borderColor: '#e67e22',
					backgroundColor: 'rgba(230, 126, 34, 0.05)',
					yAxisID: 'y1', // Right Axis
					borderWidth: 1,
					pointRadius: 0,
					fill: true,
					tension: 0.4
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
					title: { display: true, text: 'Weight (Lbs)' },
					grid: { color: '#444' }
				},
				y1: {
					type: 'linear', display: true, position: 'right',
					title: { display: true, text: 'Calories' },
					grid: { drawOnChartArea: false }
				}
			},
			plugins: { legend: { labels: { color: '#fff' } } }
		}
	});
}

/**
 * Renders Scatter plot for Activity vs Sleep.
 * @param {HealthRecord[]} data
 */
function renderScatterChart(data) {
	const canvas = document.getElementById('scatterChart');
	if (!canvas) return;

	const ctx = canvas.getContext('2d');

	// Prepare format: {x: cals, y: sleep}
	const scatterData = data
		.filter(d => d.calories_total > 0 && d.overall_score > 0)
		.map(d => ({ x: d.calories_total, y: d.overall_score }));

	new Chart(ctx, {
		type: 'scatter',
		data: {
			datasets: [{
				label: 'Calories vs Sleep Score',
				data: scatterData,
				backgroundColor: 'rgba(155, 89, 182, 0.6)',
				borderColor: 'rgba(155, 89, 182, 1)',
			}]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			scales: {
				x: {
					title: { display: true, text: 'Calories Burned' },
					grid: { color: '#444' }
				},
				y: {
					title: { display: true, text: 'Sleep Score' },
					grid: { color: '#444' }
				}
			},
			plugins: { legend: { labels: { color: '#fff' } } }
		}
	});
}

initDashboard();