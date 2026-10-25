function hideDuplicateValues(table, targetCol) {
    const rows = table.querySelectorAll("tbody tr");
    const seen = new Set();

    rows.forEach(row => {
        const cells = row.querySelectorAll("td");
        if (cells.length < 6) return;

        // Columns 1, 3, 4, and 6 are compared
        const key = [0, 2, 3, 5]
            .map(i => cells[i].textContent.trim())
            .join("|");

        // targetCol is a 1-based column position
        const targetCell = cells[targetCol - 1];
        if (!targetCell) return;

        if (seen.has(key)) {
            targetCell.style.visibility = "hidden";
        } else {
            seen.add(key);
            targetCell.style.visibility = "visible";
        }
    });
}

