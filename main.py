import os
import argparse
import json
import glob
import hashlib
from functools import partial, reduce
from operator import methodcaller
from tqdm.auto import tqdm
from shutil import copyfile, rmtree
from multiprocessing.pool import ThreadPool



parser = argparse.ArgumentParser(description='Fast converter for audiofiles using ffmpeg')
parser.add_argument('--config', type=str,
					help='config file path', default='default_config.json')
args = parser.parse_args()

with open(args.config) as config_file:
	config = json.load(config_file)

if os.path.exists(config['cache_file']):
	with open('cache.json') as cache_file:
		cache = json.load(cache_file)
else:
	cache = {}
cache_changed = False


def dumpCache():
	global cache_changed
	if not cache_changed:
		return
	print(f'Cache changed {cache_changed} times, dumping...')
	with open(config['cache_file'], 'w') as cache_file:
		json.dump(cache, cache_file, indent='\t')
	cache_changed = False


def pipe(input_value, *functions):
	return reduce(lambda result, f: f(result), functions, input_value)


def useCache(cache, keys_to_compute):
	
	def decorator(function):
		
		def newFunction(*args, **kwargs):
			
			keys = {}
			
			for k in keys_to_compute:
				arg_name = keys_to_compute[k]['input_arg']
				initial_value = kwargs[arg_name]
				result = pipe(initial_value, *keys_to_compute[k]['functions'])
				keys[k] = result if type(result) == str else str(result)
			
			joint_key = '__'.join([keys[k] for k in sorted(keys.keys())])
			
			new_key = False
			if function.__name__ in cache:
				if joint_key in cache[function.__name__]:
					return cache[function.__name__][joint_key]
				else:
					new_key = True
			else:
				cache[function.__name__] = {}
				new_key = True

			if new_key:
				cache[function.__name__][joint_key] = function(*args, **kwargs)
				global cache_changed
				cache_changed += 1
				# dumpCache()
			
			return cache[function.__name__][joint_key]
		
		return newFunction
	
	return decorator


@useCache(cache, {
	'path': {
		'input_arg': 'file_path',
		'functions': []
	},
	'modified_time': {
		'input_arg': 'file_path',
		'functions': [
			os.path.getmtime
		]
	}
	# 'md5': {
	# 	'input_arg': 'file_path',
	# 	'functions': [
	# 		partial(open, mode='rb'), 
	# 		methodcaller('read'),
	# 		hashlib.md5,
	# 		methodcaller('digest')
	# 	]
	# }
})
def isAudioFileOk(file_path):
	return 0 == os.system(f'ffmpeg -i "{file_path}" -c copy -f null - > NUL 2>&1')

# isAudioFileOk(file_path=r'F:\music_mp3\Cor\Wake - Devouring Ruin 2020\Wake - Devouring Ruin.mp3')
# exit()


def disableLengthLimit(path):
	return '\\\\?\\' + path


def convertAudioFile(file_path, new_file_path):
	os.system(f'ffmpeg -y -i "{file_path}" -b {config["bitrate"]} "{new_file_path}" > NUL 2>&1')


def processSequentially(array, function, description):
	for result in tqdm(
			map(
				function,
				array
			),
			desc=description,
			total = len(array) if type(array) == list else None):
		pass


def processInParallel(array, function, description, threads=config['threads']):
	for result in tqdm(
			ThreadPool(threads).imap_unordered(
				function,
				array
			),
			desc=description,
			total = len(array) if type(array) == list else None):
		pass


def removeOldFiles(config):
	print('Removing old files...')
	rmtree(config['output_dir'])


def removeMismatched(config):

	directories_to_remove = []

	processSequentially(
		filter(
			lambda p: (
				(not os.path.isfile(p)) and 
				(not os.path.exists(p.replace(config['output_dir'], config['input_dir'])))
			), 
			map(disableLengthLimit, glob.iglob(config['output_dir'] + '/**', recursive=True))
		), 
		rmtree,
		'Removing mismatched directories'
	)


def removeInvalidTargetAudiofiles(config):

	invalid_files_paths = []

	processInParallel(
		filter(
			lambda p: (
				os.path.isfile(p) and 
				(p.split('.')[-1] == config['to_extension'])
			), 
			map(disableLengthLimit, glob.iglob(config['output_dir'] + '/**', recursive=True))
		), 
		lambda p: invalid_files_paths.append(p) if not isAudioFileOk(file_path=p) else None,
		'Checking target audiofiles integrity'
	)
	dumpCache()

	processInParallel(
		invalid_files_paths, 
		os.remove, 
		'Removing invalid target audiofiles'
	)


def convertAll(config):
	
	audio_files_paths = []
	
	for file_path in tqdm(filter(os.path.isfile, map(disableLengthLimit, glob.iglob(config['input_dir'] + '/**', recursive=True))), desc='Looking for audiofiles'):
		
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

	for file_path in tqdm(filter(os.path.isfile, map(disableLengthLimit, glob.iglob(config['input_dir'] + '/**', recursive=True))), desc='Looking for other files'):
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
		(removeOldFiles,				config['is_overwrite'] and os.path.exists(config['output_dir'])),
		(removeMismatched,				config['sync'] and (not config['is_overwrite'])), 
		(removeInvalidTargetAudiofiles,	True), 
		(convertAll,					True), 
		(copyOtherFiles,				config['copy_other_files']) 
	],
	config
)