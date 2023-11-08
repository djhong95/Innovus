#!/usr/bin/env python3
import pdflow
import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_file_utils
import flow_log_utils
import flow_run_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_pt_load_library(filename: str) -> int:
	'''
	generate script for loading library

	:param filename: filename of the loading library script
	:return: 0 if script generation ended successfully. otherwise, 1
	'''
	ret = 0
	load_library_tcl = flow_tcl_utils.TclFile(filename=filename)

	# set db files according to tech config
	load_library_tcl.write_section_comment('load library')
	cell_corner = get_dict(FLOW_CFGS, 'TECH_CFG', 'SYN', 'CORNER')
	if cell_corner is None:
		logger.error('FLOW_CFGS[TECH_CFG:SYN:CORNER] not defined. link and target library cannot be defined')
		target_libraries = []
		ret = 1
	else:
		cell_pvt = get_dict(FLOW_CFGS, 'TECH_CFG', 'CORNERS', cell_corner, 'PVT')
		target_cell_libraries = pdflow_pnr.lib_db.query(class_name='cell', view_list=['db'], corner_list=cell_pvt)
		if pdflow.has_memory():
			target_memory_libraries = pdflow_pnr.lib_db.query(class_name='memory', cell_list=FLOW_VARS['MEMORY_CELLS'], view_list=['db'], corner_list=cell_pvt)
		else:
			target_memory_libraries = []
		target_libraries = target_cell_libraries + target_memory_libraries
	pdflow_pnr.pnr_input_collaterals += target_libraries

	link_library = ['*'] + target_libraries
	load_library_tcl.write('set link_library %s' % (flow_tcl_utils.get_list(link_library)))

	load_library_tcl.close()

	return ret


def write_pt_load_design(filename: str) -> int:
	'''
	generate script for loading design

	:param filename: filename of the loading design script
	:return: 0 if script generation ended successfully. otherwise, 1
	'''
	ret = 0
	load_design_tcl = flow_tcl_utils.TclFile(filename=filename)

	syn_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'syn', 'results')
	pnr_3d_trial_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', pdflow_pnr.get_prev_stage(FLOW_ENVS['STAGE']), 'results')
	pnr_3d_split_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', '3d_split', 'results')

	top_verilog_file = os.path.join(pnr_3d_split_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v'))
	part0_verilog_file = os.path.join(pnr_3d_split_result_dir, flow_file_utils.join_filename('part0', 'v'))
	part1_verilog_file = os.path.join(pnr_3d_split_result_dir, flow_file_utils.join_filename('part1', 'v'))
	top_sdc_file = os.path.join(syn_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdc'))
	load_design_tcl.write('read_verilog %s' % (top_verilog_file))
	load_design_tcl.write('read_verilog %s' % (part0_verilog_file))
	load_design_tcl.write('read_verilog %s' % (part1_verilog_file))
	pdflow_pnr.pnr_input_collaterals.append(top_verilog_file)
	pdflow_pnr.pnr_input_collaterals.append(part0_verilog_file)
	pdflow_pnr.pnr_input_collaterals.append(part1_verilog_file)
	load_design_tcl.write('current_design %s' % (FLOW_ENVS['BLOCK']))
	load_design_tcl.write('link_design')
	load_design_tcl.write('source %s' % (top_sdc_file))
	pdflow_pnr.pnr_input_collaterals.append(top_sdc_file)

	setup_corner = get_dict(FLOW_CFGS, 'TECH_CFG', 'CORNERS', get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'CORNERS', 'SETUP')[0])['RC']
	top_spef_file = os.path.join(pnr_3d_split_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'spef'))
	part0_spef_file = os.path.join(pnr_3d_trial_result_dir, flow_file_utils.join_filename('part0', 'rc_'+setup_corner, 'spef', 'gz'))
	part1_spef_file = os.path.join(pnr_3d_trial_result_dir, flow_file_utils.join_filename('part1', 'rc_'+setup_corner, 'spef', 'gz'))
	read_parasitic_opts = {
		'-format': 'spef',
		'-increment': None,
		'-path': 'U_part0',
		part0_spef_file: None,
	}
	load_design_tcl.write_cmd_w_opts('read_parasitics', read_parasitic_opts)
	pdflow_pnr.pnr_input_collaterals.append(part0_spef_file)
	read_parasitic_opts = {
		'-format': 'spef',
		'-increment': None,
		'-path': 'U_part1',
		part1_spef_file: None,
	}
	load_design_tcl.write_cmd_w_opts('read_parasitics', read_parasitic_opts)
	pdflow_pnr.pnr_input_collaterals.append(part1_spef_file)
	read_parasitic_opts = {
		'-format': 'spef',
		'-increment': None,
		top_spef_file: None,
	}
	load_design_tcl.write_cmd_w_opts('read_parasitics', read_parasitic_opts)
	pdflow_pnr.pnr_input_collaterals.append(top_spef_file)

	load_design_tcl.close()

	return ret


