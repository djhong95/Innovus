import pdflow
import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_log_utils
import flow_file_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str) -> int:
	'''
	write a script to perform cts stage of pnr

	:param filename: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0
	pnr_cts_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_cts_tcl)

	pnr_cts_tcl.write_section_comment('cts options')
	optmode_opts = {
		'-addInstancePrefix': 'ccopt_',
	}
	pnr_cts_tcl.write_cmd_w_opts('setOptMode', optmode_opts)
	analysismode_opts = {
		'-analysisType': 'onChipVariation',
		'-cppr': 'both',
	}
	pnr_cts_tcl.write_cmd_w_opts('setAnalysisMode', analysismode_opts)

	pnr_cts_tcl.write_section_comment('ccopt setting')
	# clock preferred layers setting
	pnr_cts_tcl.write_subsection_comment('clock route type')

	bottom_routing_layer = get_dict(FLOW_CFGS, 'TECH_CFG', 'PNR', 'ROUTE', 'BOTTOM_ROUTING_LAYER')
	if bottom_routing_layer is None:
		logger.warning('FLOW_CFGS[TECH_CFG:PNR:ROUTE:BOTTOM_ROUTING_LAYER] not defined. assuming 1')
		bottom_routing_layer = 1

	preferred_layer_spec = get_dict(FLOW_VARS, 'PNR_CTS_PREFERRED_LAYER_SPEC')
	if preferred_layer_spec is None:
		if pdflow.is_3D_design():
			max_route_layer = max(FLOW_VARS['PNR_3D_NUM_ROUTE_LAYERS'])
		else:
			max_route_layer = get_dict(FLOW_VARS, 'PNR_NUM_ROUTE_LAYER')
		preferred_layer_spec = {
			'top': {
				'top': max_route_layer,
				'bottom': max_route_layer-1,
			},
			'trunk': {
				'top': max_route_layer-1,
				'bottom': int(bottom_routing_layer)+1,
			},
			'leaf': {
				'top': int(bottom_routing_layer)+1,
				'bottom': bottom_routing_layer,
			},
		}

	for route_type in ['top', 'trunk', 'leaf']:
		route_type_opts = {
			'-name': '_'.join(['ct', route_type]),
			'-preferred_routing_layer_effort': 'medium',
			'-top_preferred_layer': preferred_layer_spec[route_type]['top'],
			'-bottom_preferred_layer': preferred_layer_spec[route_type]['bottom'],
		}
		pnr_cts_tcl.write_cmd_w_opts('create_route_type', route_type_opts)

		prop_route_type_opts = {
			'-net_type': route_type,
			'_'.join(['ct', route_type]): None,
		}
		pnr_cts_tcl.write_cmd_w_opts('set_ccopt_property route_type', prop_route_type_opts)

	pnr_cts_tcl.write_subsection_comment('clock cell settings')
	clk_buf_cell_patterns = get_dict(FLOW_CFGS, 'TECH_CFG', 'LIBRARY', 'CLK_BUF_CELL_PATTERNS')
	buf_cell_patterns = get_dict(FLOW_CFGS, 'TECH_CFG', 'LIBRARY', 'BUF_CELL_PATTERNS')
	if clk_buf_cell_patterns is not None:
		clk_buf_cells = flow_tcl_utils.get_list(pdflow_pnr.lib_db.query(class_name='cell', view_list=['lef'], return_field='cell', include_filter=clk_buf_cell_patterns))
		pnr_cts_tcl.write('set_ccopt_property buffer_cells %s' % (clk_buf_cells))
	elif buf_cell_patterns:
		buf_cells = flow_tcl_utils.get_list(pdflow_pnr.lib_db.query(class_name='cell', view_list=['lef'], return_field='cell', include_filter=buf_cell_patterns))
		pnr_cts_tcl.write('set_ccopt_property buffer_cells %s' % (buf_cells))
	else:
		logger.error('FLOW_CFGS[TECH_CFG:LIBRARY:CLK_BUF_CELL_PATTERNS] or FLOW_CFGS[TECH_CFG:LIBRARY:BUF_CELL_PATTERNS] should be defined')

	if is_on(FLOW_VARS, 'PNR_CTS_USE_INVERTER'):
		pnr_cts_tcl.write('set_ccopt_property use_inverters true')
		clk_inv_cell_patterns = get_dict(FLOW_CFGS, 'TECH_CFG', 'LIBRARY', 'CLK_INV_CELL_PATTERNS')
		inv_cell_patterns = get_dict(FLOW_CFGS, 'TECH_CFG', 'LIBRARY', 'INV_CELL_PATTERNS')
		if clk_inv_cell_patterns is not None:
			clk_inv_cells = flow_tcl_utils.get_list(pdflow_pnr.lib_db.query(class_name='cell', view_list=['lef'], return_field='cell', include_filter=clk_inv_cell_patterns))
			pnr_cts_tcl.write('set_ccopt_property inverter_cells %s' % (clk_inv_cells))
		elif inv_cell_patterns:
			inv_cells = flow_tcl_utils.get_list(pdflow_pnr.lib_db.query(class_name='cell', view_list=['lef'], return_field='cell', include_filter=inv_cell_patterns))
			pnr_cts_tcl.write('set_ccopt_property inverter_cells %s' % (inv_cells))
		else:
			logger.error('FLOW_CFGS[TECH_CFG:LIBRARY:CLK_INV_CELL_PATTERNS] or FLOW_CFGS[TECH_CFG:LIBRARY:INV_CELL_PATTERNS] should be defined when FLOW_VARS[PNR_CTS_USE_INVERTER] is true')
	else:
		pnr_cts_tcl.write('set_ccopt_property use_inverters false')

	cg_cell_patterns = get_dict(FLOW_CFGS, 'TECH_CFG', 'LIBRARY', 'CG_CELL_PATTERNS')
	if cg_cell_patterns is not None:
		cg_cells = flow_tcl_utils.get_list(pdflow_pnr.lib_db.query(class_name='cell', view_list=['lef'], return_field='cell', include_filter=FLOW_CFGS['TECH_CFG']['LIBRARY']['CG_CELL_PATTERNS']))
		pnr_cts_tcl.write('set_ccopt_property clock_gating_cells %s' % (cg_cells))

	pnr_cts_tcl.write_subsection_comment('clock timing settings')
	target_skew = get_dict(FLOW_VARS, 'PNR_CTS_TARGET_SKEW')
	if target_skew is not None:
		pnr_cts_tcl.write('set_ccopt_property target_skew %s' % (FLOW_VARS['PNR_CTS_TARGET_SKEW']))
	else:
		pnr_cts_tcl.write('set_ccopt_property target_skew %s' % ('auto'))

	target_trans_spec = get_dict(FLOW_VARS, 'PNR_CTS_TARGET_MAX_TRANS_SPEC')
	if target_trans_spec is not None:
		for net_type in ['top', 'trunk', 'leaf']:
			prop_target_max_trans_opts = {
				'-net_type': net_type,
			}
			target_trans = get_dict(FLOW_VARS, 'PNR_CTS_TARGET_MAX_TRANS_SPEC', net_type)
			if target_trans is not None:
				prop_target_max_trans_opts[target_trans] = None
			else:
				prop_target_max_trans_opts['auto'] = None
			pnr_cts_tcl.write_cmd_w_opts('set_ccopt_property target_max_trans', prop_target_max_trans_opts)

	pnr_cts_tcl.write_section_comment('run cts')
	pnr_cts_tcl.write('create_ccopt_clock_tree_spec')
	ccopt_design_opts = {
		'-outDir': FLOW_ENVS['REPORT_DIR'],
		'-prefix': 'cts',
	}
	pnr_cts_tcl.write_cmd_w_opts('ccopt_design', ccopt_design_opts)

	pnr_cts_tcl.write_section_comment('post-cts commands')
	rpt_ccopt = {
		'-summary': None,
		'-file': os.path.join(FLOW_ENVS['REPORT_DIR'], 'clock_tree.summary.rpt')
	}
	pnr_cts_tcl.write_cmd_w_opts('report_ccopt_clock_trees', rpt_ccopt)
	rpt_ccopt = {
		'-paths': 1000,
		'-summary': None,
		'-filename': os.path.join(FLOW_ENVS['REPORT_DIR'], 'skew_groups.summary.rpt')
	}
	pnr_cts_tcl.write_cmd_w_opts('report_ccopt_skew_groups', rpt_ccopt)
	rpt_ccopt = {
		'-histogram': None,
		'-filename': os.path.join(FLOW_ENVS['REPORT_DIR'], 'skew_groups.histogram.rpt')
	}
	pnr_cts_tcl.write_cmd_w_opts('report_ccopt_skew_groups', rpt_ccopt)
	rpt_ccopt = {
		'-paths': 1000,
		'-filename': os.path.join(FLOW_ENVS['REPORT_DIR'], 'skew_groups.latency.rpt')
	}
	pnr_cts_tcl.write_cmd_w_opts('report_ccopt_skew_groups', rpt_ccopt)

	pnr_cts_tcl.write('save_ccopt_config %s' % ('ccopt_config.tcl'))
	pnr_cts_tcl.write('reset_ccopt_config')

	# store verilog & sdf
	pnr_cts_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v', 'gz'))))
	pnr_cts_tcl.write('write_sdf %s' % os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdf')))

	pdflow_pnr.innovus_end_commands(pnr_cts_tcl)
	pnr_cts_tcl.close()

	return ret


def main(main_tcl_file: str) -> int:
	'''
	write all the scripts required for cts stage of pnr

	:param main_tcl_file: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	ret |= write_tcl(main_tcl_file)
	pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

	return ret
