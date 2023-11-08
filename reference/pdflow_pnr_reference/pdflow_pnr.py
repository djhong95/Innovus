import glob
import os.path
import re

import pdflow
import libdb

from flow_utils import *
import flow_log_utils
import flow_args_utils
import flow_module_utils
import flow_file_utils
import flow_run_utils
import flow_tcl_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS

lib_db: libdb.LibDb
pnr_input_collaterals: List[str]
pnr_reports: List[str]
pnr_sessions: List[str]


def is_stage_done(stage: str) -> bool:
	'''
	check whether the specified stage is already done or not

	:param stage: stage to check
	:return: True if the stage is done. Otherwise, False
	'''
	if os.path.exists(os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', stage, flow_file_utils.join_filename(stage, 'done'))):
		return True
	else:
		return False


def get_prev_stage(stage: str) -> Union[str, None]:
	'''
	get the name of the previous stage

	:param stage: current stage
	:return: if there is a previous stage, return the stage name. if there is not, return None
	'''
	stage_idx = pdflow.supported_pnr_stages.index(stage)
	if stage_idx > 0:
		return pdflow.supported_pnr_stages[stage_idx-1]
	else:
		return None


def get_prev_session_dir(stage: str, design_name: str = None) -> Union[str, None]:
	'''
	get the session directory of the previous stage

	:param stage: current stage
	:param design_name: the name of the design (if None, it will use FLOW_ENVS['BLOCK'])
	:return: if there is a previous stage, return the path to the session directory. if there is not, return None
	'''
	prev_stage = get_prev_stage(stage)
	if design_name is None:
		design_name = FLOW_ENVS['BLOCK']
	if prev_stage is not None:
		prev_stage_session_dir = os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'], prev_stage, 'sessions', flow_file_utils.join_filename(design_name, prev_stage, 'enc'))
		return prev_stage_session_dir
	else:
		return None


def get_prev_result_dir(stage: str) -> Union[str, None]:
	'''
	get the result directory of the previous stage

	:param stage: current stage
	:return: if there is a previous stage, return the path to the session directory. if there is not, return None
	'''
	prev_stage = get_prev_stage(stage)
	if prev_stage is not None:
		prev_stage_results_dir = os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'], prev_stage, 'results')
		return prev_stage_results_dir
	else:
		return None


def get_session_file(stage: str, design_name: str = None) -> str:
	'''
	get the session file of the current stage

	:param stage: current stage
	:param design_name: the name of the design (if None, it will use FLOW_ENVS['BLOCK'])
	:return: session file for the current stage
	'''
	if design_name is None:
		design_name = FLOW_ENVS['BLOCK']
	return os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'], stage, 'sessions', flow_file_utils.join_filename(design_name, stage, 'enc'))


def get_session_dir(stage: str, design_name: str = None) -> str:
	'''
	get the session directory of the current stage

	:param stage: current stage
	:param design_name: the name of the design (if None, it will use FLOW_ENVS['BLOCK'])
	:return: session directory for the current stage
	'''
	if design_name is None:
		design_name = FLOW_ENVS['BLOCK']
	return os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'], stage, 'sessions', flow_file_utils.join_filename(design_name, stage, 'enc', 'dat'))


def get_result_dir(stage: str) -> Union[str, None]:
	'''
	get the result directory for the current stage

	:param stage: current stage
	:return: result directory for the current stage
	'''
	return os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'], stage, 'results')


def innovus_start_commands(tcl: flow_tcl_utils.TclFile, restore_design: bool = True, design_name: str = None):
	'''
	put start up commands in innovus tcl script

	:param tcl: innovus tcl script object
	:param restore_design: if True, restore session from the previous stage
	:param design_name: when restore from the previous stage, if this variable is not None, restore the session from FLOW_ENVS['WORK_AREA']/FLOW_ENVS['FLOW']/FLOW_ENVS['STAGE'](previous)/'sessions'/design_name.prev_stage.enc
	'''
	global pnr_input_collaterals

	# suppress expected warnings
	if pdflow.is_compact2D_flow():
		# **WARN: (IMPEXT-3570): PostRoute (EffortLevel high) resistance scaling factor 0.707 for corner rc_fast is different than the expected 1.0 to match signoff Quantus QRC. Check that it is intended.
		# resistance/capacitances are intentionally scaled in compact2d flow
		tcl.write('set_message -id IMPEXT-3570 -suppress')
		tcl.write('')

	# setup resource monitor
	tcl.write_section_comment('setup resource monitor')
	tcl.write('package require flow_utils')
	tcl.write('namespace import flow_utils::*')
	tcl.write('package require pdflowEDI_run_utils')
	tcl.write('')
	start_resmon_opts = {
		'-tool': FLOW_ENVS['TOOL'],
	}
	resmon_chkpts = get_dict(FLOW_CFGS, FLOW_ENVS['TOOL'].upper(), 'RESMON_CHKPTS', FLOW_ENVS['FLOW'].upper(), FLOW_ENVS['STAGE'].upper())
	if resmon_chkpts is not None:
		chkpts_file = os.path.join(FLOW_ENVS['RUN_DIR'], flow_file_utils.join_filename('resmon', 'chkpts'))
		ofp = flow_file_utils.open_wfile(chkpts_file, force=True)
		for chkpt_name, chkpt_pattern in resmon_chkpts.items():
			ofp.write('%s %s\n' % (chkpt_name, chkpt_pattern))
		ofp.close()
		start_resmon_opts['-chkpts_file'] = chkpts_file
		start_resmon_opts['-tool_log_file'] = '[getLogFileName]'
	tcl.write_cmd_w_opts('flow_utils::start_resmon', start_resmon_opts)
	tcl.write('pdflowEDI_run_utils::setup_log')

	# host settings
	tcl.write_section_comment('host settings')
	dist_host_opts = {'-local': None}
	tcl.write_cmd_w_opts('setDistributeHost', dist_host_opts)
	multi_cpu_opts = {'-localCpu': 8, '-remoteHost': 0, '-cpuPerRemoteHost': 1}
	tcl.write_cmd_w_opts('setMultiCpuUsage', multi_cpu_opts)
	tcl.write('')

	# restore design
	tcl.write_section_comment('restore design')
	if restore_design and get_prev_stage(FLOW_ENVS['STAGE']) is not None:
		if design_name is None:
			design_name = FLOW_ENVS['BLOCK']
		session_dir = get_prev_session_dir(FLOW_ENVS['STAGE'], design_name)
		tcl.write('restoreDesign %s %s' % (flow_file_utils.join_filename(session_dir, 'dat'), design_name))
		tcl.write('')
		pnr_input_collaterals.append(flow_file_utils.join_filename(session_dir, 'dat'))

	# load flow envs/cfgs/vars
	tcl.write_section_comment('load flow envs/cfgs/vars')
	tcl.write('package require json')
	flow_envs_json_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('flow_envs', 'json'))
	tcl.write('set fp [open "%s" r]' % (flow_envs_json_file))
	pnr_input_collaterals.append(flow_envs_json_file)
	tcl.write('set flow_envs_data [read $fp]')
	tcl.write('close $fp')
	tcl.write('set FLOW_ENVS [::json::json2dict $flow_envs_data]')

	flow_cfgs_json_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('flow_cfgs', 'json'))
	tcl.write('set fp [open "%s" r]' % (flow_cfgs_json_file))
	pnr_input_collaterals.append(flow_cfgs_json_file)
	tcl.write('set flow_cfgs_data [read $fp]')
	tcl.write('close $fp')
	tcl.write('set FLOW_CFGS [::json::json2dict $flow_cfgs_data]')

	flow_vars_json_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('flow_vars', 'json'))
	tcl.write('set fp [open "%s" r]' % (flow_vars_json_file))
	pnr_input_collaterals.append(flow_vars_json_file)
	tcl.write('set flow_vars_data [read $fp]')
	tcl.write('close $fp')
	tcl.write('set FLOW_VARS [::json::json2dict $flow_vars_data]')
	tcl.write('')


