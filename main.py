import os
import argparse
import json
import glob
from tqdm.auto import tqdm
from shutil import copyfile, rmtree
from multiprocessing.pool import ThreadPool


parser = argparse.ArgumentParser(description='Fast converter for audiofiles using ffmpeg')
parser.add_argument('--config', type=str,
					help='config file path', default='default_config.json')
args = parser.parse_args()

with open(args.config) as config_file:
	config = json.load(config_file)
input_dir = config['input_dir']
output_dir = config['output_dir']
threads = config['threads']
is_overwrite = config['is_overwrite']
copy_other_files = config['copy_other_files']
bitrate = config['bitrate']
from_extensions = config['from_extensions']
to_extension = config['to_extension']

def convertAudioFile(file_path, new_file_path):
	os.system(f'ffmpeg -y -i "\\\\?\\{file_path}" -b {bitrate} "\\\\?\\{new_file_path}" > NUL 2>&1')

def convertAllFromDir(input_dir, output_dir, extensions, threads, is_overwrite):
	
	if is_overwrite and os.path.exists(output_dir):
		print('Removing old files...')
		rmtree(output_dir)
	
	audio_files_paths = []
	copy_tasks = []
	
	for file_path in tqdm(filter(os.path.isfile, glob.iglob(input_dir + '/**', recursive=True)), desc='Looking for audiofiles'):
		
		extension = file_path.split('.')[-1]
		if extension in extensions:
			new_file_path = file_path.replace(input_dir, output_dir)
			new_file_path = '.'.join(new_file_path.split('.')[:-1]) + '.' + to_extension
			new_file_list = audio_files_paths
		elif copy_other_files:
			new_file_path = file_path.replace(input_dir, output_dir)
			new_file_list = copy_tasks
		else:
			continue
		
		if not is_overwrite:
			if os.path.exists(new_file_path):
				continue
		new_dir = os.path.dirname(new_file_path)
		if not os.path.exists(new_dir):
			os.makedirs(new_dir)
		new_file_list.append((file_path, new_file_path))
	
	for result in tqdm(
			ThreadPool(threads).imap_unordered(
				lambda p: convertAudioFile(*p), 
				audio_files_paths
			), 
			desc=f'Converting audiofiles from {input_dir}', 
			total=len(audio_files_paths)):
		pass
	
	if copy_other_files:
		for task in tqdm(
				ThreadPool(threads).imap_unordered(
					lambda task: copyfile(*task), 
					copy_tasks
				), 
				desc=f'Copying other files from {input_dir}', 
				total=len(copy_tasks)):
			pass

convertAllFromDir(input_dir, output_dir, from_extensions, threads, is_overwrite)