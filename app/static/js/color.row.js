function colorRows(trs, a) {
	let previous = '';
	trs.forEach( tr => {
		if (tr.classList.contains("empty")) {
			return;
		}
		const td_article_description = tr.querySelector(`td:nth-child(${a})`).textContent;
		if (previous == td_article_description) {
			previous = td_article_description;
		} else {
			tr.style.borderTop = "2px solid black";
			previous = td_article_description;
		}
	});
}