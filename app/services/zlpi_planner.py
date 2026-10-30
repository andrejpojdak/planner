import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

import pandas as pd
import glob
from datetime import datetime, timedelta
import os
from .brasil_date import brasil_conf_week

def fill_schedule_response(updated_list, input_file, normalized_df):
	input = input_file
	name, ext = os.path.splitext(input)
	output = f'{name}_filled{ext}'
	not_found = []
	messages = []
	
	df_schedule_response = pd.read_excel(input, dtype={'Plant Code': str, 'Supplier No.': str, 'Order Number': str, 'Article Number': str})
	df_schedule_response = df_schedule_response.sort_values(by=['Order Number', 'Order Position', 'Original Date Sched. Line']).reset_index(drop=True)
	df_schedule_response['Article Number'] = df_schedule_response['Article Number'].astype(str)
	
	df_schedule_response = df_schedule_response.apply(row_zero_out, axis=1)
	df_schedule_response_new = df_schedule_response.iloc[0:0].copy()
	df_clear_confirmations = df_schedule_response.iloc[0:0].copy()
	
	for index, row in df_schedule_response.iterrows():
		
		orig_date = row['Original Date Sched. Line']
		orig_qty = row['Original Qty. Sched. Line']
		values = []
		order = str(row['Order Number']).lstrip('0')
		position = str(row['Order Position'])
		delta = 0
		
		if(order + "-" + position in updated_list):
			
			df_clear_confirmations = pd.concat([df_clear_confirmations, pd.DataFrame([clear_confirmations(df_clear_confirmations, row.copy()).to_dict()])], ignore_index=True)

			if row['Plant Code'] == '0701':
				delta = 9
			if row['Plant Code'] == '0254':
				delta = 2
			
			if (pd.isna(row['Original Date Sched. Line']) and
				pd.isna(row['Original Qty. Sched. Line']) and
				pd.notna(row['Confirmed Date Sched. Line'])
			):
				continue
			#nula
			elif(int(float(orig_qty)) == 0):
				row['Original Date Sched. Line'] = row['Original Date Sched. Line'].strftime('%d.%m.%Y')
				row['Confirmed Date Sched. Line'] = pd.to_datetime(orig_date, format='%d.%m.%Y').strftime('%d.%m.%Y')
				row['Confirmed Qty. Sched. Line'] = row['Original Qty. Sched. Line']
				df_schedule_response_new = pd.concat([df_schedule_response_new, pd.DataFrame([row])], ignore_index=True)
				messages.append([str(row['Order Number'].lstrip('0'))+"-"+str(row['Order Position']), row['Original Qty. Sched. Line'], row['Original Date Sched. Line'], row['Original Date Sched. Line'], row['Original Qty. Sched. Line']])
			#china
			else:
				row['Order Position'] = str(row['Order Position'])
				row['Original Date Sched. Line'] = row['Original Date Sched. Line'].strftime('%d.%m.%Y')
				row['Original Qty. Sched. Line'] = str(int(float(row['Original Qty. Sched. Line'])))
				values = (row[['Order Number', 'Order Position', 'Original Qty. Sched. Line', 'Original Date Sched. Line']].tolist())
				splits, unsorted_qtys, unsorted_dates, unsorted_comments = confirm_line(normalized_df, values[0], values[1], values[2], values[3], delta)
				if isinstance(unsorted_qtys, list) and isinstance(unsorted_dates, list) and isinstance(unsorted_comments, list):
					dates_sorted, qtys_sorted, comments_sorted = zip(*sorted(zip(unsorted_dates, unsorted_qtys, unsorted_comments), key=lambda x: datetime.strptime(x[0], '%d.%m.%Y')))
					
					# Convert back to lists
					dates = list(dates_sorted)
					qtys = list(qtys_sorted)
					comments = list(comments_sorted)
				else:
					dates = unsorted_dates
					qtys = unsorted_qtys
					comments = unsorted_comments
				
				if(splits == None):
					row['Confirmed Date Sched. Line'] = pd.to_datetime(orig_date, format='%d.%m.%Y').strftime('%d.%m.%Y')
					row['Confirmed Qty. Sched. Line'] = 0
					messages.append([str(row['Order Number'].lstrip('0'))+"-"+str(row['Order Position']), row['Original Qty. Sched. Line'], row['Original Date Sched. Line'], '', '', "NOT CONFIRMED"])
					if datetime.strptime(row['Original Date Sched. Line'], "%d.%m.%Y") < (datetime.today()+timedelta(days=180)):
						not_found.append([row['Order Number'].lstrip('0'), row['Order Position'], row['Original Qty. Sched. Line'], row['Original Date Sched. Line']])
					df_schedule_response_new = pd.concat([df_schedule_response_new, pd.DataFrame([row])], ignore_index=True)
					continue
				elif(splits == 0):
					row['Confirmed Date Sched. Line'] = pd.to_datetime(datetime.strptime(dates, "%d.%m.%Y")).strftime('%d.%m.%Y')
					row['Confirmed Qty. Sched. Line'] = qtys
					df_schedule_response_new = pd.concat([df_schedule_response_new, pd.DataFrame([row])], ignore_index=True)
					messages.append([str(row['Order Number'].lstrip('0'))+"-"+str(row['Order Position']), row['Original Qty. Sched. Line'], row['Original Date Sched. Line'], dates, qtys, comments])					
					continue
				
				elif(splits > 0 and len(qtys) == len(dates)):
					for i, (x, y, z) in enumerate(zip(qtys, dates, comments)):
						
						if(i==0):
							row['Confirmed Date Sched. Line'] = pd.to_datetime(datetime.strptime(y, "%d.%m.%Y")).strftime('%d.%m.%Y')
							row['Confirmed Qty. Sched. Line'] = int(x)
							df_schedule_response_new = pd.concat([df_schedule_response_new, pd.DataFrame([row])], ignore_index=True)
							messages.append([str(row['Order Number'].lstrip('0'))+"-"+str(row['Order Position']), row['Original Qty. Sched. Line'], row['Original Date Sched. Line'], y, x, z])					
							continue
						else:
							duplicate_row = df_schedule_response.iloc[index].copy()
							
							duplicate_row['Confirmed Date Sched. Line'] = pd.to_datetime(datetime.strptime(y, "%d.%m.%Y")).strftime('%d.%m.%Y')
							duplicate_row['Confirmed Qty. Sched. Line'] = int(x)
							duplicate_row['Original Date Sched. Line'] = None
							duplicate_row['Original Qty. Sched. Line'] = None
							
							df_schedule_response_new = pd.concat([df_schedule_response_new, duplicate_row.to_frame().T], ignore_index=True)
							
							messages.append([str(row['Order Number'].lstrip('0'))+"-"+str(row['Order Position']), '', row['Original Date Sched. Line'], y, x, z])					
							
				else:
					row['Confirmed Date Sched. Line'] = None
					row['Confirmed Qty. Sched. Line'] = None
	
	df_schedule_response_new['Confirmed Qty. Sched. Line'] = df_schedule_response_new['Confirmed Qty. Sched. Line'].apply(
		lambda x: int(x) if pd.notnull(x) else None
	)

	if not df_schedule_response_new.empty:
		all = pd.concat([df_schedule_response_new, df_clear_confirmations])
		all.to_excel(output, index=False)
		not_found = sorted(not_found, key=lambda x: datetime.strptime(x[-1], "%d.%m.%Y"))
		for m in messages[:]:  # Iterate over a shallow copy
			try:
				if m[1] == 0.0:
					messages.remove(m)
			except:
				continue
		
		return('', not_found, messages, output)
	else:
		return("\nNenasiel som nic k potvrdeniu!!!", [], [], '')