def write_pt_tcl(filename: str, load_library_file: str, load_design_file: str, tool_log_file: str) -> int:
	'''
	generate tcl file for pt to generate sdc file for tier designs

	:param filename: name of the main tcl file
	:param load_library_file: filename of loading library file
	:param load_design_file: filename of loading design file
	:param tool_log_file: filename of the tool log file (we can set)
	:return: 0 if script generation ended successfully. otherwise, 1
	'''
	ret = 0
	pt_context_tcl = flow_tcl_utils.TclFile(filename=filename)

	# set resource monitor
	pt_context_tcl.write_section_comment('flow tcl package')
	pt_context_tcl.write('package forget flow_utils; package require flow_utils')
	pt_context_tcl.write('namespace import flow_utils::*')
	pt_context_tcl.write('')
	start_resmon_opts = {
		'-tool': FLOW_ENVS['TOOL'],
	}
	resmon_chkpts = get_dict(FLOW_CFGS, FLOW_ENVS['TOOL'].upper(), 'RESMON_CHKPTS', FLOW_ENVS['FLOW'].upper())
	if resmon_chkpts is not None:
		chkpts_file = os.path.join(FLOW_ENVS['RUN_DIR'], flow_file_utils.join_filename('resmon', 'chkpts'))
		ofp = flow_file_utils.open_wfile(chkpts_file, force=True)
		for chkpt_name, chkpt_pattern in resmon_chkpts.items():
			ofp.write('%s %s\n' % (chkpt_name, chkpt_pattern))
		ofp.close()
		start_resmon_opts['-chkpts_file'] = chkpts_file
		start_resmon_opts['-tool_log_file'] = tool_log_file
	pt_context_tcl.write_cmd_w_opts('flow_utils::start_resmon', start_resmon_opts)

	# tool settings
	pt_context_tcl.write_section_comment('set host options')
	pt_context_tcl.write('set_host_options -max_core 8 -local')

	# tool settings
	pt_context_tcl.write_section_comment('global tool setting')
	suppress_warnings = get_dict(FLOW_CFGS, FLOW_ENVS['TOOL'].upper(), 'SUPPRESS_WARN')
	if suppress_warnings is not None:
		for suppress_warning in suppress_warnings:
			pt_context_tcl.write('suppress_message %s' % (suppress_warning))
	set_vars = get_dict(FLOW_CFGS, FLOW_ENVS['TOOL'].upper(), 'SET_VAR')
	if set_vars is not None:
		for set_var, value in set_vars.items():
			pt_context_tcl.write('set %s %s' % (set_var, value))
	set_app_vars = get_dict(FLOW_CFGS, FLOW_ENVS['TOOL'].upper(), 'SET_APP_VAR')
	if set_app_vars is not None:
		for set_app_var, value in set_app_vars.items():
			pt_context_tcl.write('set_app_var %s %s' % (set_app_var, value))
	# set_program_options - enable_high_capacity

	# user settings (flow vars)
	pt_context_tcl.write_section_comment('user tool setting')
	'''
	FLOW_VARS[]
	'''

	# intialize
	pt_context_tcl.write_section_comment('initial setup')

	# library/design load
	pt_context_tcl.write_section_comment('load library/design data')
	pt_context_tcl.write('source -echo -verbose %s' % (load_library_file))
	pt_context_tcl.write('source -echo -verbose %s' % (load_design_file))
	pdflow_pnr.pnr_input_collaterals.append(load_library_file)
	pdflow_pnr.pnr_input_collaterals.append(load_design_file)

	# group settings
	pt_context_tcl.write_section_comment('default path groups setup')
	pt_context_tcl.write('group_path -name io_to_flop -from [all_inputs]')
	pt_context_tcl.write('group_path -name flop_to_io -to [all_outputs]')
	pt_context_tcl.write('group_path -name io_to_io -from [all_inputs] -to [all_outputs]')

	# propagate clocks
	pt_context_tcl.write_section_comment('propagate clock')
	pt_context_tcl.write('foreach_in_collection clk [all_clocks] {')
	pt_context_tcl.write('set clk_name [ get_object_name $clk ]')
	pt_context_tcl.write('set clk_src [ get_attribute -quiet $clk sources ]')
	pt_context_tcl.write('if { $clk_src ne "" && [ get_attribute $clk_src object_class ] == "port" } {')
	pt_context_tcl.write('p_info "source of clock $clk_name is a port. clock source port of $clk_name will be propagated"')
	pt_context_tcl.write('set_propagated_clock [get_ports [get_object_name $clk_src]]')
	pt_context_tcl.write('p_info "source of clock $clk_name is a port. but clock $clk_name will be propagated"')
	pt_context_tcl.write('set_propagated_clock $clk')
	pt_context_tcl.write('} elseif { $clk_src ne "" } {')
	pt_context_tcl.write('p_info "source of clock $clk_name is not a port. clock $clk_name will be propagated"')
	pt_context_tcl.write('set_propagated_clock $clk')
	pt_context_tcl.write('} else {')
	pt_context_tcl.write('p_info "source of clock $clk_name is not real. clock $clk_name will not be propagated"')
	pt_context_tcl.write('}')
	pt_context_tcl.write('}')

	# update timing
	pt_context_tcl.write_section_comment('update timing')
	pt_context_tcl.write('update_timing -full')
	pt_context_tcl.write('')

	# write sdc for tier designs
	pt_context_tcl.write('characterize_context [get_cells *]')
	pt_context_tcl.write('for {set i 0} {$i < 2} {incr i} {')
	pt_context_tcl.write('write_context -format sdc -nosplit -out %s/part${i}.sdc [get_cells U_part${i}]' % (os.path.join(FLOW_ENVS['RESULT_DIR'])))
	pt_context_tcl.write('}')
	pt_context_tcl.write('')

	pt_context_tcl.write_section_comment('save session')
	pt_context_tcl.write('eval save_session %s' % (os.path.join(FLOW_ENVS['SESSION_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'session'))))

	pt_context_tcl.write('flow_utils::end_resmon')
	pt_context_tcl.write('exit')
	pt_context_tcl.close()

	return ret


def write_shrunk2d_tcl(filename: str, design_name: str, mmmc_file: str, cpf_file: Union[str, None], upf_file: Union[str, None], options_file: str) -> int:
	'''
	generate main tcl file for shrunk2d designs

	:param filename: name of the main tcl file
	:param design_name: name of the tier design
	:param mmmc_file: filename of mmmc file
	:param cpf_file: filename of cpf file
	:param upf_file: filename of upf file
	:param options_file: filename of options file
	:return: 0 if script generation ended successfully. otherwise, 1
	'''
	ret = 0
	pnr_3d_opt_tcl = flow_tcl_utils.TclFile(filename=filename)

	# **ERROR: (TCLCMD-290):    Could not find technology library 'sc12mc_cln28hpm_base_hvt_c35_ss_typical_max_0p81v_125c' (File /home/kchang/test_pe/test/aes_128/aes_128/CLN28HPM/r4p0/impl/wa_3d/pnr/3d_opt/results/part0.sdc, Line 247942) 
	pnr_3d_opt_tcl.write('set_message -id TCLCMD-290 -suppress')
	# **ERROR: (TCLCMD-1040):   -library option of set_wire_load_model accepts only a timing library. (File /home/kchang/test_pe/test/aes_128/aes_128/NANGATE45/2020_10/impl/wa_3d/pnr/3d_opt/results/part0.sdc, Line 357566)
	pnr_3d_opt_tcl.write('set_message -id TCLCMD-1040 -suppress')
	pnr_3d_opt_tcl.write('')

	pdflow_pnr.innovus_start_commands(pnr_3d_opt_tcl, restore_design=False)

	design_mode_opts = {
		'-pessimisticMode': 'true',
	}
	pnr_3d_opt_tcl.write_cmd_w_opts('setDesignMode', design_mode_opts)
	pnr_3d_split_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', '3d_split', 'results')
	netlist_file = os.path.join(pnr_3d_split_result_dir, flow_file_utils.join_filename(design_name, 'v'))
	pnr_3d_opt_tcl.write('set init_verilog %s' % (netlist_file))
	pdflow_pnr.pnr_input_collaterals.append(netlist_file)

	lef_files = pdflow_pnr.get_lef_files()
	pnr_3d_opt_tcl.write('set init_lef_file %s' % (flow_tcl_utils.get_list(lef_files)))
	pdflow_pnr.pnr_input_collaterals += lef_files

	pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
	gnd_net = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
	pnr_3d_opt_tcl.write('set init_pwr_net %s' % (pwr_net))
	pnr_3d_opt_tcl.write('set init_gnd_net %s' % (gnd_net))
	pnr_3d_opt_tcl.write('set init_top_cell %s' % (design_name))
	pnr_3d_opt_tcl.write('set init_mmmc_file %s' % (mmmc_file))
	pdflow_pnr.pnr_input_collaterals.append(mmmc_file)
	pnr_3d_opt_tcl.write('init_design')
	pnr_3d_opt_tcl.write('')
	if upf_file is not None:
		pnr_3d_opt_tcl.write('read_power_intent -1801 %s' % (upf_file))
		pdflow_pnr.pnr_input_collaterals.append(upf_file)
	elif cpf_file is not None:
		pnr_3d_opt_tcl.write('read_power_intent -cpf %s' % (cpf_file))
		pdflow_pnr.pnr_input_collaterals.append(cpf_file)
	else:
		logger.warning('power intent file does not exist.')
	pnr_3d_opt_tcl.write('commit_power_intent')
	pnr_3d_opt_tcl.write('')
	pnr_3d_opt_tcl.write('source %s' % (options_file))
	pdflow_pnr.pnr_input_collaterals.append(options_file)

	input_def_file = os.path.join(pnr_3d_split_result_dir, flow_file_utils.join_filename(design_name, 'def'))
	pnr_3d_opt_tcl.write('defIn %s' % (input_def_file))
	pdflow_pnr.pnr_input_collaterals.append(input_def_file)

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
	pnr_3d_opt_tcl.write_cmd_w_opts('setExtractRCMode', extractrcmode_opts)

	analysismode_opts = {
		'-analysisType': 'onChipVariation',
		'-cppr': 'both',
	}
	pnr_3d_opt_tcl.write_cmd_w_opts('setAnalysisMode', analysismode_opts)

	delaycalmode_opts = {
		'-siAware': 'true',
		'-engine': 'aae',
	}
	pnr_3d_opt_tcl.write_cmd_w_opts('setDelayCalMode', delaycalmode_opts)

	if is_on(FLOW_CFGS['INNOVUS']['FEATURES'], 'route_opt_design'):
		pnr_3d_opt_tcl.write_section_comment('route_opt_design options')
		optmode_opts = {
			'-addInstancePrefix': 'routeopt_'
		}
		pnr_3d_opt_tcl.write_cmd_w_opts('setOptMode', optmode_opts)

		pnr_3d_opt_tcl.write_section_comment('run route_opt_design')
		route_opt_design_opts = {
			'-setup': None,
			'-out_dir': FLOW_ENVS['REPORT_DIR'],
			'-prefix': 'postroute',
		}
		if is_on(FLOW_VARS, 'PNR_ENABLE_HOLD_FIX'):
			route_opt_design_opts['-hold'] = None
		pnr_3d_opt_tcl.write_cmd_w_opts('route_opt_design', route_opt_design_opts)
	else:
		pnr_3d_opt_tcl.write_section_comment('route design')
		pnr_3d_opt_tcl.write('routeDesign')

		optmode_opts = {
			'-fixHoldAllowSetupTnsDegrade': 'false',
			'-ignorePathGroupsForHold': '{default}',
			'-addInstancePrefix': 'postroute_opt_'
		}
		pnr_3d_opt_tcl.write_cmd_w_opts('setOptMode', optmode_opts)

		pnr_3d_opt_tcl.write_section_comment('run post-route optimization')
		opt_design_opts = {
			'-postRoute': None,
			'-setup': None,
			'-outDir': FLOW_ENVS['REPORT_DIR'],
			'-prefix': 'postroute_opt',
		}
		if is_on(FLOW_VARS, 'PNR_ENABLE_HOLD_FIX'):
			opt_design_opts['-hold'] = None
		pnr_3d_opt_tcl.write_cmd_w_opts('optDesign', opt_design_opts)

	pnr_3d_opt_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(design_name, 'v', 'gz'))))

	pdflow_pnr.innovus_end_commands(pnr_3d_opt_tcl, design_name=design_name)
	pnr_3d_opt_tcl.close()

	return ret


def write_compact2d_tcl(filename: str, design_name: str) -> int:
	'''
	we don't have to do anything for designs using compact2D flow as split designs are the final results themselves

	:return: 0 if script generation ended successfully. otherwise, 1
	'''
	ret = 0
	pnr_3d_opt_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_3d_opt_tcl, design_name=design_name)

	pdflow_pnr.innovus_end_commands(pnr_3d_opt_tcl, design_name=design_name)

	pnr_3d_opt_tcl.close()
	return ret


