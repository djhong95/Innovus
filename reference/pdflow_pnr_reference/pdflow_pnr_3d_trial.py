#!/usr/bin/env python3
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


def write_tcl(filename: str, part_name: str):
	'''
	generate tcl file to trial routing in a partitioned design

	:param filename: the path to the tcl file for the partitioned design
	:param part_name: the name of the partition in DEF object
	'''
	ret = 0

	pnr_3d_trial_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_3d_trial_tcl, design_name=part_name)

	# we don't have to do anything for designs using compact2D flow as split designs are the final results themselves
	if not pdflow.is_compact2D_flow():
		rail_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')
		bump_size = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_SIZE')
		bump_pitch = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_PITCH')
		if rail_spec is not None and bump_size is not None and bump_pitch is not None:
			pnr_3d_trial_tcl.write_section_comment('power plan')
			pnr_3d_trial_tcl.write('package require pdflowEDI_design_utils')
			pnr_3d_trial_tcl.write('')
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
			pnr_3d_trial_tcl.write_cmd_w_opts('pdflowEDI_design_utils::build_pdn', build_pdn_opt)

		pnr_3d_trial_tcl.write('trialRoute')

		# to avoid license problem, we need to use TQuantus instead of IQuantus
		# (from user guide) TQuantus extraction engine is recommended for the implementation phase because it is optimized for performance with a small tradeoff for accuracy. IQuantus extraction engine is recommended for ECO flow, as it has near-signoff accuracy
		# TQuantus: -effortLevel medium
		# IQuantus: -effortLevel high
		extractrcmode_opts = {
			'-effortLevel': 'medium',
			'-engine': 'preRoute',
			'-total_c_th': '0',
			'-relative_c_th': '0.03',
			'-coupling_c_th': '1',
		}
		pnr_3d_trial_tcl.write_cmd_w_opts('setExtractRCMode', extractrcmode_opts)
		pnr_3d_trial_tcl.write('extractRC')

		pnr_3d_trial_tcl.write('foreach rc_corner [all_rc_corners -active] {')
		rcout_opts = {
			'-rc_corner': '$rc_corner',
			'-spef': os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, '$rc_corner', 'spef', 'gz'))
		}
		pnr_3d_trial_tcl.write_cmd_w_opts('rcOut', rcout_opts)
		pnr_3d_trial_tcl.write('}')

		lefdef_ver = get_dict(FLOW_CFGS, 'PROJECT_CFG', 'TOOL', 'INNOVUS', 'LEFDEF_VERSION')
		if lefdef_ver is not None:
			lefdef_ver = 5.8
		pnr_3d_trial_tcl.write('set lefDefOutVersion %.1f' % (lefdef_ver))
		defout_opts = {
			'-floorplan': None,
			'-routing': None,
			os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'def', 'gz')): None,
		}
		pnr_3d_trial_tcl.write_cmd_w_opts('defOut', defout_opts)

		pnr_3d_trial_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(part_name, 'v', 'gz'))))

	pdflow_pnr.innovus_end_commands(pnr_3d_trial_tcl, design_name=part_name)
	pnr_3d_trial_tcl.close()

	return ret


def main(main_tcl_files: List[str]) -> int:
	'''
	perform trial routing with split designs, and get rough parasitics for the two tier designs

	:param main_tcl_files: the path to the tcl files for partitioned design
	'''
	ret = 0

	if pdflow.is_3D_design():
		part_names = pdflow_pnr.get_session_designs(pdflow_pnr.get_prev_stage(FLOW_ENVS['STAGE']))
		for part_tcl_file, part_name in zip(main_tcl_files, part_names):
			ret |= write_tcl(part_tcl_file, part_name)
			pdflow_pnr.pnr_input_collaterals.append(part_tcl_file)

		return ret
	else:
		logger.error('3d_trial stage is not supported in 2d designs')

		return 1