def innovus_end_commands(tcl: flow_tcl_utils.TclFile, save_design: bool = True, design_name: str = None):
	'''
	put ending commands in innovus tcl script

	:param tcl: innovus tcl script object
	:param save_design: if True, save the current session at the end
	:param design_name: if this variable is not None, save the session to FLOW_ENVS['WORK_AREA']/FLOW_ENVS['FLOW']/FLOW_ENVS['STAGE']/'sessions'/design_name.FLOW_ENVS['STAGE'].enc. Otherwise, FLOW_ENVS['WORK_AREA']/FLOW_ENVS['FLOW']/FLOW_ENVS['STAGE']/'sessions'/FLOW_ENVS['BLOCK'].FLOW_ENVS['STAGE'].enc
	'''
	tcl.write('')
	if design_name is None:
		design_name = FLOW_ENVS['BLOCK']
	if save_design:
		session_dir = get_session_file(FLOW_ENVS['STAGE'], design_name)
		save_design_opts = {
			session_dir: None,
			'-compress': None,
			'-verilog': None,
		}
		tcl.write_cmd_w_opts('saveDesign', save_design_opts)
		tcl.write('')
	tcl.write('flow_utils::end_resmon')
	tcl.write('exit 1')


def innovus_final_result_commands(tcl: flow_tcl_utils.TclFile, design_name: str = None):
	'''
	put commands for producing final outputs in innovus tcl script

	:param tcl: innovus tcl script object
	:param design_name: if this variable is not None, save the session to FLOW_ENVS['WORK_AREA']/FLOW_ENVS['FLOW']/FLOW_ENVS['STAGE']/'sessions'/design_name.FLOW_ENVS['STAGE'].enc. Otherwise, FLOW_ENVS['WORK_AREA']/FLOW_ENVS['FLOW']/FLOW_ENVS['STAGE']/'sessions'/FLOW_ENVS['BLOCK'].FLOW_ENVS['STAGE'].enc
	'''
	global pnr_input_collaterals

	if design_name is None:
		design_name = FLOW_ENVS['BLOCK']

	tcl.write_section_comment('run extraction')
	# to avoid license problem, we need to use TQuantus instead of IQuantus
	# (from user guide) TQuantus extraction engine is recommended for the implementation phase because it is optimized for performance with a small tradeoff for accuracy. IQuantus extraction engine is recommended for ECO flow, as it has near-signoff accuracy
	# TQuantus: -effortLevel medium
	# IQuantus: -effortLevel high
	extractrcmode_opts = {
		'-effortLevel': 'medium',
		'-engine': 'postRoute',
		'-total_c_th': '0',
		'-relative_c_th': '0.03',
		'-coupling_c_th': '1',
	}
	tcl.write_cmd_w_opts('setExtractRCMode', extractrcmode_opts)
	tcl.write('extractRC')

	tcl.write_section_comment('write output collaterals')
	write_sdf_opts = {
		'-precision': 4,
		os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, 'sdf')): None,
	}
	tcl.write_cmd_w_opts('write_sdf', write_sdf_opts)

	tcl.write('foreach rc_corner [all_rc_corners -active] {')
	rcout_opts = {
		'-rc_corner': '$rc_corner',
		'-spef': os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, '$rc_corner', 'spef', 'gz'))
	}
	tcl.write_cmd_w_opts('rcOut', rcout_opts)
	tcl.write('}')

	lefdef_ver = get_dict(FLOW_CFGS, 'PROJECT_CFG', 'TOOL', 'INNOVUS', 'LEFDEF_VERSION')
	if lefdef_ver is not None:
		lefdef_ver = 5.8
	tcl.write('set lefDefOutVersion %.1f' % (lefdef_ver))
	defout_opts = {
		'-floorplan': None,
		'-routing': None,
		os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, 'def', 'gz')): None,
	}
	tcl.write_cmd_w_opts('defOut', defout_opts)

	tcl.write('saveNetlist %s' % (
		os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, 'v', 'gz'))))
	tcl.write('write_power_intent %s -1801' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, 'upf'))))

	#tcl.write('foreach analysis_view [all_setup_analysis_views] {')
	#do_ext_model_opts = {
	#	'-view': '$analysis_view',
	#	'-blackbox': None,
	#	os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, '$analysis_view', 'lib')): None
	#}
	#tcl.write_cmd_w_opts('do_extract_model', do_ext_model_opts)
	#tcl.write('}')

	#max_route_layer = get_dict(FLOW_VARS, 'PNR_NUM_ROUTE_LAYER')
	#if max_route_layer is not None:
	#	lefout_opts = {
	#		'-specifyTopLayer': FLOW_VARS['PNR_NUM_ROUTE_LAYER'],
	#	}
	#else:
	#	lefout_opts = {}
	#lefout_opts[os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, 'lef'))] = None
	#tcl.write_cmd_w_opts('write_lef_abstract', lefout_opts)

	lefdef2gds_layermap = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'INNOVUS_LEFDEF2GDS_LAYERMAP')
	if lefdef2gds_layermap is not None:
		streamout_opts = {
			'-mapFile': os.path.join(FLOW_ENVS['WORK_AREA'], 'library', lefdef2gds_layermap),
			'-libName': FLOW_ENVS['BLOCK'],
			'-structureName': FLOW_ENVS['BLOCK'],
			'-mode': 'All',
			'-units': '[dbGet head.dbUnits]',
			os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, 'gds')): None,
		}
		tcl.write_cmd_w_opts('streamOut', streamout_opts)
		pnr_input_collaterals.append(os.path.join(FLOW_ENVS['WORK_AREA'], 'library', lefdef2gds_layermap))

	tcl.write('summaryReport -outdir %s' % (os.path.join(FLOW_ENVS['REPORT_DIR'], '%s_summary' % design_name)))

def get_wirelength(tcl: flow_tcl_utils.TclFile, sort: str):

	global pnr_input_collaterals

	tcl.write_section_comment('obtain wire-length')
	tcl.write('reportWire -detail -summary -sort %s wire_report' % (sort))

