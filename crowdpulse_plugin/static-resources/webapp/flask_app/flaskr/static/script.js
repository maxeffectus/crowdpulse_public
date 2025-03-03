let maxDataPoints = 50;
let dataPoints = [];
let ctx = document.getElementById('dataChart').getContext('2d');
let cameraSelect = document.getElementById("cameraSelect");
let currentCamera = cameraSelect.value;
let threshold = Number(document.getElementById("thresholdSelect").value);


document.addEventListener("DOMContentLoaded", async function () {
    let thresholdSelect = document.getElementById("thresholdSelect");

    async function getThreshold() {
        try {
            let response = await fetch(`http://127.0.0.1:${webAppPort}/engagement_threshold/${currentCamera}`);
            if (!response.ok) throw new Error("Failed to fetch threshold");

            let data = await response.json();
            thresholdSelect.value = data.engagement_threshold;
        } catch (error) {
            console.error("Error fetching threshold:", error);
        }
    }

    await getThreshold();
    thresholdSelect.addEventListener("change", async function () {
        let newThreshold = thresholdSelect.value;

        try {
            let response = await fetch(`http://127.0.0.1:${webAppPort}/engagement_threshold/${currentCamera}`, {
                method: 'POST',
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ engagement_threshold: newThreshold })
            });

            let result = await response.json();
            console.log("Threshold updated:", result);
        } catch (error) {
            console.error("Error updating threshold:", error);
        }
    });
});


function getSegmentColor(ctx) {
    let chart = ctx.chart;
    let data = chart.data.datasets[0].data;
    let index = ctx.p1DataIndex;

    if (index <= 0 || index >= data.length) return 'blue'; // Default color

    let y1 = data[index - 1];
    let y2 = data[index];

    if (y1 >= threshold && y2 >= threshold) {
        return 'blue';
    } else {
        return 'red';
    }
}

function breakSegments(dataset) {
    let newData = [];
    let newLabels = [];

    for (let i = 1; i < dataset.length; i++) {
        let prevPoint = dataset[i - 1];
        let currPoint = dataset[i];

        newData.push(prevPoint.value);
        newLabels.push(prevPoint.timestamp);

        if ((prevPoint.value < threshold && currPoint.value >= threshold) ||
            (prevPoint.value >= threshold && currPoint.value < threshold)) {


            let ratio = (threshold - prevPoint.value) / (currPoint.value - prevPoint.value);
            let midTimestamp = prevPoint.timestamp + " | ";
            let midValue = threshold;


            newData.push(midValue);
            newLabels.push(midTimestamp);
        }
    }


    newData.push(dataset[dataset.length - 1].value);
    newLabels.push(dataset[dataset.length - 1].timestamp);

    return { newData, newLabels };
}

// Create a chart
let chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Engagement Level',
            data: [],
            borderWidth: 2,
            fill: false,
            segment: {
                borderColor: getSegmentColor
            }
        }]
    },
    options: {
        animation: {
            duration: 0  // Disable animation for smooth updates
        },
        responsive: true,
        scales: {
            x: { title: { display: true, text: 'Timestamp' } },
            y: {
                title: { display: true, text: 'Engagement Level' },
                min: 0,
                max: 100
            }
        },
        plugins: {
            annotation: {
                annotations: {
                    thresholdLine: {
                        type: 'line',
                        yMin: threshold,
                        yMax: threshold,
                        borderColor: 'red',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        label: {
                            content: 'Threshold',
                            enabled: true,
                            position: 'end',
                            backgroundColor: 'rgba(255, 0, 0, 0.2)',
                            color: 'red'
                        }
                    },
                    aboveThreshold: {
                        type: 'box',
                        borderWidth: 0,
                        yMin: threshold + 10,
                        yMax: 100,
                        backgroundColor: 'rgba(0, 255, 0, 0.2)' // Green
                    },
                    aroundThreshold: {
                        type: 'box',
                        borderWidth: 0,
                        yMin: threshold - 10,
                        yMax: threshold + 10,
                        backgroundColor: 'rgba(255, 255, 0, 0.2)' // Yellow
                    },
                    belowThreshold: {
                        type: 'box',
                        borderWidth: 0,
                        yMin: 0,
                        yMax: threshold - 10,
                        backgroundColor: 'rgba(255, 0, 0, 0.2)' // Red
                    }
                }
            }
        }

    }
});

