function clearTable() {
  const filters = table.querySelectorAll(".filter-row input");
  
  filters.forEach(input => {
	input.value = "";
  });

  filterTable();
  
}

function filterTable() {

  const filters = table.querySelectorAll(".filter-row input");
  const rows = table.querySelectorAll("tbody tr:not(.filter-row):not(.filter-row-button)");
  const row_separators = table.querySelectorAll("tbody tr.end");
  
  rows.forEach(row => {

    let visible = "";

    filters.forEach(input => {

      const colIndex = input.dataset.column;
      const cellText = row.cells[colIndex].textContent.toLowerCase();
      const filterValue = input.value.toLowerCase();

      if (!cellText.includes(filterValue)) {
        visible = "none";
		row_separators.forEach( end=> {
			end.style.display = "none"
		});
      }

    });

    row.style.display = visible;

  });

}
