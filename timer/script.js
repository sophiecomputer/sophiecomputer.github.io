// Read HTML elements.
const logBox = document.getElementById("logBox");
const logButton = document.getElementById("logButton"); 
const logStatusText = document.getElementById("logStatusText");
const timerArea = document.getElementById("timerArea");

/** 
 * Given a key passed via the URL, converts it to a serialized name. 
 */
function keyName(key) {
	return key.toLowerCase().replace(/[^a-z0-9]/g, ""); 
}

function createTimerElements(data) {
	// Define colors to cycle through.
	const colors = ["yellow", "lightblue", "lightpink", "violet", "lightgreen"]
	let index = 0; 

	const matches = data.matchAll(/(\w+)\[([^\]]*)\]/g);
	for (const match of matches) {
		const superKeyText = match[1];
		const superKey = keyName(superKeyText);
		const color = colors[index % colors.length]; 
		index += 1; 
		
		// Create outer block.
		const h2 = document.createElement("h2");
		const outerText = document.createTextNode(superKeyText + " ");
		const outerTime = document.createElement("span"); 
		outerTime.className = "timetext";
		outerTime.style = "background-color: " + color;
		outerTime.textContent = "00:00.00";
		h2.appendChild(outerText);
		h2.appendChild(outerTime);
		timerArea.appendChild(h2);
		totalTimeBoxes[superKey] = outerTime;
		
		// Create one inner block per comma-separated item.
		const innerItems = match[2].split(",").map(s => s.trim());	
		timerElements[superKey] = {}; 
		for (const item of innerItems) {
			if (!item)
				continue; 
			const itemKey = keyName(item); 
		
			const h3 = document.createElement("h3");
			const bold = document.createElement("b"); 
			bold.textContent = item;
			const innerTime = document.createElement("span");
			innerTime.className = "timetext";
			innerTime.textContent = "00:00.00";
			innerTime.style = "background-color: " + color; 
			const btn = document.createElement("button");
			btn.textContent = "Start";
			h3.appendChild(bold); 
			h3.appendChild(document.createTextNode(" ")); 
			h3.appendChild(innerTime); 
			h3.appendChild(document.createTextNode(" ")); 
			h3.appendChild(btn);
			timerArea.appendChild(h3);
			
			timerElements[superKey][superKey + "_" + itemKey] = {
				"text": innerTime, 
				"button": btn, 
				"startTime": null, 
				"sessions": [] 
			}; 
		}
		
		const hr = document.createElement("hr");
		hr.className = "horizontalDivider";
		timerArea.appendChild(hr);
	}
}

// Parse the URL for the timer structure.
const params = new URLSearchParams(window.location.search);
let data = params.get("s");

const defaultData = (
	"Work[Project 1,Project 2,Project 3]," + 
	"Personal[Project 4, Project 5]"
);
if (data == null) {
	// Reload default data with parameter. 
	data = defaultData; 
	const newUrl = window.location.pathname + "?s=" + data;
	window.location.replace(newUrl);
}

let timerElements = {}; 
let totalTimeBoxes = {}; 

try { 
	createTimerElements(data);
} catch { 
	// If there's an error, destroy everything under the "timerArea" div, then 
	// add an error message, then add the default.
	timerElements = {};
	totalTimeBoxes = {}; 
	while (timerArea.firstChild)
		timerArea.removeChild(timerArea.firstChild);
	
	const h2 = document.createElement("h2"); 
	const textNode = document.createTextNode(
		"Error in parsing structure, using default. Structure: " + data);
	h2.appendChild(textNode);
	timerArea.appendChild(h2); 
	
	createTimerElements(defaultData);
}

/**
 * Converts a delta time to a displayable string. 
 */
function elapsedTime(deltaTimeMillis) {
	const totalSec = Math.floor(deltaTimeMillis / 1000);
	let h = Math.floor(totalSec / 3600);
	let m = Math.floor((totalSec % 3600) / 60);
	let s = totalSec % 60;
	return (
		String(h).padStart(2, "0") + ":" + 
		String(m).padStart(2, "0") + "." + 
		String(s).padStart(2, "0")
	); 
};

/**
 * This function is run once every time interval. It's used to update all timer 
 * text with new durations.
 */
function updateTimers() {
	// For each button that's currently running, update the timer text.
	Object.keys(timerElements).forEach(function(superKey) {
		let sumTime = 0; 
		Object.keys(timerElements[superKey]).forEach(function(key) {
			if (timerElements[superKey][key]["startTime"] != null) {
				const ms = 
					(new Date()) - timerElements[superKey][key]["startTime"];
				timerElements[superKey][key]["text"].textContent = 
					elapsedTime(ms);
				sumTime += ms;
			}
			
			// Also add history.
			for (const session of timerElements[superKey][key]["sessions"]) {
				sumTime += session["end"] - session["start"];
			} 
		});
		
		// Set total time box to this.
		totalTimeBoxes[superKey].textContent = elapsedTime(sumTime);
	});
}