def date_to_week(date_str):
	date = pd.to_datetime(date_str, format="%d.%m.%Y")
	iso_year, iso_week, _ = date.isocalendar()
	cw_string = f"CW{iso_week:02}/{str(iso_year)[-2:]}"  # CW18/25
	return(cw_string)

def get_friday_from_cw(cw_string):
	week, year_suffix = cw_string.replace("CW", "").split("/")
	week = int(week)
	year = int("20" + year_suffix)
	return pd.to_datetime(
		f'{year}-W{week}-5',
		format='%G-W%V-%u'
	).strftime('%d.%m.%Y')

def row_zero_out(row):
    if pd.notna(row['Original Date Sched. Line']) and pd.notna(row['Original Qty. Sched. Line']):
        row['Confirmed Date Sched. Line'] = None
        row['Confirmed Qty. Sched. Line'] = None
    elif (
        pd.isna(row['Original Date Sched. Line']) and
        pd.isna(row['Original Qty. Sched. Line']) and
        pd.notna(row['Confirmed Date Sched. Line'])
    ):
        row['Confirmed Qty. Sched. Line'] = 0
    return row

def clear_confirmations(df_clear_confirmations, row):
	
	row['Confirmed Qty. Sched. Line'] = 0
	
	if pd.notnull(row['Original Date Sched. Line']):
		row['Original Date Sched. Line'] = row['Original Date Sched. Line'].strftime("%d.%m.%Y")
	
	if pd.notnull(row['Confirmed Date Sched. Line']):
		row['Confirmed Date Sched. Line'] = row['Confirmed Date Sched. Line'].strftime("%d.%m.%Y")
	
	if pd.isna(row['Confirmed Date Sched. Line']):
		row['Confirmed Date Sched. Line'] = row['Original Date Sched. Line']
	
	return(row)