def get_target_stages(target_stage: str) -> List[str]:
	'''
	return list of stages need to perform to reach the target_stage

	:param target_stage: stage to run
	:return: list of stages need to perform to reach the target_stage
	'''
	#TODO: need to check syn as well
	prev_stage_done_last_modified = -1
	start_stage = pdflow.supported_pnr_stages[0]
	end_stage = target_stage
	for cur_stage in pdflow.supported_pnr_stages[:pdflow.supported_pnr_stages.index(end_stage)+1]:
		start_stage = cur_stage
		if not is_stage_done(cur_stage):
			break
		else:
			cur_stage_done_file = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', cur_stage, flow_file_utils.join_filename(cur_stage, 'done'))
			cur_stage_done_last_modified = os.stat(cur_stage_done_file).st_mtime
			if prev_stage_done_last_modified > cur_stage_done_last_modified:
				break
			else:
				prev_stage_done_last_modified = cur_stage_done_last_modified
	return pdflow.supported_pnr_stages[pdflow.supported_pnr_stages.index(start_stage):pdflow.supported_pnr_stages.index(end_stage)+1]


def get_lef_files() -> List[str]:
	'''
	get a list of tech LEF and macro LEF used in design

	:return: list of tech LEF and macro LEF files
	'''
	if 'lib_db' in globals():
		global lib_db
	else:
		lib_db = libdb.LibDb()

	logger = flow_log_utils.start_logging()
	tech_lef = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'TECH_LEF')
	if tech_lef is None:
		logger.error('FLOW_CFGS[TECH_CFG:PDK:TECH_LEF] not defined.')
		lef_files = []
	else:
		if type(tech_lef) is not list:
			lef_files = [os.path.join(FLOW_ENVS['WORK_AREA'], 'library', tech_lef)]
		else:
			lef_files = [os.path.join(FLOW_ENVS['WORK_AREA'], 'library', f) for f in tech_lef]
	lef_files += lib_db.query(class_name='cell', view_list=['lef'])
	if pdflow.has_memory():
		if FLOW_ENVS['IMPL_TYPE'] != '2d' and (FLOW_ENVS['STAGE'] in ['init', 'floorplan']):
			import pdflow_lefdef_utils
			macro_lefs = [os.path.join(FLOW_ENVS['WORK_AREA'], 'library', 'memory', 'lef', f + '.lef') for f in FLOW_VARS['MEMORY_CELLS']]
			tlef = [os.path.join(FLOW_ENVS['WORK_AREA'], 'library', f) for f in tech_lef]
			mLEF = pdflow_lefdef_utils.LEF(tlef)

			for macro_lef in macro_lefs:
				expanded_name = 'expanded_' + os.path.basename(macro_lef)
				shrunk_name = 'shrunk_' + os.path.basename(macro_lef)
				if os.path.exists(os.path.join(FLOW_ENVS['WORK_AREA'], expanded_name)):
					pass
				else:
					mLEF.read_lef([macro_lef])
					mLEF.scale_macro(scale_factor=1.414, preserve_pins=False)
					mLEF.write_lef(os.path.join(FLOW_ENVS['WORK_AREA'], expanded_name), only_macro=True)

				exist_shrunk = os.path.exists(os.path.join(FLOW_ENVS['WORK_AREA'], shrunk_name))

				if (FLOW_VARS['PNR_FPLAN_INIT_DEF'] is None) or (not exist_shrunk):
					lef_files += [os.path.join(FLOW_ENVS['WORK_AREA'], expanded_name)]
				else:
					lef_files += [os.path.join(FLOW_ENVS['WORK_AREA'], shrunk_name)]

		else:
			lef_files += lib_db.query(class_name='memory', cell_list=FLOW_VARS['MEMORY_CELLS'], view_list=['lef'])
	return lef_files


def get_session_designs(stage: str) -> List[str]:
	'''
	get a list of design names in the specified stage's session directory

	:param stage: stage to find designs in the session directory
	:return: list of designs in the session directory of the specified stage
	'''
	session_dir = os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'], stage, 'sessions')
	dirs = [d for d in os.listdir(session_dir) if os.path.isdir(os.path.join(session_dir, d))]
	dirs = sorted([str(d.split('.')[0]) for d in dirs])
	return dirs


