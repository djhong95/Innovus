#!/usr/bin/env python3

import pdflow
import pdflow_pnr
from typing import *

from flow_utils import *
import flow_tcl_utils
import flow_log_utils

from flow_env_utils import flow_envs as FLOW_ENVS

logger = flow_log_utils.start_logging()


def write_tcl(filename: str, part_name: str) -> int:
	'''
	write a script to perform finish stage for split designs

	:param filename: path to innovus script
	:param part_name: name of split design
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	pnr_3d_finish_tcl = flow_tcl_utils.TclFile(filename=filename)
	# **ERROR: (TCLCMD-290):    Could not find technology library 'sc12mc_cln28hpm_base_hvt_c35_ss_typical_max_0p81v_125c' (File /home/kchang/test_pe/test/aes_128/aes_128/CLN28HPM/r4p0/impl/wa_3d/pnr/3d_opt/results/part0.sdc, Line 247942)
	pnr_3d_finish_tcl.write('set_message -id TCLCMD-290 -suppress')
	# **ERROR: (TCLCMD-1040):   -library option of set_wire_load_model accepts only a timing library. (File /home/kchang/test_pe/test/aes_128/aes_128/NANGATE45/2020_10/impl/wa_3d/pnr/3d_opt/results/part0.sdc, Line 357566)
	pnr_3d_finish_tcl.write('set_message -id TCLCMD-1040 -suppress')
	pnr_3d_finish_tcl.write('')
	pdflow_pnr.innovus_start_commands(pnr_3d_finish_tcl, design_name=part_name)

	pdflow_pnr.innovus_final_result_commands(pnr_3d_finish_tcl, design_name=part_name)

	pdflow_pnr.innovus_end_commands(pnr_3d_finish_tcl, design_name=part_name)
	pnr_3d_finish_tcl.close()

	return ret


def main(main_tcl_files: List[str]) -> int:
	'''
	write all the scripts required for finish stage for split designs

	:param main_tcl_files: path to innovus script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	if pdflow.is_3D_design():
		for part_tcl_file, part_name in zip(main_tcl_files, ['part0', 'part1']):
			ret |= write_tcl(part_tcl_file, part_name)

		return ret
	else:
		logger.error('3d_legalize stage is not supported in 2d designs')

		return 1

