// Wait for DOM to fully load
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById("editShiftModal");
    const span = document.getElementsByClassName("close")[0];

    // Check if elements exist
    if (!modal) {
        console.error("Modal element not found");
        return;
    }

    if (!span) {
        console.error("Close button not found");
        return;
    }

    // Make editShift function global
    window.editShift = function(cell) {
        console.log("Edit shift clicked", cell.dataset); // Debug log

        const username = cell.dataset.username;
        const date = cell.dataset.date;
        const start = cell.dataset.start;
        const end = cell.dataset.end;

        document.getElementById("shift_username").value = username;
        document.getElementById("shift_date").value = date;
        document.getElementById("start_time").value = start;
        document.getElementById("end_time").value = end;

        modal.style.display = "block";
    }

    span.onclick = function() {
        modal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});