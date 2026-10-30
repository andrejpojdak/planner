import datetime

def brasil_conf_week(cw_string, delta):
	week, year_suffix = cw_string.replace("CW", "").split("/")
	week = int(week)
	year = int("20" + year_suffix)

	start_date = datetime.date.fromisocalendar(year, week, 1)

	new_date = start_date + datetime.timedelta(weeks=delta)

	new_iso_year, new_iso_week, _ = new_date.isocalendar()

	return(f'CW{new_iso_week:02}/{new_iso_year % 100:02}')