def write_mmmc(filename: str, lib_files_override: Dict[str, List[str]] = None, qx_tech_file_override: Dict[str, str] = None, sdc_file_override: str = None) -> int:
	"""
	write a mmmc file used in innnovus

	:param filename: path to mmmc file
	:param lib_files_override: if you want to use your own lib files instead of the defaults set in technology, use this. {corner_name: [list of lib files]}
	:param qx_tech_file_override: if you want to use your own qrcTechFile instead of the default set in technology, use this. {corner_name: qrcTechFile}
	:param sdc_file_override: if you want to use your own sdc file instead of the result from synthesis, use this. path to sdc file
	:return: 0 if script is generated successfully. Otherwise, 1
	"""
	ret = 0

	global lib_db
	global pnr_input_collaterals

	logger = flow_log_utils.start_logging()
	mmmc_tcl = flow_tcl_utils.TclFile(filename=filename)

	required_lib = {}
	required_rc = []
	for corner_name, corner_info in get_dict(FLOW_CFGS, 'TECH_CFG', 'CORNERS').items():
		if '_'.join(corner_info['PVT']) not in required_lib:
			required_lib['_'.join(corner_info['PVT'])] = corner_info['PVT']
		if corner_info['RC'] not in required_rc:
			required_rc.append(corner_info['RC'])

	mmmc_tcl.write_subsection_comment('define library set')
	for lib_name, lib_pvts in required_lib.items():
		if lib_files_override is not None:
			lib_files = []
			for pvt in lib_pvts:
				if pvt in lib_files_override:
					lib_files += [os.path.abspath(lib_file) for lib_file in lib_files_override[pvt]]
		else:
			lib_files = lib_db.query(class_name='cell', view_list=['lib'], corner_list=lib_pvts)
			if pdflow.has_memory():
				lib_files += lib_db.query(class_name='memory', cell_list=FLOW_VARS['MEMORY_CELLS'], view_list=['lib'], corner_list=lib_pvts)
		libset_opt = {
			'-name': '_'.join(['libset', lib_name]),
			'-timing': flow_tcl_utils.get_list(lib_files),
		}
		mmmc_tcl.write_cmd_w_opts('create_library_set', libset_opt)
		mmmc_tcl.write('')
		pnr_input_collaterals += lib_files

	mmmc_tcl.write_subsection_comment('define rc corners')
	for corner in required_rc:
		rc_opts = {
			'-name': '_'.join(['rc', corner]),
		}
		if qx_tech_file_override is not None and corner in qx_tech_file_override:
			rc_opts['-qx_tech_file'] = os.path.abspath(qx_tech_file_override[corner])
		else:
			qx_tech_file = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'QRC', corner)
			if qx_tech_file is None:
				logger.error('FLOW_CFGS[TECH_CFG:PDK:QRC:%s] not defined. RC corner for %s cannot be defined' % (corner, corner))
				ret = 1
			else:
				rc_opts['-qx_tech_file'] = os.path.join(FLOW_ENVS['WORK_AREA'], 'library', qx_tech_file)
		mmmc_tcl.write_cmd_w_opts('create_rc_corner', rc_opts)
		mmmc_tcl.write('')
		pnr_input_collaterals.append(rc_opts['-qx_tech_file'])

		#if pdflow.is_compact2D_flow() and FLOW_ENVS['STAGE'] in pdflow.supported_pnr_2d_stages:
		#if pdflow.is_3D_design() and FLOW_ENVS['STAGE'] in pdflow.supported_pnr_2d_stages:
		#	update_rc_opts = {
		#		'-name': '_'.join(['rc', corner]),
		#		'-postRoute_cap': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
		#		'-postRoute_clkcap': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
		#		'-postRoute_clkres': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
		#		'-postRoute_res': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
		#		'-postRoute_xcap': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
		#		'-preRoute_cap': '"%.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
		#		'-preRoute_clkcap': '"0"',
		#		'-preRoute_clkres': '"0"',
		#		'-preRoute_res': '"%.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'])
		#	}
		#	mmmc_tcl.write_cmd_w_opts('update_rc_corner', update_rc_opts)

	mmmc_tcl.write_subsection_comment('define delay corners')
	for corner_name, corner_info in get_dict(FLOW_CFGS, 'TECH_CFG', 'CORNERS').items():
		dc_opts = {
			'-name': '_'.join(['dc', corner_name]),
			'-library_set': '_'.join(['libset', '_'.join(corner_info['PVT'])]),
			'-rc_corner': '_'.join(['rc', corner_info['RC']]),
		}
		mmmc_tcl.write_cmd_w_opts('create_delay_corner', dc_opts)
		pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
		dc_opts = {
			'-name': '_'.join(['dc', corner_name]),
			'-power_domain': '_'.join(['PD', pwr_net]),
		}
		mmmc_tcl.write_cmd_w_opts('update_delay_corner', dc_opts)
		mmmc_tcl.write('')

	mmmc_tcl.write_subsection_comment('define constraint modes')
	if sdc_file_override is not None:
		syn_sdc_file = os.path.abspath(sdc_file_override)
	else:
		syn_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'syn', 'results')
		syn_sdc_file = os.path.join(syn_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdc'))
	constraints_opts ={
		'-name': '_'.join(['PM', 'on']),
		'-sdc_files': syn_sdc_file,
	}
	mmmc_tcl.write_cmd_w_opts('create_constraint_mode', constraints_opts)
	mmmc_tcl.write('')
	pnr_input_collaterals.append(syn_sdc_file)

	mmmc_tcl.write_subsection_comment('define views')
	for corner_name, corner_info in get_dict(FLOW_CFGS, 'TECH_CFG', 'CORNERS').items():
		view_opts = {
			'-name': '_'.join(['view', corner_name]),
			'-constraint_mode': '_'.join(['PM', 'on']),
			'-delay_corner': '_'.join(['dc', corner_name]),
		}
		mmmc_tcl.write_cmd_w_opts('create_analysis_view', view_opts)
	mmmc_tcl.write_section_comment('view setup')
	# if we don't add POWER view in set_analysis_view, it will cast error when we do 'report_power' with POWER view (the view is inactive)
	# so let's just add them in SETUP and HOLD views (it will not affect the result as POWER views are normally 'typical')
	setup_corners = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'CORNERS', 'SETUP') + get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'CORNERS', 'POWER')
	scaled_rc_corners = []
	if pdflow.is_3D_design() and FLOW_ENVS['STAGE'] in pdflow.supported_pnr_2d_stages:
		for setup_corner in setup_corners:
			rc_corner = get_dict(FLOW_CFGS, 'TECH_CFG', 'CORNERS', setup_corner, 'RC')
			if rc_corner not in scaled_rc_corners:
				update_rc_opts = {
					'-name': '_'.join(['rc', rc_corner]),
					'-postRoute_cap': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
					'-postRoute_clkcap': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
					'-postRoute_clkres': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
					'-postRoute_res': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
					'-postRoute_xcap': '"%.3f %.3f %.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'], FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
					'-preRoute_cap': '"%.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR']),
					'-preRoute_clkcap': '"0"',
					'-preRoute_clkres': '"0"',
					'-preRoute_res': '"%.3f"' % (FLOW_VARS['PNR_COMPACT2D_DERATE_FACTOR'])
				}
				mmmc_tcl.write_cmd_w_opts('update_rc_corner', update_rc_opts)
				scaled_rc_corners.append(rc_corner)
		mmmc_tcl.write('')

	setup_views = ['view_'+corner for corner in setup_corners]
	setup_views = flow_tcl_utils.get_list(setup_views)
	hold_corners = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'CORNERS', 'HOLD') + get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'CORNERS', 'POWER')
	hold_views = ['view_'+corner for corner in hold_corners]
	hold_views = flow_tcl_utils.get_list(hold_views)
	set_view_opts = {
		'-setup': setup_views,
		'-hold': hold_views,
	}
	mmmc_tcl.write_cmd_w_opts('set_analysis_view', set_view_opts)
	mmmc_tcl.write('')
	mmmc_tcl.close()

	return ret


