import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_log_utils
import flow_file_utils

from flow_var_utils import flow_vars as FLOW_VARS
from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str) -> int:
	'''
	write a script to perform postcts_opt stage of pnr

	:param filename: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0
	pnr_postcts_opt_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_postcts_opt_tcl)

	pnr_postcts_opt_tcl.write_section_comment('post-cts optimization options')
	optmode_opts = {
		'-fixHoldAllowSetupTnsDegrade': 'false',
		'-ignorePathGroupsForHold': '{default}',
		'-addInstancePrefix': 'postcts_opt_',
	}
	pnr_postcts_opt_tcl.write_cmd_w_opts('setOptMode', optmode_opts)

	pnr_postcts_opt_tcl.write_section_comment('run post-cts optimization')
	opt_design_opts = {
		'-postCTS': None,
		'-setup': None,
		'-outDir': FLOW_ENVS['REPORT_DIR'],
		'-prefix': 'postcts_opt',
	}
	if is_on(FLOW_VARS, 'PNR_ENABLE_HOLD_FIX'):
		opt_design_opts['-hold'] = None
	pnr_postcts_opt_tcl.write_cmd_w_opts('optDesign', opt_design_opts)

	# store verilog & sdf
	pnr_postcts_opt_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v', 'gz'))))
	pnr_postcts_opt_tcl.write('write_sdf %s' % os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdf')))

	pdflow_pnr.innovus_end_commands(pnr_postcts_opt_tcl)
	pnr_postcts_opt_tcl.close()

	return ret


def main(main_tcl_file: str) -> int:
	'''
	write all the scripts required for postcts_opt stage of pnr

	:param main_tcl_file: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	ret |= write_tcl(main_tcl_file)
	pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

	return ret

