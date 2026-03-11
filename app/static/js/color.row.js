function colorRows(trs, a) {
	let previous = '';
	//let classes = ["lightgrey", "white"];
	trs.forEach( tr => {
		const td_article_description = tr.querySelector(`td:nth-child(${a})`).textContent;
		if (previous == td_article_description) {
			//tr.classList.add(classes[0]);
			previous = td_article_description;
		} else {
			//classes.push(classes.shift());
			//tr.classList.add(classes[0]);
			tr.style.borderTop = "2px solid black";
			previous = td_article_description;
		}
	});
}