check_list = []
def confirm_line(df, plan, position, req_qty, req_day, delta):
	
	plan = str(plan).lstrip('0')
	req_qty = int(req_qty)
	req_day = pd.to_datetime(req_day, format="%d.%m.%Y").strftime("%d.%m.%Y")
	req_wk = date_to_week(req_day)
	
	part_df = df.query('plan == @plan and position == @position')
	
	filtered_df = part_df.copy()
	filtered_df['req_day'] = filtered_df['req_day'].ffill()
	
	#z formatu CW11-12/25 urobi CW12/25
	filtered_df['conf_wk'] = filtered_df['conf_wk'].str.replace(r'CW\d{2}-(\d{2}/\d{2})', r'CW\1', regex=True)
	#akceptuj iba format CWxx/xx, nie random text
	pattern = r'^CW\d{2}(-\d{2})?/(\d{2})$'
	filtered_df = filtered_df[filtered_df['conf_wk'].str.match(pattern, na=False)]
	
	filtered_df['req_day'] = pd.to_datetime(filtered_df['req_day'], dayfirst=True, errors='coerce')  # for DD.MM.YYYY or DD.MM.YY
	
	try:
		filtered_df['req_day'] = filtered_df['req_day'].dt.strftime('%d.%m.%Y')
	except Exception as e:
		print(e)
	
	filtered_df = filtered_df.query('req_day == @req_day')
	
	no_of_batches = filtered_df.shape[0]
	#print(plan, position, req_qty, req_day, delta)
	
	#opt0 - not found
	if(no_of_batches == 0):
		deltas = [-1,1]
		found = 0
		for d in deltas:
			target_day = datetime.strptime(req_day, '%d.%m.%Y')
			check_day = target_day + timedelta(days=d)
			check_list.append(target_day)
			check_day_str = check_day.strftime('%d.%m.%Y')
			if(abs((check_list[0] - check_day).days) > abs(d)):
				break
			else:
				return(None, 0, 0, "Not found")
			result = confirm_line(df, plan, position, req_qty, check_day_str, delta)
			
			if result[0]:
				return(confirm_line(df, plan, position, req_qty, check_day_str, delta))
		return(None, 0, 0, "Not found")
	
	elif(no_of_batches == 1):
		splits_needed = 0
		week_check = date_to_week(req_day)
		week_check_req_wk = filtered_df.iloc[0]['req_wk']
		week_check_conf_wk = filtered_df.iloc[0]['conf_wk']
		if delta > 0:
			week_check_conf_wk = brasil_conf_week(week_check_conf_wk, delta)
		conf_qty = filtered_df.iloc[0]['conf_qty']
		conf_day = req_day
		
		#opt1.1 - one line/batch, date OK, qty OK
		if(week_check == week_check_req_wk == week_check_conf_wk and int(req_qty) == int(conf_qty)):
			return(int(splits_needed), int(conf_qty), conf_day, "OK")
		
		#opt1.2 - one line/batch, date NOK, qty OK
		elif((week_check_req_wk != week_check_conf_wk) and int(req_qty) == int(conf_qty)):
			conf_day = get_friday_from_cw(week_check_conf_wk)
			return(int(splits_needed), int(conf_qty), conf_day, f"POSUNUTE NA {week_check_conf_wk}")
		
		#opt1.3 - one line/batch, date OK, qty NOK
		elif(week_check == week_check_req_wk == week_check_conf_wk and int(req_qty) != int(conf_qty)):
			diff = int(conf_qty) - int(req_qty)
			return(int(splits_needed), int(conf_qty), conf_day, f"ROZDIEL V QTY {diff:+d} pcs")

		#opt1.4 - one line/batch, date NOK, qty NOK
		elif((week_check_req_wk != week_check_conf_wk) and int(req_qty) != int(conf_qty)):
			conf_day = get_friday_from_cw(week_check_conf_wk)
			diff = int(conf_qty) - int(req_qty)
			return(int(splits_needed), int(conf_qty), conf_day, f"POSUNUTE NA {week_check_conf_wk}, ROZDIEL V QTY {diff:+d} pcs")
		else:
			return(None, 0, 0, "A - Nespravny prepocitany tyzden alebo pocet dielcov nie je cele cislo!")
	
	
	elif(no_of_batches > 1):
		week_check = date_to_week(req_day)
		week_check_req_wk = filtered_df.iloc[0]['req_wk']
		week_check_conf_wk = filtered_df.iloc[0]['conf_wk']
		if delta > 0:
			week_check_conf_wk = brasil_conf_week(week_check_conf_wk, delta)
		conf_qty = int(filtered_df.groupby(['plan', 'position', 'req_day'])['conf_qty'].sum().iloc[0])
		conf_day = req_day
		splits_needed = int(filtered_df.groupby(['plan', 'position', 'req_day', 'conf_wk'])['conf_qty'].sum().shape[0]) - 1
		splits_list = list(filtered_df.groupby(['conf_wk'])['conf_qty'].sum().index)
		if delta > 0:
			for i, sl in enumerate(splits_list):
				splits_list[i] = brasil_conf_week(sl, delta)
		qtys_list = list(filtered_df.groupby(['conf_wk'])['conf_qty'].sum())
		
		#opt2.1 - 2 and more lines/batches, dates OK, qtys OK
		if(week_check == week_check_req_wk == week_check_conf_wk and int(req_qty) == int(conf_qty) and splits_needed == 0):
			return(int(splits_needed), int(conf_qty), conf_day, "OK")
		
		#opt2.2 - 2 and more lines/batches, dates OK, qtys NOK
		elif(week_check == week_check_req_wk == week_check_conf_wk and int(req_qty) != int(conf_qty) and splits_needed == 0):
			diff = int(conf_qty) - int(req_qty)
			return(int(splits_needed), int(conf_qty), conf_day, f"ROZDIEL V QTY {diff:+d} pcs")
		
		#opt2.3 - 2 and more lines/batches, dates NOK, qtys OK
		elif(int(req_qty) == int(conf_qty) and splits_needed > 0):
			return(int(splits_needed),[int(x) for x in qtys_list] ,[req_day if n == week_check_req_wk else get_friday_from_cw(n) for n in splits_list] , [f"OK" if n == week_check_req_wk else f"POSUNUTE NA {n}" for n in splits_list])
		
		#opt2.4 - 2 and more lines/batches, dates NOK, qtys NOK
		elif(int(req_qty) != int(conf_qty) and splits_needed > 0):
			diff = int(sum(qtys_list) - int(req_qty))
			return(int(splits_needed),[int(x) for x in qtys_list] ,[req_day if n == week_check_req_wk else get_friday_from_cw(n) for n in splits_list], [f"OK" if n == week_check_req_wk else f"POSUNUTE NA {n}, ROZDIEL V QTY {diff:+d} pcs" for n in splits_list])

		#opt2.5 - 2 and more lines/batches, dates NOK, qtys OK, but no splits needed, all batches in the same week
		elif(int(req_qty) == int(conf_qty) and splits_needed == 0):
			return(int(splits_needed),int(conf_qty) ,get_friday_from_cw(week_check_conf_wk), f"POSUNUTE NA {week_check_conf_wk}")
		
		#opt2.6 - Brasil - 2 and more lines/batches, dates NOK, qtys NOK, but no splits needed, all batches in the same week
		elif(int(req_qty) != int(conf_qty) and splits_needed == 0):
			diff = int(sum(qtys_list) - int(req_qty))
			return(int(splits_needed),int(conf_qty) ,get_friday_from_cw(week_check_conf_wk), f"POSUNUTE NA {week_check_conf_wk}, ROZDIEL V QTY {diff:+d} pcs")
			
		else:
			return(None, 0, 0, "B - Nespravny prepocitany tyzden alebo pocet dielcov nie je cele cislo!")
	
	else:
		return(None, 0, 0, "C - Nespravny prepocitany tyzden alebo pocet dielcov nie je cele cislo!")