def write_upf(filename: str) -> int:
	'''
	write a upf file (power intention file)

	:param filename: path to upf file
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0
	global lib_db

	logger = flow_log_utils.start_logging()
	upf_tcl = flow_tcl_utils.TclFile(filename=filename)

	upf_tcl.write('upf_version 2.0')
	upf_tcl.write('')

	power_corner = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'CORNERS', 'POWER')
	if power_corner is None:
		logger.error('FLOW_CFGS[TECH_CFG:PNR:CORNERS:POWER] not defined. nominal voltage cannot be defined correctly')
		nom_voltage = lib_db.query(class_name='cell', view_list=['lib'], return_field='nom_voltage')[0]
		ret = 1
	else:
		nom_voltage = lib_db.query(class_name='cell', view_list=['lib'], corner_list=power_corner[0], return_field='nom_voltage')[0]

	pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
	pwr_port = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
	upf_tcl.write('create_supply_net %s' % (pwr_net))
	upf_tcl.write('create_supply_port %s' % (pwr_port))
	connect_supply_net_opts = {
		pwr_net: None,
		'-ports': pwr_port,
	}
	upf_tcl.write_cmd_w_opts('connect_supply_net', connect_supply_net_opts)

	gnd_net = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
	gnd_port = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
	upf_tcl.write('create_supply_net %s' % (gnd_net))
	upf_tcl.write('create_supply_port %s' % (gnd_port))
	connect_supply_net_opts = {
		gnd_net: None,
		'-ports': gnd_port,
	}
	upf_tcl.write_cmd_w_opts('connect_supply_net', connect_supply_net_opts)

	supply_set_name = 'SS_%s' % (pwr_net)
	create_supply_set_opts = {
		supply_set_name: None,
		'-function {power %s}' % (pwr_net): None,
		'-function {ground %s}' % (gnd_net): None,
	}
	upf_tcl.write_cmd_w_opts('create_supply_set', create_supply_set_opts)

	power_domain_name = 'PD_%s' % (pwr_net)
	pd_opts = {
		power_domain_name: None,
		'-include_scope': None,
		'-supply': '{primary %s}' % (supply_set_name),
	}
	upf_tcl.write_cmd_w_opts('create_power_domain', pd_opts)

	add_power_state_opts = {
		supply_set_name: None,
		'-state on': '{-supply_expr { power == `{FULL_ON, %s} && ground == `{FULL_ON, 0.0}}}' % (nom_voltage),
		'-state off': '{-supply_expr { power == `{OFF} && ground == `{FULL_ON, 0.0}}}',
	}
	upf_tcl.write_cmd_w_opts('add_power_state', add_power_state_opts)

	add_power_state_opts = {
		power_domain_name: None,
		'-state PM_on': '{-logic_expr { %s == on }}' % (supply_set_name),
		'-state PM_off': '{-logic_expr { %s == off }}' % (supply_set_name),
	}
	upf_tcl.write_cmd_w_opts('add_power_state', add_power_state_opts)
	upf_tcl.close()

	return ret


def write_cpf(filename: str) -> int:
	'''
	write a cpf file (power intention file for Cadence tools only)

	:param filename: path to cpf file
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	logger = flow_log_utils.start_logging()
	cpf_tcl = flow_tcl_utils.TclFile(filename=filename)

	cpf_tcl.write('set_cpf_version 2.0')
	cpf_tcl.write('set_hierarchy_separator /')
	cpf_tcl.write('')

	cpf_tcl.write('set_design %s' % (FLOW_ENVS['BLOCK']))
	cpf_tcl.write('')

	power_corner = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'CORNERS', 'POWER')
	if power_corner is None:
		logger.error('FLOW_CFGS[TECH_CFG:PNR:CORNERS:POWER] not defined. nominal voltage cannot be defined correctly')
		nom_voltage = lib_db.query(class_name='cell', view_list=['lib'], return_field='nom_voltage')[0]
		ret = 1
	else:
		nom_voltage = lib_db.query(class_name='cell', view_list=['lib'], corner_list=power_corner, return_field='nom_voltage')[0]
	pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
	pwr_nets_opts = {
		'-nets': pwr_net,
		'-internal': None,
		'-voltage': nom_voltage
	}
	cpf_tcl.write_cmd_w_opts('create_power_nets', pwr_nets_opts)
	gnd_net = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
	gnd_nets_opts = {
		'-nets': gnd_net,
	}
	cpf_tcl.write_cmd_w_opts('create_ground_nets', gnd_nets_opts)
	cpf_tcl.write('')

	pd_opts = {
		'-name': '_'.join(['PD', pwr_net]),
		'-default': None
	}
	cpf_tcl.write_cmd_w_opts('create_power_domain', pd_opts)
	pd_opts = {
		'-name': '_'.join(['PD', pwr_net]),
		'-primary_power_net': pwr_net,
		'-primary_ground_net': gnd_net,
	}
	cpf_tcl.write_cmd_w_opts('update_power_domain', pd_opts)
	cpf_tcl.write('')

	on_nom_cond = {
		'-name': 'ON',
		'-voltage': nom_voltage,
		'-ground_voltage': 0,
		'-state': 'on'
	}
	cpf_tcl.write_cmd_w_opts('create_nominal_condition', on_nom_cond)
	off_nom_cond = {
		'-name': 'OFF',
		'-voltage': 0,
		'-ground_voltage': 0,
		'-state': 'off'
	}
	cpf_tcl.write_cmd_w_opts('create_nominal_condition', off_nom_cond)
	cpf_tcl.write('')

	pm_opts = {
		'-name': '_'.join(['PM', 'on']),
		'-domain_conditions': '_'.join(['PD', pwr_net]) + '@ON',
		'-default': None
	}
	cpf_tcl.write_cmd_w_opts('create_power_mode', pm_opts)
	pm_opts = {
		'-name': '_'.join(['PM', 'off']),
		'-domain_conditions': '_'.join(['PD', pwr_net]) + '@OFF',
	}
	cpf_tcl.write_cmd_w_opts('create_power_mode', pm_opts)
	cpf_tcl.write('')

	cpf_tcl.write('end_design')
	cpf_tcl.close()

	return ret


