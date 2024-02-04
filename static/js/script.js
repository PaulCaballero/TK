let activityTimeout;
let warningTimeout;
const warningDuration = 60 * 1000; // 1 minute warning duration

function resetTimer() {
    clearTimeout(activityTimeout);
    clearTimeout(warningTimeout);
    activityTimeout = setTimeout(showWarning, 6 * 60 * 1000); // 6 minutes
}

function showWarning() {
    // Show a warning popup to the user
    alert("You have been inactive for 6 minutes. You will be logged out in 1 minute if there's no further activity.");

    // Set another timeout for auto-logout
    warningTimeout = setTimeout(autoLogout, warningDuration);
}

// Function to update the clock
function updateClock() {
    const now = new Date(); // Get the current time
    const hours = ('0' + now.getHours()).slice(-2); // Format the hours
    const minutes = ('0' + now.getMinutes()).slice(-2); // Format the minutes
    const seconds = ('0' + now.getSeconds()).slice(-2); // Format the seconds
    document.getElementById('digital-clock').textContent = `${hours}:${minutes}:${seconds}`;
}

// Update the clock every second
setInterval(updateClock, 1000);

// Call the function on initial load
window.onload = updateClock;

function autoLogout() {
    // Redirect to logout URL or send a request to the server to end the session
    window.location.href = '/logout'; // Assuming '/logout' is your logout route
}

window.onload = resetTimer;
document.onmousemove = resetTimer;
document.onkeypress = resetTimer;

document.addEventListener("DOMContentLoaded", function() {
    const messageBox = document.getElementById('message-box');
    if (messageBox) {
        setTimeout(() => {
            messageBox.style.animation = 'fadeOut 1s forwards';
        }, 5000);
    }
});

