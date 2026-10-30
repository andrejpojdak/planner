import os
import zipfile
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()
ZLPI_OUTPUT = os.getenv("ZLPI_OUTPUT")
ZLPI_ARCHIVE = os.getenv("ZLPI_ARCHIVE")

def zip_old_files(path):
	
	dir_yyyymm = date.today().strftime("%Y%m")
	zip_filename = str(dir_yyyymm) + "_archive.zip"
	zip_filepath = os.path.join(ZLPI_ARCHIVE, zip_filename)
	today = date.today()

	files_to_zip = []

	for file in os.listdir(path):
		file_path = os.path.join(path, file)

		if file.endswith('.xlsx') and os.path.isfile(file_path):
			mod_time = datetime.fromtimestamp(
				os.path.getmtime(file_path)
			).date()

			if mod_time < today:
				if "filled" in file:
					files_to_zip.append(file_path)
				else:
					os.remove(file_path)

	if files_to_zip:
		with zipfile.ZipFile(zip_filepath, 'a', compression=zipfile.ZIP_DEFLATED) as zipf:
			for file_path in files_to_zip:
				zipf.write(file_path, arcname=os.path.basename(file_path))
				os.remove(file_path)