def write_options(filename:str, num_route_layer_override: int = None, lefdef2qrc_layermap_override: str = None) -> int:
	'''
	write a file for basic options used in innovus

	:param filename: path to options file
	:param num_route_layer_override: override number of routing layer used for the design
	:param lefdef2qrc_layermap_override: override LEF/DEF to QRC layer mapping file
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	logger = flow_log_utils.start_logging()
	options_tcl = flow_tcl_utils.TclFile(filename=filename)
	disthost_opts = {
		'-local': None
	}
	options_tcl.write_cmd_w_opts('setDistributeHost', disthost_opts)
	multicpuusage_opts = {
		'-localCpu': 8,
		'-remoteHost': 0,
	}
	options_tcl.write_cmd_w_opts('setMultiCpuUsage', multicpuusage_opts)
	licensecheck_opts = {
		'-wait': 10000,
	}
	options_tcl.write_cmd_w_opts('setLicenseCheck', licensecheck_opts)
	design_mode_opts = {
		'-flowEffort': 'standard',
	}
	process = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'PROCESS')
	if process is not None:
		design_mode_opts['-process'] = process
	else:
		logger.warning('FLOW_CFGS[TECH_CFG:PDK:PROCESS] not defined. it will lower the accuracy')
	options_tcl.write_cmd_w_opts('setDesignMode', design_mode_opts)
	place_mode_opts = {}
	place_mode_opts['-wireLenOptEffort'] = 'high'
	place_mode_opts['-placeIoPins'] = 'true'
	if len(place_mode_opts) > 0:
		options_tcl.write_cmd_w_opts('setPlaceMode', place_mode_opts)

	if num_route_layer_override is not None:
		max_route_layer = num_route_layer_override
	elif pdflow.is_3D_design():
		max_route_layer = max(FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'])
	else:
		max_route_layer = get_dict(FLOW_VARS, 'PNR_NUM_ROUTE_LAYER')
	if max_route_layer is not None:
		options_tcl.write('setMaxRouteLayer %d' % (max_route_layer))

	route_mode_opts = {}
	bottom_routing_layer = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'ROUTE', 'BOTTOM_ROUTING_LAYER')
	if bottom_routing_layer is not None and FLOW_ENVS['TOOL_MAJOR_VERSION'] >= 17:
		route_mode_opts['-earlyGlobalMinRouteLayer'] = bottom_routing_layer
	if len(route_mode_opts) > 0:
		options_tcl.write_cmd_w_opts('setRouteMode', route_mode_opts)

	nanoroute_mode_opts = {}
	if bottom_routing_layer is not None:
		nanoroute_mode_opts['-routeBottomRoutingLayer'] = bottom_routing_layer
	else:
		logger.warning('FLOW_CFGS[TECH_CFG:PNR:ROUTE:BOTTOM_ROUTING_LAYER] not defined. assuming 1')
		nanoroute_mode_opts['-routeBottomRoutingLayer'] = 1
	num_droute_itr = get_dict(FLOW_VARS, 'PNR_ROUTE_NUM_ITERATION')
	if num_droute_itr is not None:
		nanoroute_mode_opts['-drouteEndIteration'] = num_droute_itr
	if len(nanoroute_mode_opts) > 0:
		options_tcl.write_cmd_w_opts('setNanoRouteMode', nanoroute_mode_opts)

	# make same environment between innovus and tempus
	if FLOW_ENVS['TOOL_MAJOR_VERSION'] >= 17:
		delaycal_mode_opts = {
			'-equivalent_waveform_model': 'none',
			'-SIAware': 'false',
		}
	else:
		delaycal_mode_opts = {
			'-equivalent_waveform_model_propagation': 'false',
			'-equivalent_waveform_model_type': 'none',
			'-SIAware': 'false',
		}
	if len(delaycal_mode_opts) > 0:
		options_tcl.write_cmd_w_opts('setDelayCalMode', delaycal_mode_opts)

	extractrc_mode_opts = {}
	if lefdef2qrc_layermap_override is not None:
		lef_techfile_layermap = os.path.abspath(lefdef2qrc_layermap_override)
	else:
		lef_techfile_layermap = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'LEFDEF2QRC_LAYERMAP')
	if lef_techfile_layermap is not None:
		extractrc_mode_opts['-lefTechFileMap'] = lef_techfile_layermap
	if len(extractrc_mode_opts) > 0:
		options_tcl.write_cmd_w_opts('setExtractRCMode', extractrc_mode_opts)

	# leakageToDynamicRatio
	# 0.0: optimize dynamic power
	# 1.0: optimize leakage power
	opt_mode_opts = {
		'-powerEffort': 'high',
		'-leakageToDynamicRatio': 0,
	}
	if is_on(FLOW_VARS, 'PNR_PRESERVE_HIER_PORTS'):
		opt_mode_opts['-preserveModuleFunction'] = 'true'
	if len(opt_mode_opts) > 0:
		options_tcl.write_cmd_w_opts('setOptMode', opt_mode_opts)

	innovus_tcl = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'INNOVUS', 'TCL')
	if innovus_tcl is not None:
		logger.warning('FLOW_CFG[TECH_CFG:PNR:INNOVUS:TCL] is specified, but will not be used as it might cause license problems')
		'''
		options_tcl.write('# source %s' % (os.path.join(FLOW_ENVS['WORK_AREA'], 'library', innovus_tcl)))
		pnr_input_collaterals.append(innovus_tcl)
		'''

	options_tcl.close()

	return ret


def write_interactive(filename: str, interactive_design: str = None) -> int:
	'''
	write a script for innovus interactive session

	:param filename: path to interactive session script
	:param interactive_design: name of the design for interactive session
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	global pnr_sessions

	ret = 0
	interactive_tcl = flow_tcl_utils.TclFile(filename=filename)

	if interactive_design is None:
		interactive_dir = get_session_dir(FLOW_ENVS['STAGE'])
	else:
		interactive_dir = get_session_dir(FLOW_ENVS['STAGE'], interactive_design)
	pnr_sessions.append(interactive_dir)
	if interactive_design is None:
		interactive_design = FLOW_ENVS['BLOCK']

	interactive_tcl.write_section_comment('load design')
	interactive_tcl.write('if {[is_common_ui_mode]} {')
	interactive_tcl.write('read_db %s' % (interactive_dir))
	interactive_tcl.write('} else {')
	interactive_tcl.write('restoreDesign %s %s' % (interactive_dir, interactive_design))
	interactive_tcl.write('}')
	interactive_tcl.write('')

	# load flow envs/cfgs/vars
	interactive_tcl.write_section_comment('load flow envs/cfgs/vars')
	interactive_tcl.write('package require json')
	flow_envs_json_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('flow_envs', 'json'))
	interactive_tcl.write('set fp [open "%s" r]' % (flow_envs_json_file))
	pnr_sessions.append(flow_envs_json_file)
	interactive_tcl.write('set flow_envs_data [read $fp]')
	interactive_tcl.write('close $fp')
	interactive_tcl.write('set FLOW_ENVS [::json::json2dict $flow_envs_data]')

	flow_cfgs_json_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('flow_cfgs', 'json'))
	interactive_tcl.write('set fp [open "%s" r]' % (flow_cfgs_json_file))
	pnr_sessions.append(flow_cfgs_json_file)
	interactive_tcl.write('set flow_cfgs_data [read $fp]')
	interactive_tcl.write('close $fp')
	interactive_tcl.write('set FLOW_CFGS [::json::json2dict $flow_cfgs_data]')

	flow_vars_json_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('flow_vars', 'json'))
	interactive_tcl.write('set fp [open "%s" r]' % (flow_vars_json_file))
	pnr_sessions.append(flow_vars_json_file)
	interactive_tcl.write('set flow_vars_data [read $fp]')
	interactive_tcl.write('close $fp')
	interactive_tcl.write('set FLOW_VARS [::json::json2dict $flow_vars_data]')
	interactive_tcl.write('')

	# set marker variables
	interactive_tcl.write('set is_rc_extracted 0')

	interactive_tcl.close()

	return ret


