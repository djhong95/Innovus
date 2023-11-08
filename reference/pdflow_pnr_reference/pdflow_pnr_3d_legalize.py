import pdflow
import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_file_utils
import flow_log_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str, part_name: str) -> int:
	'''
	write a script to legalize cells in partitioned designs

	:param filename: path to innovus script
	:param part_name: name of design to legalize
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	pnr_legalize_tcl = flow_tcl_utils.TclFile(filename=filename)

	# suppress expected warnings
	# **WARN: (IMPSR-511):    instance ROUND_4__U_ROUND_U_SUB_ROM_1__ROM_U56 is not placed in the correct row, followpin rail may not be generated correctly for it.
	pnr_legalize_tcl.write('set_message -id IMPSR-511 -suppress')
	# **WARN: (IMPPP-133):   The block boundary of instance 'U_SUB_ROM_11__ROM_U37' was increased to (96.584999 36.625000) (97.154999 38.110001) because pins or obstructions were outside the original block boundary.
	pnr_legalize_tcl.write('set_message -id IMPPP-133 -suppress')
	pnr_legalize_tcl.write('')

	pdflow_pnr.innovus_start_commands(pnr_legalize_tcl, design_name=part_name)

	rail_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')
	bump_size = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_SIZE')
	bump_pitch = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_PITCH')
	if rail_spec is not None and bump_size is not None and bump_pitch is not None:
		pnr_legalize_tcl.write_section_comment('power plan')
		pnr_legalize_tcl.write('package require pdflowEDI_design_utils')
		pnr_legalize_tcl.write('')
		bottom_routing_layer = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'ROUTE', 'BOTTOM_ROUTING_LAYER')
		if bottom_routing_layer is None:
			logger.warning('FLOW_CFGS[TECH_CFG:PNR:ROUTE:BOTTOM_ROUTING_LAYER] not defined. assuming 1')
			bottom_routing_layer = 1
		build_pdn_opt = {
			'-imp_type': get_dict(FLOW_ENVS, 'IMPL_TYPE'),
			'-imp_method': FLOW_ENVS['IMPL_METHOD'],
			'-pwr_net': get_dict(FLOW_VARS, 'DEFAULT_PWR_NET'),
			'-gnd_net': get_dict(FLOW_VARS, 'DEFAULT_GND_NET'),
			'-pwr_pins': '[lsort -unique [dbGet [dbGet -p head.libCells.pgTerms.pgType primaryPower].name]]',
			'-gnd_pins': '[lsort -unique [dbGet [dbGet -p head.libCells.pgTerms.pgType primaryGround].name]]',
			'-bump_size': bump_size,
			'-bump_pitch': bump_pitch,
			'-rail_spec': flow_tcl_utils.get_array(get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')),
			'-bottom_routing_layer': bottom_routing_layer,
			'-output_dir': FLOW_ENVS['RESULT_DIR'],
			'-output_prefix': FLOW_ENVS['BLOCK'],
		}
		core_ring_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_CORE_RING_SPEC')
		if core_ring_spec is not None:
			build_pdn_opt['-core_ring_spec'] = flow_tcl_utils.get_array(core_ring_spec)
		block_ring_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_BLOCK_RING_SPEC')
		if block_ring_spec is not None:
			logger.error(block_ring_spec)
			build_pdn_opt['-block_ring_spec'] = flow_tcl_utils.get_array(block_ring_spec)
		if FLOW_ENVS['IMPL_TYPE'] == 'f2f':
			build_pdn_opt['-pwr_tsv_size'] = FLOW_VARS['PNR_FPLAN_PWR_TSV_SIZE']
			build_pdn_opt['-pwr_tsv_pitch'] = FLOW_VARS['PNR_FPLAN_PWR_TSV_PITCH']
		pnr_legalize_tcl.write_cmd_w_opts('pdflowEDI_design_utils::build_pdn', build_pdn_opt)

	pnr_legalize_tcl.write('refinePlace')
	lefdef_ver = get_dict(FLOW_CFGS, 'PROJECT_CFG', 'TOOL', 'INNOVUS', 'LEFDEF_VERSION')
	if lefdef_ver is not None:
		lefdef_ver = 5.8
	pnr_legalize_tcl.write('set lefDefOutVersion %.1f' % (lefdef_ver))
	if FLOW_VARS['PNR_PARTITION_METHOD'] == 'cluster':
		defout_opts = {
			'-floorplan': None,
			'-netlist': None,
			os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'cluster', 'def', 'gz')): None,
		}
	else:
		defout_opts = {
			'-floorplan': None,
			'-netlist': None,
			os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'def', 'gz')): None,
		}
	pnr_legalize_tcl.write_cmd_w_opts('defOut', defout_opts)

	pdflow_pnr.innovus_end_commands(pnr_legalize_tcl, design_name=part_name)
	pnr_legalize_tcl.close()

	return ret


def main(main_tcl_files: List[str]) -> int:
	'''
	write all the scripts to legalize cells in the partitioned designs

	:param main_tcl_file: path to innovus script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	if pdflow.is_3D_design():
		part_names = pdflow_pnr.get_session_designs(pdflow_pnr.get_prev_stage(FLOW_ENVS['STAGE']))
		for part_tcl_file, part_name in zip(main_tcl_files, part_names):
			ret |= write_tcl(part_tcl_file, part_name)
			pdflow_pnr.pnr_input_collaterals.append(part_tcl_file)

		return ret
	else:
		logger.error('3d_legalize stage is not supported in 2d designs')

		return 1
