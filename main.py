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



def convertAudioFile(file_path, new_file_path):
	os.system(f'ffmpeg -y -i "\\\\?\\{file_path}" -b {config["bitrate"]} "\\\\?\\{new_file_path}" > NUL 2>&1')


def processSequentially(array, function, description):
	for result in tqdm(
			map(
				function,
				array
			),
			desc=description,
			total=len(array)):
		pass


def processInParallel(array, function, description, threads=config['threads']):
	for result in tqdm(
			ThreadPool(threads).imap_unordered(
				function,
				array
			),
			desc=description,
			total=len(array)):
		pass


def removeOldFiles(config):
	print('Removing old files...')
	rmtree(config['output_dir'])


def removeMismatched(config):

	directories_to_remove = []

	for some_path in tqdm(
		filter(
			lambda p: (
				(not os.path.isfile(p)) and 
				(not os.path.exists(p.replace(config['output_dir'], config['input_dir'])))
			), 
			glob.iglob(config['output_dir'] + '/**', recursive=True)
		), 
		desc='Removing mismatched directories'
	):
		rmtree(some_path)


def convertAll(config):
	
	audio_files_paths = []
	
	for file_path in tqdm(filter(os.path.isfile, glob.iglob(config['input_dir'] + '/**', recursive=True)), desc='Looking for audiofiles'):
		
		extension = file_path.split('.')[-1]
		if extension in config['from_extensions']:
			new_file_path = file_path.replace(config['input_dir'], config['output_dir'])
			new_file_path = '.'.join(new_file_path.split('.')[:-1]) + '.' + config['to_extension']
		else:
			continue
		
		if not config['is_overwrite']:
			if os.path.exists(new_file_path):
				continue
		new_dir = os.path.dirname(new_file_path)
		if not os.path.exists(new_dir):
			os.makedirs(new_dir)
		audio_files_paths.append((file_path, new_file_path))

	processInParallel(audio_files_paths, lambda p: convertAudioFile(*p), f'Converting audiofiles from {config["input_dir"]}')


def copyOtherFiles(config):

	copy_tasks = []

	for file_path in tqdm(filter(os.path.isfile, glob.iglob(config['input_dir'] + '/**', recursive=True)), desc='Looking for other files'):
		extension = file_path.split('.')[-1]
		if not extension in config['from_extensions']:
			new_file_path = file_path.replace(config['input_dir'], config['output_dir'])
			if not os.path.exists(new_file_path):
				new_dir = os.path.dirname(new_file_path)
				if not os.path.exists(new_dir):
					os.makedirs(new_dir)
				copy_tasks.append((file_path, new_file_path))

	processInParallel(copy_tasks, lambda task: copyfile(*task), f'Copying other files from {config["input_dir"]}')


def processTasks(tasks, config):
	for function, condition in tasks:
		if condition:
			function(config)



processTasks([
		(removeOldFiles,	config['is_overwrite'] and os.path.exists(config['output_dir'])),
		(removeMismatched,	config['sync'] and (not config['is_overwrite'])), 
		(convertAll,		True),
		(copyOtherFiles,	config['copy_other_files'])
	],
	config
)