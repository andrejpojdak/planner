
import re
from datetime import date

def iso_week_range(isoweek_cwMMYY_format):

	year = 2000 + int(isoweek_cwMMYY_format.split('/')[1])
	week = int(re.sub("CW", "", isoweek_cwMMYY_format.split('/')[0]), flags=re.IGNORECASE)

	monday = date.fromisocalendar(year, week, 1)
	sunday = date.fromisocalendar(year, week, 7)

	return monday, sunday
