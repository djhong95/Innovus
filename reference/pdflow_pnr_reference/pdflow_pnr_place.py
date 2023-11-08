import pdflow_pnr

from flow_utils import *
import flow_tcl_utils
import flow_file_utils

from flow_config_utils import flow_cfgs as FLOW_CFGS
from flow_env_utils import flow_envs as FLOW_ENVS
from flow_var_utils import flow_vars as FLOW_VARS


def write_tcl(filename: str) -> int:
	'''
	write a script to perform place stage of pnr

	:param filename: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	pnr_place_tcl = flow_tcl_utils.TclFile(filename=filename)

	pdflow_pnr.innovus_start_commands(pnr_place_tcl)

	pnr_place_tcl.write_section_comment('place options')
	optmode_opts = {
		'-addInstancePrefix': 'placeopt_'
	}
	pnr_place_tcl.write_cmd_w_opts('setOptMode', optmode_opts)

	'''
	placemode_opts = {}
	if not dict_exist(FLOW_VARS, FLOW_VARS, 'PNR_FPLAN_INIT_DEF'):
		placemode_opts['-placeIoPins'] = 'true'
	pnr_place_tcl.write_cmd_w_opts('setPlaceMode', placemode_opts)
	'''
	pnr_place_tcl.write_section_comment('place design')
	placeoptdesign_opts = {
		'-out_dir': FLOW_ENVS['REPORT_DIR'],
		'-prefix': 'place'
	}
	pnr_place_tcl.write_cmd_w_opts('place_opt_design', placeoptdesign_opts)

	pnr_place_tcl.write_section_comment('post-place commands')
	tie_cells = get_dict(FLOW_CFGS, 'TECH_CFG', 'LIBRARY', 'TIE_CELLS')
	if tie_cells is not None:
		tiehilomode_opts = {
			'-cell': flow_tcl_utils.get_list(tie_cells),
		}
		tie_max_dist = get_dict(FLOW_VARS, 'PNR_PLACE_TIE_MAX_DIST')
		if tie_max_dist is not None:
			tiehilomode_opts['-maxDistance'] = tie_max_dist
		tie_max_fanout = get_dict(FLOW_VARS, 'PNR_PLACE_TIE_MAX_FANOUT')
		if tie_max_fanout is not None:
			tiehilomode_opts['-maxFanout'] = tie_max_fanout

		pnr_place_tcl.write_cmd_w_opts('setTieHiLoMode', tiehilomode_opts)

	# store verilog & sdf
	pnr_place_tcl.write('saveNetlist %s' % (os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'v', 'gz'))))
	pnr_place_tcl.write('write_sdf %s' % os.path.join(FLOW_ENVS['RESULT_DIR'], flow_file_utils.join_filename(FLOW_ENVS['BLOCK'], 'sdf')))

	pdflow_pnr.innovus_end_commands(pnr_place_tcl)
	pnr_place_tcl.close()

	return ret


def main(main_tcl_file: str) -> int:
	'''
	write all the scripts required for place stage of pnr

	:param main_tcl_file: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	ret |= write_tcl(main_tcl_file)
	pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

	return ret