/**
 * Updates the text in the log with a JSON file describing each timer's state.
 * Does not change each timer's state. 
 */
function drawLog() {
	const now = new Date();
	const obj = { 
		"date": (
			(now.getMonth() + 1) + "/" + 
			now.getDate() + "/" + 
			now.getFullYear()
		)
	}; 
	Object.keys(timerElements).forEach(function(superKey) {
		Object.keys(timerElements[superKey]).forEach(function(key) {
			// Get the collection of times for this and store it in an object.
			const sessions = []; 
			let times = ""; 
			let millis = 0; 
			for (const session of timerElements[superKey][key]["sessions"]) {
				const startStr = (
					String(session["start"].getHours()).padStart(2, "0") + ":" + 
					String(session["start"].getMinutes()).padStart(2, "0") + "." + 
					String(session["start"].getSeconds()).padStart(2, "0") 
				);
				const endStr = (
					String(session["end"].getHours()).padStart(2, "0") + ":" + 
					String(session["end"].getMinutes()).padStart(2, "0") + "." + 
					String(session["end"].getSeconds()).padStart(2, "0")			
				);
				sessions.push({
					"start": startStr, 
					"end": endStr
				}); 
				
				// Also obtain the difference in milliseconds between these. 
				millis += session["end"] - session["start"]; 
			}
			
			const keyObj = {
				"sum": elapsedTime(millis), 
				"sessions": sessions
			}; 
			obj[key] = keyObj;
		}); 
	}); 
	
	logBox.value = JSON.stringify(obj, null, 2);
	logBox.style.height = logBox.scrollHeight + "px";
}

/**
 * Reads the log for text and updates the internal state of the timers based on
 * it. 
 */
function parseLog() {
	let textValue = logBox.value;
	let result = null; 
	
	if (textValue.trim().length == 0) 
		result = {};
	else {
		try {
			result = JSON.parse(logBox.value);
		} catch {
			logStatusText.textContent = "Invalid JSON";
			return; 
		}
	}
	
	// "result" is a map of key names to times.
	Object.keys(timerElements).forEach(function(superKey) {
		Object.keys(timerElements[superKey]).forEach(function(key) {
			const sessions = [];
			if (key in result) {
				if ("sessions" in result[key]) {
					for (const session of result[key]["sessions"]) {
						if (!("start" in session && "end" in session))
							continue;
					
						// Turn these into Date objects.
						sessions.push({
							"start": parseTime(session["start"]), 
							"end": parseTime(session["end"])
						}); 
					}
				}
			}
			timerElements[superKey][key]["sessions"] = sessions;
		}); 
	}); 
	updateTimers();
	Object.keys(timerElements).forEach(function(superKey) {
		Object.keys(timerElements[superKey]).forEach(function(key) {
			if (timerElements[superKey][key]["startTime"] == null)
				timerElements[superKey][key]["text"].textContent = 
					elapsedTime(0); 
		}); 
	});
	logStatusText.textContent = "";
	logBox.style.height = logBox.scrollHeight + "px";
}

// Helper: parse "HH:MM.SS" into a Date object (today)
function parseTime(str) {
	const now = new Date();
	const [time, seconds] = str.split(".");
	const [hours, minutes] = time.split(":").map(Number);

	const date = new Date(now);
	date.setHours(hours, minutes, seconds, 0);

	return date;
}

logButton.onclick = parseLog;

// Set button behavior. When a button is pressed, run the function.
Object.keys(timerElements).forEach(function(superKey) {
	Object.keys(timerElements[superKey]).forEach(function(key) {
		timerElements[superKey][key]["button"].onclick = function() {
			if (timerElements[superKey][key]["startTime"] != null) {
				// The timer is currently running. Append the duration to the log 
				// and stop it.
				timerElements[superKey][key]["button"].textContent = "Start";
				timerElements[superKey][key]["sessions"].push({
					"start": timerElements[superKey][key]["startTime"], 
					"end": new Date()
				});
				timerElements[superKey][key]["startTime"] = null;
				drawLog();
			}
			else {
				// The timer is not currently running. Start it.
				timerElements[superKey][key]["button"].textContent = "Stop";
				timerElements[superKey][key]["startTime"] = new Date();
			}
		}; 
	}); 
}); 

// Run every 500ms.
setInterval(updateTimers, 500);
