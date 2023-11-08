import pdflow
import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_log_utils
import flow_file_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_env_utils import flow_envs as FLOW_ENVS
from flow_config_utils import flow_cfgs as FLOW_CFGS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str) -> int:
	'''
	write a script to perform floorplan stage of pnr

	:param filename: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0
	pnr_floorplan_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_floorplan_tcl)

	pnr_floorplan_tcl.write_section_comment('floorplan')
	init_def = get_dict(FLOW_VARS, 'PNR_FPLAN_INIT_DEF')
	if init_def is not None:
		if FLOW_ENVS['IMPL_TYPE'] == '2d':
			pnr_floorplan_tcl.write('defIn %s' % (init_def[0]))
			pdflow_pnr.pnr_input_collaterals.append(init_def[0])
		elif FLOW_ENVS['IMPL_TYPE'] != '2d' and len(init_def) == 1:
			pnr_floorplan_tcl.write('defIn %s' % (init_def[0]))
			pdflow_pnr.pnr_input_collaterals.append(init_def[0])
		elif FLOW_ENVS['IMPL_TYPE'] != '2d' and len(init_def) >= 2:
			init_result = pdflow_pnr.get_prev_result_dir('floorplan')
			c2d_def = os.path.join(init_result, 'c2d.def')
			pnr_floorplan_tcl.write('defIn %s' % (c2d_def))
			pdflow_pnr.pnr_input_collaterals.append(c2d_def)
	else:
		margin_str = ''
		for direction in ['left', 'bottom', 'right', 'left']:
			margin_str += '%f ' % (get_dict(FLOW_VARS, 'PNR_FPLAN_MARGIN', direction))

		core_width = get_dict(FLOW_VARS, 'PNR_FPLAN_CORE_WIDTH')
		core_height = get_dict(FLOW_VARS, 'PNR_FPLAN_CORE_HEIGHT')
		core_ratio = get_dict(FLOW_VARS, 'PNR_FPLAN_CORE_RATIO')
		core_density = get_dict(FLOW_VARS, 'PNR_FPLAN_TARGET_DENSITY')
		if core_width is not None and core_height is not None:
			if pdflow.is_3D_design():
				core_width /= 0.707
				core_height /= 0.707
			fplan_opts = {
				'-s': '%f %f' % (core_width, core_height),
				margin_str: None,
			}
			pnr_floorplan_tcl.write_cmd_w_opts('floorPlan', fplan_opts)
		else:
			fplan_opts = {
				'-r': core_ratio,
				core_density: None,
				margin_str: None,
			}
			pnr_floorplan_tcl.write_cmd_w_opts('floorPlan', fplan_opts)

	rail_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_RAIL_SPEC')
	bump_size = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_SIZE')
	bump_pitch = get_dict(FLOW_VARS, 'PNR_FPLAN_BUMP_PITCH')
	if rail_spec is not None and bump_size is not None and bump_pitch is not None:
		pnr_floorplan_tcl.write_section_comment('power plan')
		pnr_floorplan_tcl.write('package require pdflowEDI_design_utils')
		pnr_floorplan_tcl.write('')
		bottom_routing_layer = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'ROUTE', 'BOTTOM_ROUTING_LAYER')
		if bottom_routing_layer is None:
			logger.warning('FLOW_CFGS[TECH_CFG:PNR:ROUTE:BOTTOM_ROUTING_LAYER] not defined. assuming 1')
			bottom_routing_layer = 1
		build_pdn_opt = {
			'-imp_type': get_dict(FLOW_ENVS, 'IMPL_TYPE'),
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
		if pdflow.is_3D_design():
			build_pdn_opt['-imp_method'] = FLOW_ENVS['IMPL_METHOD']
		core_ring_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_CORE_RING_SPEC')
		if core_ring_spec is not None:
			build_pdn_opt['-core_ring_spec'] = flow_tcl_utils.get_array(core_ring_spec)
		block_ring_spec = get_dict(FLOW_VARS, 'PNR_FPLAN_BLOCK_RING_SPEC')
		if block_ring_spec is not None:
			logger.error(block_ring_spec)
			build_pdn_opt['-block_ring_spec'] = flow_tcl_utils.get_array(block_ring_spec)
		pnr_floorplan_tcl.write_cmd_w_opts('pdflowEDI_design_utils::build_pdn', build_pdn_opt)

	# store verilog & sdf
	pnr_floorplan_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v', 'gz'))))
	pnr_floorplan_tcl.write('write_sdf %s' % os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdf')))

	pdflow_pnr.innovus_end_commands(pnr_floorplan_tcl)
	pnr_floorplan_tcl.close()

	return ret


def main(main_tcl_file: str) -> int:
	'''
	write all the scripts required for floorplan stage of pnr

	:param main_tcl_file: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	ret |= write_tcl(main_tcl_file)
	pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

	return ret