def run_pnr(stage: str, tool: str, tool_version: str, clean_prevrun: bool, run: str, interactive_design: str, log_tracer: flow_log_utils.CustomStreamHandler) -> int:
	'''
	perform pnr of designs

	:param stage: pnr stage to perform. it will perform all the stages prior to the specified stage if required. if not specified, it will perform all the stages.
	:param tool: tool to use for pnr
	:param tool_version: tool version to use for pnr. e.g.: 19.11
	:param clean_prevrun: delete existing run
	:param run: phase to run the flow
	:param interactive_design: choose design to open in interactive run (if not given, it will open the main design)
	:param log_tracer: logging.CustomStreamHandler to manage warning/errors
	:return: 0 if pnr is completed successfully. Otherwise, 1
	'''
	# update tool version if needed
	if tool_version is not None:
		ret = flow_module_utils.update_tool_version(tool, tool_version)
		if ret == 1:
			return 1
	else:
		tool_version = flow_module_utils.get_cur_version(tool)

	ret = 0

	# load libdb
	global lib_db
	lib_db = libdb.LibDb()
	# read FLOW_CFGS, FLOW_VARS
	# read them first, so that the flow can identify how many times it needs to run
	pdflow.read_pdflow_configs(flow='pnr', tool=tool)
	pdflow.read_pdflow_vars_specs(flow='pnr')
	pdflow.read_pdflow_vars_setups(flow='pnr')

	# identify how many times it needs to run
	if stage is None:
		if pdflow.is_3D_design():
			stage = pdflow.supported_pnr_3d_stages[-1]
		else:
			stage = pdflow.supported_pnr_2d_stages[-1]
	if run == 'main':
		target_stages = get_target_stages(stage)
	else:
		target_stages = [stage]

	for cur_stage in target_stages:
		# RUN START
		# setup logging and print command arguments
		logger, log_file = pdflow.setup_command_log('pnr', stage=cur_stage, corner=None, extra_file_ext=run)
		log_tracer.reset()
		flow_log_utils.write_section_comment(logger, 'pdflow pnr flow - stage %s' % (cur_stage))
		args = {
			'stage': cur_stage,
			'tool': tool,
			'tool_version': tool_version,
			'clean_prevrun': clean_prevrun,
			'run': run,
			'interactive_design': interactive_design,
		}
		flow_args_utils.print_args(args, logger=logger)

		# setup flow envs (it can depend on other FLOW_ENVS or other FLOW_CFGS)
		pdflow.setup_command_flow_env('pnr', stage=cur_stage, tool=tool, tool_version=tool_version, logger=logger)
		# setup additional flow envs
		if tool.upper() == 'INNOVUS':
			FLOW_ENVS['TOOL_MAJOR_VERSION'] = int(tool_version.split('.')[0])

		# read flow cfgs (it does not do anything, but just read once more)
		flow_log_utils.write_subsection_comment(logger, 'read flow configs')
		pdflow.read_pdflow_configs(flow=FLOW_ENVS['FLOW'], tool=FLOW_ENVS['TOOL'])

		# read flow vars (it can depend on FLOW_ENVS, FLOW_CFGS, or other FLOW_VARS)
		flow_log_utils.write_subsection_comment(logger, 'read flow vars')
		pdflow.read_pdflow_vars_specs(flow=FLOW_ENVS['FLOW'])
		pdflow.read_pdflow_vars_setups(flow=FLOW_ENVS['FLOW'])

		# setup directories
		pdflow.setup_command_dir(clean_prevrun=clean_prevrun, logger=logger)

		# setup script/log filenames
		if cur_stage == 'init' or cur_stage == 'floorplan' or cur_stage == 'place' or cur_stage == 'cts' or cur_stage == 'postcts_opt' or cur_stage == 'route' or cur_stage == 'postroute_opt' or cur_stage == 'finish':
			main_tcl_files = [os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'tcl'))]
		elif cur_stage == '3d_route' or cur_stage == '3d_merge':
			main_tcl_files = [os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'tcl'))]
		elif cur_stage == '3d_partition' or cur_stage == '3d_legalize' or cur_stage == '3d_split' or cur_stage == '3d_trial' or cur_stage == '3d_opt' or cur_stage == '3d_finish':
			main_tcl_files = [
				os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('part0', 'tcl')),
				os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('part1', 'tcl'))
			]
		else:
			main_tcl_files = []

		global pnr_input_collaterals
		global pnr_reports
		global pnr_sessions
		pnr_input_collaterals = []
		#TODO: need to fill out reports needed in postproc
		pnr_reports = []
		pnr_sessions = []

		if run != 'interactive':
			# script generation ------> tool run -------> post-processing -------> end
			# |-------------------------|-----------------|------------------------|
			# |- main ------------------------------------------------------------>
			# |- setup ---------------->
			#                           - run ------------------------------------>
			#                                             - postproc ------------->
			if run == 'setup' or run == 'main':
				# SETUP: SCRIPT GENERATION
				flow_log_utils.write_subsection_comment(logger, 'generate scripts')

				cd(FLOW_ENVS['RUN_DIR'])

				# for 3d stages, copy all the result files from previous stage
				prev_stage = get_prev_stage(FLOW_ENVS['STAGE'])
				if prev_stage is not None and not re.match('3d_.*', FLOW_ENVS['STAGE']):
					for path in glob.glob(os.path.join(get_prev_result_dir(FLOW_ENVS['STAGE']), '*')):
						flow_file_utils.copy_path(path, FLOW_ENVS['RESULT_DIR'])

				# dump FLOW_ENVS, FLOW_CFGS, FLOW_VARS
				pdflow.dump_flow_envs_cfgs_vars(FLOW_ENVS['SCRIPT_DIR'])

				# generate scripts
				if cur_stage == 'init':
					import pdflow_pnr_init

					ret |= pdflow_pnr_init.main(main_tcl_files[0])
				elif cur_stage == 'floorplan':
					import pdflow_pnr_floorplan

					ret |= pdflow_pnr_floorplan.main(main_tcl_files[0])
				elif cur_stage == 'place':
					import pdflow_pnr_place

					ret |= pdflow_pnr_place.main(main_tcl_files[0])
				elif cur_stage == 'cts':
					import pdflow_pnr_cts

					ret |= pdflow_pnr_cts.main(main_tcl_files[0])
				elif cur_stage == 'postcts_opt':
					import pdflow_pnr_postcts_opt

					ret |= pdflow_pnr_postcts_opt.main(main_tcl_files[0])
				elif cur_stage == 'route':
					import pdflow_pnr_route

					ret |= pdflow_pnr_route.main(main_tcl_files[0])
				elif cur_stage == 'postroute_opt':
					import pdflow_pnr_postroute_opt

					ret |= pdflow_pnr_postroute_opt.main(main_tcl_files[0])
				elif cur_stage == 'finish':
					import pdflow_pnr_finish

					ret |= pdflow_pnr_finish.main(main_tcl_files[0])
				elif cur_stage == '3d_partition':
					import pdflow_pnr_3d_partition

					ret |= pdflow_pnr_3d_partition.main(main_tcl_files)
				elif cur_stage == '3d_legalize':
					import pdflow_pnr_3d_legalize

					ret |= pdflow_pnr_3d_legalize.main(main_tcl_files)
				elif cur_stage == '3d_route':
					import pdflow_pnr_3d_route

					ret |= pdflow_pnr_3d_route.main(main_tcl_files[0])
				elif cur_stage == '3d_split':
					import pdflow_pnr_3d_split

					ret |= pdflow_pnr_3d_split.main(main_tcl_files)
				elif cur_stage == '3d_trial':
					import pdflow_pnr_3d_trial

					ret |= pdflow_pnr_3d_trial.main(main_tcl_files)
				elif cur_stage == '3d_opt':
					import pdflow_pnr_3d_opt

					ret |= pdflow_pnr_3d_opt.main(main_tcl_files, log_tracer)
				elif cur_stage == '3d_finish':
					import pdflow_pnr_3d_finish

					ret |= pdflow_pnr_3d_finish.main(main_tcl_files)
				elif cur_stage == '3d_merge':
					import pdflow_pnr_3d_merge

					ret |= pdflow_pnr_3d_merge.main(main_tcl_files[0])

				# check errors and print summary
				# if there are errors, stop here,
				# if there is no error, store list of required files to run the tool
				if pdflow.has_errors(log_tracer=log_tracer, status=ret):
					logger.error('error detected while generating scripts. stop running. resolve the errors to proceed.')

					cd(FLOW_ENVS['WORK_AREA'])
					flow_log_utils.print_summary(logger, log_tracer)
					flow_log_utils.stop_logging(logger, log_file)
					return ret
				else:
					input_collateral_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('input_collaterals', 'txt'))
					pdflow.write_file_list(input_collateral_file, pnr_input_collaterals)

					cd(FLOW_ENVS['WORK_AREA'])

			if run == 'run' or run == 'main':
				# RUN: TOOL RUN
				flow_log_utils.write_subsection_comment(logger, 'run scripts')

				cd(FLOW_ENVS['RUN_DIR'])

				# check the list of required files to run the tool
				flow_log_utils.write_subsubsection_comment(logger, 'check input collaterals')
				input_collateral_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename('input_collaterals', 'txt'))
				pnr_input_collaterals = pdflow.read_file_list(input_collateral_file)
				ret |= pdflow.check_file_list(pnr_input_collaterals, logger)

				# check errors and print summary
				# if there are errors, stop here.
				if pdflow.has_errors(log_tracer=log_tracer, status=ret):
					logger.error('missing files exist. resolve the errors to proceed.')

					cd(FLOW_ENVS['WORK_AREA'])
					flow_log_utils.print_summary(logger, log_tracer)
					flow_log_utils.stop_logging(logger, log_file)
					return ret
				pnr_input_collaterals = []

				# for each main_tcl_file, run the tool
				for main_tcl_file in main_tcl_files:
					if tool.upper() == 'INNOVUS':
						# to avoid **ERROR: (IMPOAX-124):    OpenAccess (OA) shared library installation is older than the one that was used to build this Innovus version. For using the OA installation built and tested with this Innovus version, unset the shell variable OA_HOME. For using 'p020' or higher version of OA, reset OA_HOME to point to that installation.
						if 'OA_HOME' in os.environ:
							del os.environ['OA_HOME']

						# set options for the tool
						lic_waittime = os.getenv('CDS_MAX_WAITTIME')
						if lic_waittime is None:
							lic_waittime = '10000'
						innovus_opts = '-wait %s -no_gui -batch -file %s -overwrite' % (lic_waittime, main_tcl_file)
						# invsb (Innovus Basic license) cannot handle ccopt_design with 28nm and below. wait for invs (Innovus license) for 28nm and below.
						if (cur_stage=='cts' or cur_stage=='route' or cur_stage=='postroute_opt' or cur_stage=='3d_route' or cur_stage=='3d_opt') and int(get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', 'PROCESS')) < 30:
							innovus_opts += ' -lic_startup invs'

						# run the tool
						innovus_ret = flow_run_utils.run('innovus %s' % (innovus_opts), run_lvls=['%s(%s)' % (FLOW_ENVS['TOOL'].upper(), FLOW_ENVS['STAGE'].upper())])

						# we use "exit 1" for normal exits (see innovus_end_commands)
						if innovus_ret == 1:
							# normally in linux, exit code 0: normal exit, other: fail
							ret |= 0
						else:
							ret |= 1

						tool_log_file = os.path.join(FLOW_ENVS['RUN_DIR'], flow_file_utils.join_filename('innovus', 'latest', 'log'))
					else:
						# FOR OTHER TOOLS
						tool_log_file = None

					# filter logs
					log_filter = get_dict(FLOW_CFGS, FLOW_ENVS['TOOL'].upper(), 'LOG_FILTER')
					if log_filter is not None and os.path.exists(tool_log_file):
						flow_log_utils.write_subsection_comment(logger, 'run summary')
						flow_log_utils.filter_log(tool_log_file, log_filter)
						flow_log_utils.print_filtered_log(logger, FLOW_ENVS['TOOL'], tool_log_file)

					# check errors and print summary
					# if there are errors, stop here.
					if pdflow.has_errors(log_tracer=log_tracer, status=ret):
						logger.error('error detected while running the tool. stop running. resolve the errors to proceed.')

						cd(FLOW_ENVS['WORK_AREA'])
						flow_log_utils.print_summary(logger, log_tracer)
						flow_log_utils.stop_logging(logger, log_file)
						return ret

				cd(FLOW_ENVS['WORK_AREA'])

			if run == 'run' or run == 'postproc' or run == 'main':
				# POSTPROC: POST PROCESSING
				flow_log_utils.write_subsection_comment(logger, 'run post-processing')

				cd(FLOW_ENVS['RUN_DIR'])

				# check the list of required reports to run post-processing
				flow_log_utils.write_subsubsection_comment(logger, 'check reports')
				ret = pdflow.check_file_list(pnr_reports, logger)
				if ret != 0:
					logger.error('error detected. stop running. resolve the errors to proceed.')

					cd(FLOW_ENVS['WORK_AREA'])
					flow_log_utils.print_summary(logger, log_tracer)
					flow_log_utils.stop_logging(logger, log_file)
					return ret
				pnr_reports = []

				# TODO: implement postproc here

				if pdflow.has_errors(log_tracer=log_tracer, status=ret):
					logger.error('error detected while post-processing. stop running. resolve the errors to proceed.')

					cd(FLOW_ENVS['WORK_AREA'])
					flow_log_utils.print_summary(logger, log_tracer)
					flow_log_utils.stop_logging(logger, log_file)
					return ret

				cd(FLOW_ENVS['WORK_AREA'])

			if run != 'setup':
				flow_file_utils.open_wfile(os.path.join(FLOW_ENVS['WORK_AREA'], FLOW_ENVS['FLOW'], FLOW_ENVS['STAGE'], flow_file_utils.join_filename(FLOW_ENVS['STAGE'], 'done')), force=True).close()

		else:
			# INTERACTIVE: INTERACTIVE SESSION
			flow_log_utils.write_subsection_comment(logger, 'run interative')

			interactive_name = pdflow.setup_command_interactive_dir()
			cd(FLOW_ENVS['INTERACTIVE_DIR'])

			if tool.upper() == 'INNOVUS':
				interactive_file = os.path.join(FLOW_ENVS['INTERACTIVE_DIR'], flow_file_utils.join_filename(interactive_name, 'tcl'))
				write_interactive(interactive_file, interactive_design)

				# set options for the tool
				lic_waittime = os.getenv('CDS_MAX_WAITTIME')
				if lic_waittime is None:
					lic_waittime = '480'

				# check the list of required files (sessions) to open an interactive session
				flow_log_utils.write_subsubsection_comment(logger, 'check input collaterals')
				ret |= pdflow.check_file_list(pnr_sessions, logger)
				# check errors and print summary
				# if there are errors, stop here.
				if ret != 0:
					logger.error('error detected. stop running. resolve the errors to proceed.')

					cd(FLOW_ENVS['WORK_AREA'])
					flow_log_utils.print_summary(logger, log_tracer)
					flow_log_utils.stop_logging(logger, log_file)
					return ret
				pnr_sessions = []

				# open interactive session
				flow_run_utils.interactive_run('innovus -wait %s -init %s -log %s' % (lic_waittime, interactive_file, interactive_name))
			else:
				# FOR OTHER TOOLS
				pass

			cd(FLOW_ENVS['WORK_AREA'])

		flow_log_utils.print_summary(logger, log_tracer)
		flow_log_utils.stop_logging(logger, log_file)

	return ret