def main(main_tcl_files: List[str], log_tracer: flow_log_utils.CustomStreamHandler) -> int:
	'''
	generate timing constraints (sdc) with parasitics from 3d_trial stage,
	and perform detailed routing with the timing contraints

	:param main_tcl_files: the path to the tcl files for partitioned design
	'''
	ret = 0

	if pdflow.is_3D_design():
		if pdflow.is_compact2D_flow():
			part_names = pdflow_pnr.get_session_designs(pdflow_pnr.get_prev_stage(FLOW_ENVS['STAGE']))
			for part_tcl_file, part_name in zip(main_tcl_files, part_names):
				write_compact2d_tcl(part_tcl_file, part_name)
				pdflow_pnr.pnr_input_collaterals.append(part_tcl_file)
		else:
			# generate pt scripts for context generation (sdc for tier designs)
			flow_log_utils.write_subsection_comment(logger, 'generate pt scripts')

			pt_tool_log_file = os.path.join(FLOW_ENVS['RUN_DIR'], flow_file_utils.join_filename('pt'.lower(), 'log'))
			pt_load_library_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'pt', 'load_library', 'tcl'))
			pt_load_design_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'pt', 'load_design', 'tcl'))
			pt_main_tcl_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'pt', 'tcl'))

			ret |= write_pt_load_library(filename=pt_load_library_file)
			ret |= write_pt_load_design(filename=pt_load_design_file)
			ret |= write_pt_tcl(pt_main_tcl_file, load_library_file=pt_load_library_file, load_design_file=pt_load_design_file, tool_log_file=pt_tool_log_file)
			pdflow_pnr.pnr_input_collaterals.append(pt_main_tcl_file)

			flow_log_utils.write_subsubsection_comment(logger, 'check pt input collaterals')
			ret |= pdflow.check_file_list(pdflow_pnr.pnr_input_collaterals, logger)
			if ret != 0:
				return ret
			pdflow_pnr.pnr_input_collaterals = []

			# generate context with pt
			flow_log_utils.write_subsection_comment(logger, 'generate pt context file')
			ret |= flow_run_utils.run('pt_shell -f %s' % (pt_main_tcl_file), run_lvls=['pt'.upper()], tee=pt_tool_log_file)

			# filter logs
			log_filter = get_dict(FLOW_CFGS, 'pt'.upper(), 'LOG_FILTER')
			if log_filter is not None:
				flow_log_utils.filter_log(pt_tool_log_file, log_filter)
				flow_log_utils.write_subsection_comment(logger, 'run summary')
				flow_log_utils.print_filtered_log(logger, 'pt'.upper(), pt_tool_log_file)

			# convert context file to sdc if needed
			# N/A

			# check errors and print summary
			# if there are errors, stop here.
			if pdflow.has_errors(log_tracer=log_tracer, status=ret):
				logger.error('error detected while generating context. stop running. resolve the errors to proceed.')

				cd(FLOW_ENVS['WORK_AREA'])
				return ret

			# generate scripts for detailed routing with generated sdc in innovus
			flow_log_utils.write_subsubsection_comment(logger, 'generate innovus scripts')
			for tier_num, split_info in enumerate(zip(main_tcl_files, ['part0', 'part1'])):
				split_tcl_file, split_name = split_info

				sdc_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(split_name, 'sdc'))
				mmmc_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(split_name, 'mmmc', 'tcl'))
				upf_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(split_name, 'upf'))
				options_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(split_name, 'options', 'tcl'))

				ret |= pdflow_pnr.write_mmmc(mmmc_file, sdc_file_override=sdc_file)
				ret |= pdflow_pnr.write_upf(upf_file)
				ret |= pdflow_pnr.write_options(options_file, num_route_layer_override=FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'][tier_num])
				ret |= write_shrunk2d_tcl(split_tcl_file, split_name, mmmc_file, None, upf_file, options_file)
				pdflow_pnr.pnr_input_collaterals.append(split_tcl_file)

		return ret
	else:
		logger.error('3d_legalize stage is not supported in 2d designs')

		return 1