async function loadHistory() {
    try {
        let response = await fetch(`http://127.0.0.1:${webAppPort}/camera_data/${currentCamera}`);
        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        let historyData = await response.json();
        dataPoints = historyData.map(d => ({ timestamp: d.timestamp, value: d.value }));

        chart.data.labels = dataPoints.map(d => d.timestamp);
        chart.data.datasets[0].data = dataPoints.map(d => d.value);
        chart.update();
    } catch (error) {
        console.error("Fetch error:", error);
    }
}

async function getNewThreshold() {
    document.getElementById("applyThreshold").addEventListener("click", function () {
        let newThreshold = parseInt(document.getElementById("thresholdSelect").value);

        if (!isNaN(newThreshold) && newThreshold >= 0 && newThreshold <= 100) {
            threshold = newThreshold;
            chart.options.plugins.annotation.annotations.thresholdLine.yMin = threshold;
            chart.options.plugins.annotation.annotations.thresholdLine.yMax = threshold;
            chart.options.plugins.annotation.annotations.aboveThreshold.yMin = threshold + 10;
            chart.options.plugins.annotation.annotations.aroundThreshold.yMin = threshold - 10;
            chart.options.plugins.annotation.annotations.aroundThreshold.yMax = threshold + 10;
            chart.options.plugins.annotation.annotations.belowThreshold.yMax = threshold - 10;
            chart.update();
        } else {
            alert("Please enter a valid number between 0 and 100.");
        }
    });

}

async function fetchData() {
    try {  // Fetch from selected camera
        let response = await fetch(`http://127.0.0.1:${webAppPort}/camera_data/${currentCamera}`);
        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        let historyData = await response.json();
        let latestData = historyData[historyData.length - 1];

        document.getElementById('data').innerText = `Message: ${latestData.message}, Value: ${latestData.value}`;
        document.getElementById('time').innerText = `Timestamp: ${latestData.timestamp}`;

        // Add only the latest data point if it's new
        if (!dataPoints.length || dataPoints[dataPoints.length - 1].timestamp !== latestData.timestamp) {
            dataPoints.push({ timestamp: latestData.timestamp, value: latestData.value });

            // Shift if max history exceeded
            if (dataPoints.length > maxDataPoints) {
                dataPoints.shift();
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }

            chart.data.labels.push(latestData.timestamp);
            chart.data.datasets[0].data.push(latestData.value);
            chart.update();

            let processedData = breakSegments(dataPoints);

            // Update chart data
            chart.data.labels = processedData.newLabels;
            chart.data.datasets[0].data = processedData.newData;

            function updateEventIcon() {
                if (dataPoints.length < 1) return;
                let sum = 0
                dataPoints.forEach(point => {
                    sum += point.value;
                    }
                )
                let average = sum / dataPoints.length
                console.log(average)

                let lowerLimit = threshold - 10;
                let upperLimit = threshold + 10;

                if (average < lowerLimit) {
                    iconPath = "boring_event.svg";
                } else if (average > upperLimit) {
                    iconPath = "interesting_event.svg";
                } else {
                    iconPath = "meh_event.svg";
                }
                document.getElementById("eventIcon").src = `/static/icons/${iconPath}`;
            }
            chart.update()
            updateEventIcon();
        }

    } catch (error) {
        console.error("Fetch error:", error);
        document.getElementById('data').innerText = "Failed to load data!";
        document.getElementById('time').innerText = "Error retrieving timestamp!";
    }
}

// Handle camera selection change
cameraSelect.addEventListener("change", async function () {
    currentCamera = this.value;
    chart.data.datasets[0].borderColor = "blue";
    chart.data.datasets[0].label = `Value from ${currentCamera.toUpperCase()}`;
    await loadHistory();
});

setInterval(fetchData, 2000);
loadHistory();
getNewThreshold();