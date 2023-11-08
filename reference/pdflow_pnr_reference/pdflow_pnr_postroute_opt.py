import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_log_utils
import flow_file_utils

from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS
from flow_var_utils import flow_vars as FLOW_VARS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str) -> int:
	'''
	write a script to perform postroute_opt stage of pnr

	:param filename: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0
	pnr_postroute_opt_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_postroute_opt_tcl)

	if not is_on(FLOW_CFGS, 'INNOVUS', 'FEATURES', 'route_opt_design'):
		pnr_postroute_opt_tcl.write_section_comment('post-route optimization options')
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
		pnr_postroute_opt_tcl.write_cmd_w_opts('setExtractRCMode', extractrcmode_opts)

		analysismode_opts = {
			'-analysisType': 'onChipVariation',
			'-cppr': 'both',
		}
		pnr_postroute_opt_tcl.write_cmd_w_opts('setAnalysisMode', analysismode_opts)

		delaycalmode_opts = {
			'-siAware': 'true',
			'-engine': 'aae',
		}
		pnr_postroute_opt_tcl.write_cmd_w_opts('setDelayCalMode', delaycalmode_opts)

		optmode_opts = {
			'-fixHoldAllowSetupTnsDegrade': 'false',
			'-ignorePathGroupsForHold': '{default}',
			'-addInstancePrefix': 'postroute_opt_'
		}
		pnr_postroute_opt_tcl.write_cmd_w_opts('setOptMode', optmode_opts)

		pnr_postroute_opt_tcl.write_section_comment('run post-route optimization')
		opt_design_opts = {
			'-postRoute': None,
			'-setup': None,
			'-outDir': FLOW_ENVS['REPORT_DIR'],
			'-prefix': 'postroute_opt',
		}
		if is_on(FLOW_VARS, 'PNR_ENABLE_HOLD_FIX'):
			opt_design_opts['-hold'] = None
		pnr_postroute_opt_tcl.write_cmd_w_opts('optDesign', opt_design_opts)

	# store verilog & sdf
	pnr_postroute_opt_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v', 'gz'))))
	pnr_postroute_opt_tcl.write('write_sdf %s' % os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdf')))

	pdflow_pnr.innovus_end_commands(pnr_postroute_opt_tcl)
	pnr_postroute_opt_tcl.close()

	return ret


def main(main_tcl_file: str) -> int:
	'''
	write all the scripts required for postroute_opt stage of pnr

	:param main_tcl_file: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	ret |= write_tcl(main_tcl_file)
	pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

	return ret

