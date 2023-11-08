import pdflow
import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_file_utils
import flow_log_utils

import pdflow_lefdef_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str, part_name: str, mmmc_file: str, cpf_file: Union[str, None], upf_file: Union[str, None], options_file: str) -> int:
	'''
	write a script to create sessions for split designs

	:param filename: path to innovus script
	:param part_name: name of split design
	:param mmmc_file: path to mmmc file
	:param cpf_file: path to cpf file
	:param upf_file: path to upf file
	:param options_file: path to options file
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	pnr_3d_split_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_3d_split_tcl, restore_design=False)

	design_mode_opts = {
		'-pessimisticMode': 'true',
	}
	pnr_3d_split_tcl.write_cmd_w_opts('setDesignMode', design_mode_opts)
	netlist_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'v'))
	pnr_3d_split_tcl.write('set init_verilog %s' % (netlist_file))
	pdflow_pnr.pnr_input_collaterals.append(netlist_file)

	lef_files = pdflow_pnr.get_lef_files()
	pnr_3d_split_tcl.write('set init_lef_file %s' % (flow_tcl_utils.get_list(lef_files)))
	pdflow_pnr.pnr_input_collaterals += lef_files

	pwr_net = get_dict(FLOW_VARS, 'DEFAULT_PWR_NET')
	gnd_net = get_dict(FLOW_VARS, 'DEFAULT_GND_NET')
	pnr_3d_split_tcl.write('set init_pwr_net %s' % (pwr_net))
	pnr_3d_split_tcl.write('set init_gnd_net %s' % (gnd_net))
	pnr_3d_split_tcl.write('set init_top_cell %s' % (part_name))
	pnr_3d_split_tcl.write('set init_mmmc_file %s' % (mmmc_file))
	pdflow_pnr.pnr_input_collaterals.append(mmmc_file)
	pnr_3d_split_tcl.write('init_design')
	pnr_3d_split_tcl.write('')
	if upf_file is not None:
		pnr_3d_split_tcl.write('read_power_intent -1801 %s' % (upf_file))
		pdflow_pnr.pnr_input_collaterals.append(upf_file)
	elif cpf_file is not None:
		pnr_3d_split_tcl.write('read_power_intent -cpf %s' % (cpf_file))
		pdflow_pnr.pnr_input_collaterals.append(cpf_file)
	else:
		logger.warning('power intent file does not exist.')
	pnr_3d_split_tcl.write('commit_power_intent')
	pnr_3d_split_tcl.write('')
	pnr_3d_split_tcl.write('source %s' % (options_file))
	pdflow_pnr.pnr_input_collaterals.append(options_file)

	input_def_file = os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'def'))
	pnr_3d_split_tcl.write('defIn %s' % (input_def_file))
	pdflow_pnr.pnr_input_collaterals.append(input_def_file)

	pdflow_pnr.innovus_end_commands(pnr_3d_split_tcl, design_name=part_name)
	pnr_3d_split_tcl.close()

	return ret


def main(main_tcl_files: List[str]) -> int:
	'''
	from ilv cutlayer, split 3d routed design into two tier designs,
	write  all th scripts to create sessions for split design

	:param main_tcl_files: the path to innovus script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	if pdflow.is_3D_design():
		# list all the files required to do 3d split
		route_result_dir = os.path.join(FLOW_ENVS['WORK_AREA'], 'pnr', '3d_route', 'results')
		lef_3d_file = os.path.join(route_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'lef'))
		pdflow_pnr.pnr_input_collaterals.append(lef_3d_file)
		def_3d_file = os.path.join(route_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'def', 'gz'))
		pdflow_pnr.pnr_input_collaterals.append(def_3d_file)
		lef_files = pdflow_pnr.get_lef_files()
		pdflow_pnr.pnr_input_collaterals += lef_files
		ilv_layers_file = os.path.join(route_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'ilv_layers', 'json'))
		pdflow_pnr.pnr_input_collaterals.append(ilv_layers_file)
		maps_2d_to_3d_file = os.path.join(route_result_dir, flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'map', 'json'))
		pdflow_pnr.pnr_input_collaterals.append(maps_2d_to_3d_file)

		ilv_r = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'ILV_R')
		if ilv_r is None:
			logger.error('FLOW_CFGS[TECH_CFG:PDK:3D:%s:ILV_R] not defined.' % (FLOW_ENVS['IMPL_TYPE']))
			ret = 1
		else:
			ilv_r = float(ilv_r)
		ilv_c = get_dict(FLOW_CFGS, 'TECH_CFG', 'PDK', '3D', FLOW_ENVS['IMPL_TYPE'].upper(), 'ILV_C')
		if ilv_c is None:
			logger.error('FLOW_CFGS[TECH_CFG:PDK:3D:%s:ILV_R] not defined.' % (FLOW_ENVS['IMPL_TYPE']))
			ret = 1
		else:
			ilv_c = float(ilv_c)

		flow_log_utils.write_subsubsection_comment(logger, 'check input collaterals')
		ret |= pdflow.check_file_list(pdflow_pnr.pnr_input_collaterals, logger)
		if ret != 0:
			return ret
		pdflow_pnr.pnr_input_collaterals = []

		# read 3d lef/def
		flow_log_utils.write_subsubsection_comment(logger, 'read 3d lef/def')
		i3DLEF = pdflow_lefdef_utils.LEF([lef_3d_file])
		i3DDEF = pdflow_lefdef_utils.DEF(def_3d_file, i3DLEF)
		iLEF = pdflow_lefdef_utils.LEF(lef_files)

		# split the dsign
		flow_log_utils.write_subsubsection_comment(logger, 'split design')
		ilv_layers = flow_file_utils.read_json_file(ilv_layers_file)
		maps_2d_to_3d = flow_file_utils.read_json_file(maps_2d_to_3d_file)
		maps_3d_to_2d = pdflow_lefdef_utils.convert_maps_2d_to_3d_TO_maps_3d_to_2d(maps_2d_to_3d)
		if pdflow.is_compact2D_flow():
			preserve_wire = True
		else:
			preserve_wire = False
		splitDEF = i3DDEF.designs[FLOW_ENVS['BLOCK']].split_by_cutLayer(split_cutLayer_names=ilv_layers, maps_3d_to_2d=maps_3d_to_2d, split_lef=iLEF, row_splitting=True, split_names=['part0', 'part1'], exclude_wires=not preserve_wire)

		# create top verilog/spef, tier verilog/def
		flow_log_utils.write_subsubsection_comment(logger, 'write outputs')
		splitDEF.designs[FLOW_ENVS['BLOCK']].write_verilog(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v')))
		splitDEF.designs[FLOW_ENVS['BLOCK']].write_3d_top_spef(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'spef')), ilv_r, ilv_c)
		splitDEF.designs['part0'].write_verilog(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part0', 'v')))
		splitDEF.designs['part0'].write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part0', 'def')))
		splitDEF.designs['part1'].write_verilog(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part1', 'v')))
		splitDEF.designs['part1'].write_def(os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename('part1', 'def')))

		# create sessions for each tier designs
		flow_log_utils.write_subsubsection_comment(logger, 'generate innovus scripts')
		for tier_num, split_info in enumerate(zip(main_tcl_files, ['part0', 'part1'])):
			split_tcl_file, split_name = split_info
			dummy_sdc_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(split_name, 'sdc'))
			flow_file_utils.make_empty_file(dummy_sdc_file)
			mmmc_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(split_name, 'mmmc', 'tcl'))
			upf_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(split_name, 'upf'))
			options_file = os.path.join(FLOW_ENVS['SCRIPT_DIR'], flow_file_utils.join_filename(split_name, 'options', 'tcl'))
			ret |= pdflow_pnr.write_mmmc(mmmc_file, sdc_file_override=dummy_sdc_file)
			ret |= pdflow_pnr.write_upf(upf_file)
			ret |= pdflow_pnr.write_options(options_file, num_route_layer_override=FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'][tier_num])
			ret |= write_tcl(split_tcl_file, split_name, mmmc_file, None, upf_file, options_file)
			pdflow_pnr.pnr_input_collaterals.append(split_tcl_file)

		return ret
	else:
		logger.error('3d_split stage is not supported in 2d designs')

		return 1
