import pdflow_pnr

import flow_tcl_utils
import flow_log_utils

logger = flow_log_utils.start_logging()


def write_tcl(filename: str) -> int:
	'''
	write a script to perform finish stage of pnr

	:param filename: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	pnr_finish_tcl = flow_tcl_utils.TclFile(filename=filename)
	pdflow_pnr.innovus_start_commands(pnr_finish_tcl)

	# no need to write verilog and sdf as innovus_final_result_commands includes saveNelist and write_sdf
	pdflow_pnr.innovus_final_result_commands(pnr_finish_tcl)
	pdflow_pnr.get_wirelength(pnr_finish_tcl, 'wire_length')
	pdflow_pnr.innovus_end_commands(pnr_finish_tcl)
	pnr_finish_tcl.close()

	return ret


def main(main_tcl_file: str) -> int:
	'''
	write all the scripts required for finish stage of pnr

	:param main_tcl_file: path to pnr script
	:return: 0 if script is generated successfully. Otherwise, 1
	'''
	ret = 0

	ret |= write_tcl(main_tcl_file)
	pdflow_pnr.pnr_input_collaterals.append(main_tcl_file)

	return ret
